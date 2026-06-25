package com.performance;

import com.performance.dto.ReportAttachmentUploadResponse;
import com.performance.dto.ReportReviewItemResponse;
import com.performance.dto.ReportUpdateRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URI;
import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/admin/reports")
@Validated
public class PerformanceController {

    private final PerformanceService service;
    private final ReportAttachmentService attachmentService;

    public PerformanceController(PerformanceService service, ReportAttachmentService attachmentService) {
        this.service = service;
        this.attachmentService = attachmentService;
    }

    @PostMapping("/submit")
    public ResponseEntity<TaskResult> submit(@Valid @RequestBody TaskResult report) {
        TaskResult saved = service.submitReport(report);
        return ResponseEntity.created(URI.create("/api/admin/reports/" + saved.getId())).body(saved);
    }

    @PostMapping(value = "/attachments", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<ReportAttachmentUploadResponse> uploadAttachment(@RequestParam("file") MultipartFile file)
            throws IOException {
        return ResponseEntity.ok(attachmentService.store(file));
    }

    @GetMapping
    public List<ReportReviewItemResponse> list(
            @RequestParam(required = false) TaskResultStatus status,
            @RequestParam(required = false) Long submitterId,
            @RequestParam(required = false) String from,
            @RequestParam(required = false) String to) {
        if (status != null) {
            return service.listByStatus(status);
        }
        if (submitterId != null) {
            return service.listBySubmitter(submitterId);
        }
        if (from != null && to != null) {
            return service.listByDateRange(LocalDate.parse(from), LocalDate.parse(to));
        }
        return service.listAll();
    }

    @GetMapping("/statuses")
    public List<TaskResultStatus> statuses() {
        return List.of(TaskResultStatus.values());
    }

    @GetMapping("/{id:\\d+}")
    public ResponseEntity<TaskResult> get(@PathVariable Long id) {
        return service.findById(id).map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PutMapping("/{id:\\d+}")
    public ResponseEntity<TaskResult> update(@PathVariable Long id, @RequestBody ReportUpdateRequest report) {
        TaskResult updated = service.updateReport(id, report);
        if (updated == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id:\\d+}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        service.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id:\\d+}/approve")
    public ResponseEntity<TaskResult> approve(@PathVariable Long id,
                                              @RequestParam @NotBlank String reviewer,
                                              @RequestParam(required = false) String comment) {
        TaskResult r = service.approve(id, reviewer, comment == null ? "Approved" : comment);
        if (r == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(r);
    }

    @PostMapping("/{id:\\d+}/reject")
    public ResponseEntity<TaskResult> reject(@PathVariable Long id,
                                             @RequestParam @NotBlank String reviewer,
                                             @RequestParam @NotBlank String reason) {
        TaskResult r = service.reject(id, reviewer, reason);
        if (r == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(r);
    }
}
