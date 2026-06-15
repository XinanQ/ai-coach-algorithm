package com.project;

import com.project.dto.ProjectIndicatorCreateRequest;
import com.project.dto.ProjectIndicatorResponse;
import com.project.dto.ProjectIndicatorUpdateRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

/**
 * 1.1.3.4 项目-指标挂接（含 V1 积分标准）
 */
@RestController
@RequestMapping("/api/admin/projects/{projectId}/indicators")
public class ProjectIndicatorController {

    private final ProjectIndicatorService service;

    public ProjectIndicatorController(ProjectIndicatorService service) {
        this.service = service;
    }

    @GetMapping
    public List<ProjectIndicatorResponse> list(@PathVariable Long projectId) {
        return service.listByProject(projectId);
    }

    @GetMapping("/{id}")
    public ProjectIndicatorResponse get(@PathVariable Long projectId, @PathVariable Long id) {
        return service.get(projectId, id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ProjectIndicatorResponse> create(
            @PathVariable Long projectId,
            @RequestBody ProjectIndicatorCreateRequest request) {
        ProjectIndicatorResponse saved = service.create(projectId, request);
        return ResponseEntity
                .created(URI.create("/api/admin/projects/" + projectId + "/indicators/" + saved.getId()))
                .body(saved);
    }

    @PutMapping("/{id}")
    public ProjectIndicatorResponse update(
            @PathVariable Long projectId,
            @PathVariable Long id,
            @RequestBody ProjectIndicatorUpdateRequest request) {
        return service.update(projectId, id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long projectId, @PathVariable Long id) {
        service.delete(projectId, id);
    }
}
