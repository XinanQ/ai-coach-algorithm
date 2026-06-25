package com.project;

import com.project.Project;
import com.project.ProjectStatus;

import java.util.List;
import java.util.Optional;

public interface ProjectService {
    List<Project> findAll();

    /** 仅返回当前登录用户机构有权看到的项目（按参与机构范围 + 机构层级过滤）。 */
    List<Project> findVisibleForCurrentUser();

    Optional<Project> findById(Long id);

    /** 当前用户对该项目是否可见。 */
    boolean isVisibleToCurrentUser(Long projectId);

    Project save(Project project);

    /** 覆盖式设置项目的参与机构范围。 */
    void replaceVisibleOrgs(Long projectId, List<Long> organizationIds);

    void deleteById(Long id);

    Project setStatus(Long id, ProjectStatus status);
}
