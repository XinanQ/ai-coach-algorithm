package com.project;

import com.auth.CurrentUserContext;
import com.organization.Organization;
import com.organization.OrganizationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
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

    @Override
    public Project setStatus(Long id, ProjectStatus status) {
        return repo.findById(id).map(p -> {
            p.setStatus(status);
            return repo.save(p);
        }).orElse(null);
    }
}
