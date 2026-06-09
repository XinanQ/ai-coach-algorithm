package com.project;

import com.project.Project;
import com.project.ProjectStatus;
import com.project.ProjectRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class ProjectServiceImpl implements ProjectService {

    private final ProjectRepository repo;

    public ProjectServiceImpl(ProjectRepository repo) {
        this.repo = repo;
    }

    @Override
    public List<Project> findAll() {
        return repo.findAll();
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
    public void deleteById(Long id) {
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
