package com.project;

import com.auth.CurrentUserContext;
import com.organization.Organization;
import com.organization.OrganizationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

@Service
@Transactional
public class ProjectServiceImpl implements ProjectService {

    private final ProjectRepository repo;
    private final ProjectVisibleOrgRepository visibleOrgRepo;
    private final OrganizationRepository orgRepo;

    public ProjectServiceImpl(ProjectRepository repo,
                              ProjectVisibleOrgRepository visibleOrgRepo,
                              OrganizationRepository orgRepo) {
        this.repo = repo;
        this.visibleOrgRepo = visibleOrgRepo;
        this.orgRepo = orgRepo;
    }

    @Override
    public List<Project> findAll() {
        return repo.findAll();
    }

    @Override
    @Transactional(readOnly = true)
    public List<Project> findVisibleForCurrentUser() {
        Long userOrgId = CurrentUserContext.getOrganizationId();
        // 没有登录机构信息时不做过滤（如本地联调），返回全部
        if (userOrgId == null) {
            return repo.findAll();
        }

        Set<Long> selfAndAncestors = selfAndAncestorIds(userOrgId);

        List<Project> result = new ArrayList<>();
        for (Project project : repo.findAll()) {
            if (isProjectVisible(project, userOrgId, selfAndAncestors)) {
                result.add(project);
            }
        }
        return result;
    }

    @Override
    @Transactional(readOnly = true)
    public boolean isVisibleToCurrentUser(Long projectId) {
        Long userOrgId = CurrentUserContext.getOrganizationId();
        if (userOrgId == null) {
            return true;
        }
        Project project = repo.findById(projectId).orElse(null);
        if (project == null) {
            return false;
        }
        return isProjectVisible(project, userOrgId, selfAndAncestorIds(userOrgId));
    }

    private boolean isProjectVisible(Project project, Long userOrgId, Set<Long> selfAndAncestors) {
        List<Long> visibleOrgIds = visibleOrgRepo.findByProjectId(project.getId()).stream()
                .map(ProjectVisibleOrg::getOrganizationId)
                .toList();

        // 未设置参与范围 → 不限制
        if (visibleOrgIds.isEmpty()) {
            return true;
        }
        // 创建者本机构始终可见
        if (project.getOrganizationId() != null && project.getOrganizationId().equals(userOrgId)) {
            return true;
        }
        // 某个参与机构是当前用户机构本身或其上级 → 用户（含其下级）可见
        return visibleOrgIds.stream().anyMatch(selfAndAncestors::contains);
    }

    /** 当前机构 + 一路向上的所有上级机构 id。 */
    private Set<Long> selfAndAncestorIds(Long orgId) {
        Set<Long> ids = new HashSet<>();
        Organization org = orgRepo.findById(orgId).orElse(null);
        int guard = 0;
        while (org != null && guard++ < 20) {
            ids.add(org.getId());
            org = org.getParent();
        }
        return ids;
    }

    @Override
    public Optional<Project> findById(Long id) {
        return repo.findById(id);
    }

    @Override
    public Project save(Project project) {
        if (project.getStatus() == null) {
            project.setStatus(ProjectStatus.DRAFT);
        }
        return repo.save(project);
    }

    @Override
    public void replaceVisibleOrgs(Long projectId, List<Long> organizationIds) {
        visibleOrgRepo.deleteByProjectId(projectId);
        if (organizationIds == null || organizationIds.isEmpty()) {
            return;
        }
        // 去重后保存
        Set<Long> unique = new HashSet<>(organizationIds);
        for (Long orgId : unique) {
            if (orgId != null) {
                visibleOrgRepo.save(new ProjectVisibleOrg(projectId, orgId));
            }
        }
    }

    @Override
    public void deleteById(Long id) {
        // 先清参与机构关联，避免孤儿记录
        visibleOrgRepo.deleteByProjectId(id);
        repo.deleteById(id);
    }

    /**
     * 合法状态流转表（状态机）。仅允许下列转换；终态（已结束 / 已取消）不可再变更。
     * 前端 Projects.vue 的 ALLOWED_TRANSITIONS 须与此保持一致。
     */
    private static final Map<ProjectStatus, Set<ProjectStatus>> ALLOWED_TRANSITIONS = buildAllowedTransitions();

    private static Map<ProjectStatus, Set<ProjectStatus>> buildAllowedTransitions() {
        Map<ProjectStatus, Set<ProjectStatus>> map = new EnumMap<>(ProjectStatus.class);
        map.put(ProjectStatus.DRAFT, EnumSet.of(ProjectStatus.PLANNED, ProjectStatus.CANCELLED));
        map.put(ProjectStatus.PLANNED, EnumSet.of(ProjectStatus.ACTIVE, ProjectStatus.CANCELLED));
        map.put(ProjectStatus.ACTIVE, EnumSet.of(ProjectStatus.PAUSED, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED));
        map.put(ProjectStatus.PAUSED, EnumSet.of(ProjectStatus.ACTIVE, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED));
        map.put(ProjectStatus.COMPLETED, EnumSet.noneOf(ProjectStatus.class));
        map.put(ProjectStatus.CANCELLED, EnumSet.noneOf(ProjectStatus.class));
        return map;
    }

    @Override
    public Project setStatus(Long id, ProjectStatus status) {
        if (status == null) {
            throw new IllegalArgumentException("目标状态不能为空");
        }
        return repo.findById(id).map(p -> {
            ProjectStatus current = p.getStatus();
            // 同状态视为幂等；不同状态则必须是合法流转，否则拒绝（HTTP 400）
            if (current != null && current != status) {
                Set<ProjectStatus> allowed = ALLOWED_TRANSITIONS.getOrDefault(current, Set.of());
                if (!allowed.contains(status)) {
                    throw new IllegalArgumentException(
                            "不允许的状态流转：" + zh(current) + " → " + zh(status));
                }
            }
            p.setStatus(status);
            return repo.save(p);
        }).orElse(null);
    }

    private static String zh(ProjectStatus status) {
        if (status == null) {
            return "未知";
        }
        return switch (status) {
            case DRAFT -> "草稿";
            case PLANNED -> "未开始";
            case ACTIVE -> "进行中";
            case PAUSED -> "已暂停";
            case COMPLETED -> "已结束";
            case CANCELLED -> "已取消";
        };
    }
}
