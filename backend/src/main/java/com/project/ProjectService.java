package com.project;

import com.project.Project;
import com.project.ProjectStatus;

import java.util.List;
import java.util.Optional;

public interface ProjectService {
    List<Project> findAll();
    Optional<Project> findById(Long id);
    Project save(Project project);
    void deleteById(Long id);
    Project setStatus(Long id, ProjectStatus status);
}
