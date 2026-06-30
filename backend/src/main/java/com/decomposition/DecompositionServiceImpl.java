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

    // 机构层级 → 前端角色字符串。用于由登录用户的真实机构推导其身份，
    // 不再信任前端传来的 ownerRole / currentOrgId。
    private static final Map<OrgLevel, String> ROLE_BY_ORG_LEVEL = Map.of(
            OrgLevel.HEADQUARTERS, "head_admin",
            OrgLevel.PROVINCE, "province_admin",
            OrgLevel.CITY, "city_admin",
            OrgLevel.BRANCH, "branch_admin",
            OrgLevel.OUTLET, "outlet_admin"
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
        // 回读身份以登录用户为准，确保与保存时落库的 ownerRole / currentOrgId 完全一致，
        // 从根本上避免"存了却查不到"。未登录场景（无上下文）则沿用入参，保持向后兼容。
        Long employeeId = CurrentUserContext.getEmployeeId();
        if (employeeId != null) {
            Employee current = employeeRepository.findByIdWithOrganization(employeeId).orElse(null);
            if (current != null && current.getOrganization() != null) {
                Long authedOrgId = current.getOrganization().getId();
                String authedRole = roleByOrgLevel(current.getOrganization().getLevel());
                if (authedOrgId != null) {
                    currentOrgId = authedOrgId;
                }
                if (authedRole != null) {
                    ownerRole = authedRole;
                }
            }
        }

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
            // 单项目视图：优先返回可编辑记录（readOnly=false），其次才是只读的上级下发记录，
            // 这样收到方分解保存后能读回自己的可编辑计划，而不是又回到只读的收到视图。
            result.sort(Comparator.comparing(DecompositionListResponse::isReadOnly));
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
        String originType = request.getOriginType();

        // 分解方的身份一律以登录用户的真实机构为准，不信任前端传来的
        // currentOrgId / ownerRole / 机构名 / 层级，从根本上保证写入 key 与回读 key 一致。
        Organization userOrg = current.getOrganization();
        if (userOrg == null) {
            throw new IllegalArgumentException("当前用户无关联机构，无法执行分解");
        }
        Long currentOrgId = userOrg.getId();
        String currentOrgName = userOrg.getName() != null ? userOrg.getName() : "";
        String currentLevel = resolveChineseLevel(userOrg.getLevel());
        String ownerRole = roleByOrgLevel(userOrg.getLevel());
        // 下一层级按机构真实层级推导，推导不出时回退到请求值
        String nextLevel = NEXT_LEVEL_MAP.get(currentLevel);
        if (nextLevel == null) {
            nextLevel = request.getNextLevel();
        }

        // 按来源类型校验权限
        if ("received".equals(originType)) {
            List<DecompositionRecord> existing = repo.findByProjectIdAndCurrentOrgId(projectId, currentOrgId);
            boolean hasReceived = existing.stream().anyMatch(r -> "received".equals(r.getOriginType()));
            if (!hasReceived) {
                throw new IllegalArgumentException("未找到上级下发的分解记录");
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
            original.setOwnerRole(ownerRole);
            original.setOriginType(originType);
            original.setReceivedFrom(request.getReceivedFrom() != null ? request.getReceivedFrom() : "");
            original.setCurrentOrganization(currentOrgName);
            original.setCurrentOrgId(currentOrgId);
            original.setCurrentLevel(currentLevel != null ? currentLevel : "");
            original.setNextLevel(nextLevel);
            original.setStatus(request.getStatus() != null ? request.getStatus() : "已下发");
            original.setReadOnly(false);
            original.setPayload(json);
            original = repo.save(original);
            log.info("主分解记录已保存 id={} externalId={}", original.getId(), original.getExternalId());

            // 重建前先清掉本机构就该项目下发过的旧 received 记录
            List<DecompositionRecord> oldReceived = repo.findByProjectId(projectId);
            for (DecompositionRecord r : oldReceived) {
                if ("received".equals(r.getOriginType())
                        && currentOrgName.equals(r.getReceivedFrom())) {
                    repo.delete(r);
                    log.debug("删除旧下发记录 externalId={}", r.getExternalId());
                }
            }

            // 为每个直属对象生成下一层级的 received 记录
            String childLevel = nextLevel;
            String grandChildLevel = childLevel != null ? NEXT_LEVEL_MAP.get(childLevel) : null;
            String childRole = childLevel != null ? ROLE_BY_LEVEL.get(childLevel) : null;

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

    private String roleByOrgLevel(OrgLevel level) {
        return level == null ? null : ROLE_BY_ORG_LEVEL.get(level);
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
