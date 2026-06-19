package com.project;

import com.project.dto.ProjectCreateRequest;
import com.project.dto.ProjectResponse;

import java.time.LocalDate;
import java.time.LocalTime;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;


import java.net.URI;
import java.util.Arrays;
import java.util.List;

@RestController
@RequestMapping("/api/admin/projects")
@Validated
public class ProjectController {

    private final ProjectService service;

    public ProjectController(ProjectService service) {
        this.service = service;
    }

    @GetMapping
    public List<ProjectResponse> list() {
        return service.findAll()
                .stream()
                .map(this::toResponse)
                .toList();
    }


    @GetMapping("/{id}")
    public ResponseEntity<ProjectResponse> get(@PathVariable Long id) {
        return service.findById(id)
                .map(project -> ResponseEntity.ok(toResponse(project)))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<ProjectResponse> create(@Valid @RequestBody ProjectCreateRequest request) {

        Project project = toEntity(request);
        Project saved = service.save(project);

        return ResponseEntity
                .created(URI.create("/api/admin/projects/" + saved.getId()))
                .body(toResponse(saved));
    }

    @PutMapping("/{id}")
    public ResponseEntity<Project> update(@PathVariable Long id, @Valid @RequestBody Project project) {
        return service.findById(id).map(existing -> {
            project.setId(id);
            project.setCreatedAt(existing.getCreatedAt());
            Project updated = service.save(project);
            return ResponseEntity.ok(updated);
        }).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        service.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/status")
    public ResponseEntity<Project> setStatus(@PathVariable Long id, @RequestParam @NotNull ProjectStatus status) {
        Project p = service.setStatus(id, status);
        if (p == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(p);
    }

    @GetMapping("/statuses")
    public List<ProjectStatus> statuses() {
        return Arrays.asList(ProjectStatus.values());
    }

    private Project toEntity(ProjectCreateRequest request) {
        Project project = new Project();

        project.setName(request.name());
        project.setDescription(request.description());
        project.setStartDate(LocalDate.parse(request.startDate()));
        project.setEndDate(LocalDate.parse(request.endDate()));
        project.setReportDeadline(parseReportDeadline(request.reportDeadline()));
        project.setStatus(parseStatus(request.status()));
        project.setOrganizationId(resolveOrganizationId(request));
        project.setManagerId(parseLong(request.managerId()));
        project.setAttachmentsRequired(Boolean.TRUE.equals(request.attachmentRequired()));
        project.setAttachmentInstructions(request.attachmentInstructions());

        return project;
    }

    private ProjectResponse toResponse(Project project) {
        String statusCode = project.getStatus() == null ? "PLANNED" : project.getStatus().name();

        return new ProjectResponse(
                String.valueOf(project.getId()),
                project.getId(),
                project.getName(),
                project.getDescription(),
                project.getStartDate() == null ? "" : project.getStartDate().toString(),
                project.getEndDate() == null ? "" : project.getEndDate().toString(),
                project.getReportDeadline() == null ? "" : project.getReportDeadline().toString().substring(0, 5),
                Boolean.TRUE.equals(project.getAttachmentsRequired()),
                project.getAttachmentInstructions(),
                toChineseStatus(statusCode),
                statusCode,
                project.getOrganizationId(),
                project.getManagerId(),
                project.getManagerId() == null ? "项目负责人" : "负责人ID " + project.getManagerId(),
                "",
                project.getOrganizationId() == null ? "" : String.valueOf(project.getOrganizationId()),
                "待分解",
                project.getCreatedAt() == null ? "" : project.getCreatedAt().toLocalDate().toString()
        );
    }

    private LocalTime parseReportDeadline(String value) {
        if (value == null || value.isBlank()) {
            return LocalTime.of(18, 0);
        }

        return value.length() == 5
                ? LocalTime.parse(value + ":00")
                : LocalTime.parse(value);
    }

    private ProjectStatus parseStatus(String status) {
        if (status == null || status.isBlank()) {
            return ProjectStatus.PLANNED;
        }

        switch (status) {
            case "草稿":
            case "DRAFT":
                return ProjectStatus.DRAFT;

            case "未开始":
            case "PLANNED":
                return ProjectStatus.PLANNED;

            case "进行中":
            case "ACTIVE":
                return ProjectStatus.ACTIVE;

            case "已暂停":
            case "PAUSED":
                return ProjectStatus.PAUSED;

            case "已结束":
            case "COMPLETED":
                return ProjectStatus.COMPLETED;

            case "已取消":
            case "CANCELLED":
                return ProjectStatus.CANCELLED;

            default:
                return ProjectStatus.PLANNED;
        }
    }

    private String toChineseStatus(String statusCode) {
        if (statusCode == null || statusCode.isBlank()) {
            return "未开始";
        }

        switch (statusCode) {
            case "DRAFT":
                return "草稿";

            case "PLANNED":
                return "未开始";

            case "ACTIVE":
                return "进行中";

            case "PAUSED":
                return "已暂停";

            case "COMPLETED":
                return "已结束";

            case "CANCELLED":
                return "已取消";

            default:
                return "未开始";
        }
    }

    private Long resolveOrganizationId(ProjectCreateRequest request) {
        Long organizationId = parseLong(request.organizationId());
        if (organizationId != null) return organizationId;

        Long ownerOrgId = parseLong(request.ownerOrgId());
        return ownerOrgId == null ? 1L : ownerOrgId;
    }

    private Long parseLong(String value) {
        try {
            return value == null || value.isBlank() ? null : Long.parseLong(value);
        } catch (NumberFormatException ex) {
            return null;
        }
    }
}