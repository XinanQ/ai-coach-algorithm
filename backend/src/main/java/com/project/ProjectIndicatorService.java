package com.project;

import com.project.dto.ProjectIndicatorCreateRequest;
import com.project.dto.ProjectIndicatorResponse;
import com.project.dto.ProjectIndicatorUpdateRequest;

import java.util.List;

public interface ProjectIndicatorService {

    List<ProjectIndicatorResponse> listByProject(Long projectId);

    ProjectIndicatorResponse get(Long projectId, Long id);

    ProjectIndicatorResponse create(Long projectId, ProjectIndicatorCreateRequest req);

    ProjectIndicatorResponse update(Long projectId, Long id, ProjectIndicatorUpdateRequest req);

    void delete(Long projectId, Long id);
}
