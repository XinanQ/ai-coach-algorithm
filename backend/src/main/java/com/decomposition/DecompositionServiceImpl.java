package com.decomposition;

import com.auth.CurrentUserContext;
import com.decomposition.dto.DecompositionContextResponse;
import com.decomposition.dto.DecompositionListResponse;
import com.decomposition.dto.DecompositionSaveRequest;
import com.decomposition.dto.DecompositionSaveRequest.IndicatorItem;
import com.decomposition.dto.DecompositionSaveRequest.TargetItem;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.organization.Organization;
import com.organization.Organization.OrgLevel;
import com.organization.OrganizationRepository;
import com.performance.ReviewScopeService;
import com.project.Project;
import com.project.ProjectRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@Transactional
public class DecompositionServiceImpl implements DecompositionService {

    private static final Logger log = LoggerFactory.getLogger(DecompositionServiceImpl.class);

    private static final Map<String, String> NEXT_LEVEL_MAP = Map.of(
            "总行", "省行",
            "省行", "市行",
            "市行", "支行",
            "支行", "网点",
            "网点", "员工"
    );

    private static final Map<String, String> ROLE_BY_LEVEL = Map.of(
            "省行", "province_admin",
            "市行", "city_admin",
            "支行", "branch_admin",
            "网点", "outlet_admin"
    );

    private final DecompositionRepository repo;
    private final EmployeeRepository employeeRepository;
    private final ReviewScopeService reviewScopeService;
    private final OrganizationRepository organizationRepository;
    private final ProjectRepository projectRepository;
    private final ObjectMapper objectMapper;

    public DecompositionServiceImpl(DecompositionRepository repo,
                                    EmployeeRepository employeeRepository,
                                    ReviewScopeService reviewScopeService,
                                    OrganizationRepository organizationRepository,
                                    ProjectRepository projectRepository,
                                    ObjectMapper objectMapper) {
        this.repo = repo;
        this.employeeRepository = employeeRepository;
        this.reviewScopeService = reviewScopeService;
        this.organizationRepository = organizationRepository;
        this.projectRepository = projectRepository;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional(readOnly = true)
    public List<DecompositionListResponse> list(String ownerRole, Long currentOrgId, Long projectId) {
        List<DecompositionRecord> records;
        if (ownerRole != null && currentOrgId != null && projectId != null) {
            records = repo.findByOwnerRoleAndCurrentOrgIdAndProjectId(ownerRole, currentOrgId, projectId);
        } else if (ownerRole != null && currentOrgId != null) {
            records = repo.findByOwnerRoleAndCurrentOrgId(ownerRole, currentOrgId);
        } else if (ownerRole != null) {
            records = repo.findByOwnerRole(ownerRole);
        } else if (projectId != null) {
            records = repo.findByProjectId(projectId);
        } else {
            records = repo.findAll();
        }

        List<DecompositionListResponse> result = new ArrayList<>();
        for (DecompositionRecord r : records) {
            try {
                result.add(DecompositionListResponse.from(r));
            } catch (Exception ignored) {
                // skip malformed records
            }
        }

        if (projectId != null && !result.isEmpty()) {
            return List.of(result.get(0));
        }
        return result;
    }

    @Override
    public Map<String, Object> save(DecompositionSaveRequest request) {
        Employee current = getCurrentEmployee();
        log.info("分解保存请求: user={} orgId={} projectId={} originType={} targets={}",
                current.getName(), current.getOrganization() != null ? current.getOrganization().getId() : null,
                request.getProjectId(), request.getOriginType(),
                request.getTargets() != null ? request.getTargets().size() : 0);

        // Permission: must be review admin
        if (!reviewScopeService.isReviewAdmin(current)) {
            throw new IllegalArgumentException("当前账号无分解权限，仅管理员可执行分解操作");
        }

        Long projectId = request.getProjectId();
        Long currentOrgId = request.getCurrentOrgId();
        String originType = request.getOriginType();
        Long userOrgId = current.getOrganization() != null ? current.getOrganization().getId() : null;

        // Verify org ownership based on origin type
        if ("created".equals(originType)) {
            if (userOrgId == null || !userOrgId.equals(currentOrgId)) {
                throw new IllegalArgumentException("只有项目所在机构可下发分解");
            }
        } else if ("received".equals(originType)) {
            List<DecompositionRecord> existing = repo.findByProjectIdAndCurrentOrgId(projectId, currentOrgId);
            boolean hasReceived = existing.stream().anyMatch(r -> "received".equals(r.getOriginType()));
            if (!hasReceived) {
                throw new IllegalArgumentException("未找到上级下发的分解记录");
            }
            if (!currentOrgId.equals(userOrgId)) {
                throw new IllegalArgumentException("只能分解本机构收到的任务");
            }
        }

        // Persist original plan (upsert by externalId) and generate received records
        try {
            String json = objectMapper.writeValueAsString(request);
            log.debug("序列化请求成功, payload length={}", json.length());

            // Upsert: find all records with this externalId (may have duplicates from earlier bugs)
            List<DecompositionRecord> matching = repo.findAllByExternalId(request.getId());
            DecompositionRecord original;
            if (matching.isEmpty()) {
                original = new DecompositionRecord();
            } else {
                original = matching.get(0);
                // Delete duplicates (keep the first one)
                for (int i = 1; i < matching.size(); i++) {
                    repo.delete(matching.get(i));
                    log.info("清理重复主记录 externalId={} id={}", matching.get(i).getExternalId(), matching.get(i).getId());
                }
            }
            original.setExternalId(request.getId());
            original.setProjectId(projectId);
            original.setOwnerRole(request.getOwnerRole());
            original.setOriginType(originType);
            original.setReceivedFrom(request.getReceivedFrom() != null ? request.getReceivedFrom() : "");
            original.setCurrentOrganization(request.getCurrentOrganization() != null ? request.getCurrentOrganization() : "");
            original.setCurrentOrgId(currentOrgId);
            original.setCurrentLevel(request.getCurrentLevel() != null ? request.getCurrentLevel() : "");
            original.setNextLevel(request.getNextLevel());
            original.setStatus(request.getStatus() != null ? request.getStatus() : "已下发");
            original.setReadOnly(false);
            original.setPayload(json);
            original = repo.save(original);
            log.info("主分解记录已保存 id={} externalId={}", original.getId(), original.getExternalId());

            // Clean up old received records sent by this org for this project before recreating
            List<DecompositionRecord> oldReceived = repo.findByProjectId(projectId);
            String currentOrgName = request.getCurrentOrganization();
            for (DecompositionRecord r : oldReceived) {
                if ("received".equals(r.getOriginType())
                        && currentOrgName != null && currentOrgName.equals(r.getReceivedFrom())) {
                    repo.delete(r);
                    log.debug("删除旧下发记录 externalId={}", r.getExternalId());
                }
            }

            // Generate received records for each target at the next level
            String childLevel = request.getNextLevel();
            String grandChildLevel = NEXT_LEVEL_MAP.get(childLevel);
            String childRole = ROLE_BY_LEVEL.get(childLevel);

            if (childRole != null) {
                for (TargetItem target : request.getTargets()) {
                    DecompositionRecord rec = new DecompositionRecord();
                    String extId = "received-" + projectId + "-" + target.getId();
                    rec.setExternalId(extId);
                    rec.setProjectId(projectId);
                    rec.setOwnerRole(childRole);
                    rec.setOriginType("received");
                    rec.setReceivedFrom(currentOrgName != null ? currentOrgName : "");
                    rec.setCurrentOrganization(target.getTarget());
                    rec.setCurrentOrgId(target.getId());
                    rec.setCurrentLevel(childLevel);
                    rec.setNextLevel(grandChildLevel != null ? grandChildLevel : "");
                    rec.setStatus("已下发");
                    rec.setReadOnly(true);

                    Map<String, Object> single = new LinkedHashMap<>();
                    single.put("id", extId);
                    single.put("projectId", String.valueOf(projectId));
                    single.put("ownerRole", childRole);
                    single.put("originType", "received");
                    single.put("receivedFrom", currentOrgName != null ? currentOrgName : "");
                    single.put("currentOrganization", target.getTarget());
                    single.put("currentOrgId", target.getId());
                    single.put("currentLevel", childLevel);
                    single.put("nextLevel", grandChildLevel != null ? grandChildLevel : "");
                    single.put("status", "已下发");
                    single.put("readOnly", true);
                    single.put("targets", List.of(buildSingleTargetPayload(target, childLevel, grandChildLevel)));

                    rec.setPayload(objectMapper.writeValueAsString(single));
                    repo.save(rec);
                }
            }

            Map<String, Object> response = new LinkedHashMap<>();
            response.put("success", true);
            response.put("message", "分解方案已保存");
            response.put("recordId", original.getId());
            return response;
        } catch (JsonProcessingException e) {
            log.error("分解方案序列化失败: {}", e.getMessage(), e);
            throw new IllegalArgumentException("序列化分解方案失败: " + e.getMessage(), e);
        } catch (Exception e) {
            log.error("保存分解方案失败: {}", e.getMessage(), e);
            // Unwrap to get the root cause message
            Throwable root = e;
            while (root.getCause() != null && root.getCause() != root) {
                root = root.getCause();
            }
            throw new IllegalArgumentException("保存分解方案失败: " + root.getMessage(), e);
        }
    }

    @Override
    @Transactional(readOnly = true)
    public DecompositionContextResponse getContext() {
        Employee current = getCurrentEmployee();
        Organization org = current.getOrganization();
        if (org == null) {
            throw new IllegalArgumentException("当前用户无关联机构");
        }

        String currentLevel = resolveChineseLevel(org.getLevel());
        String nextLevel = NEXT_LEVEL_MAP.get(currentLevel);
        if (nextLevel == null) {
            throw new IllegalArgumentException("当前层级（" + currentLevel + "）无法继续向下分解");
        }

        // Verify user is admin and has permission at this level
        if (!reviewScopeService.isReviewAdmin(current)) {
            throw new IllegalArgumentException("无权限查看分解上下文");
        }

        List<Organization> children = organizationRepository.findByParentId(org.getId());

        DecompositionContextResponse resp = new DecompositionContextResponse();
        resp.setOrgId(org.getId());
        resp.setOrgName(org.getName());
        resp.setCurrentLevel(currentLevel);
        resp.setNextLevel(nextLevel);
        resp.setChildren(children.stream().map(child -> {
            DecompositionContextResponse.ChildOrg co = new DecompositionContextResponse.ChildOrg();
            co.setId(child.getId());
            co.setName(child.getName());
            co.setLevel(resolveChineseLevel(child.getLevel()));
            return co;
        }).collect(Collectors.toList()));
        return resp;
    }

    @Override
    @Transactional(readOnly = true)
    public DecompositionListResponse findById(Long id) {
        return repo.findById(id).map(DecompositionListResponse::from).orElse(null);
    }

    // ---- helpers ----

    private Employee getCurrentEmployee() {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId == null) {
            throw new IllegalArgumentException("未登录，无法操作");
        }
        return employeeRepository.findByIdWithOrganization(currentId)
                .orElseThrow(() -> new IllegalArgumentException("当前用户信息缺失"));
    }

    private String resolveChineseLevel(OrgLevel level) {
        if (level == null) return "";
        return switch (level) {
            case HEADQUARTERS -> "总行";
            case PROVINCE -> "省行";
            case CITY -> "市行";
            case BRANCH -> "支行";
            case OUTLET -> "网点";
        };
    }

    private Map<String, Object> buildSingleTargetPayload(TargetItem target, String childLevel, String grandChildLevel) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", target.getId());
        payload.put("target", target.getTarget());
        payload.put("level", childLevel);

        List<Map<String, Object>> indicators = new ArrayList<>();
        if (target.getIndicators() != null) {
            for (IndicatorItem ind : target.getIndicators()) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("indicatorId", ind.getIndicatorId());
                item.put("indicator", ind.getIndicator() != null ? ind.getIndicator() : "");
                item.put("totalTask", ind.getCurrentAllocation() != null ? ind.getCurrentAllocation().doubleValue() : 0);
                item.put("allocated", 0);
                item.put("currentAllocation", 0);
                item.put("unit", ind.getUnit() != null ? ind.getUnit() : "");
                indicators.add(item);
            }
        }
        payload.put("indicators", indicators);
        return payload;
    }
}
