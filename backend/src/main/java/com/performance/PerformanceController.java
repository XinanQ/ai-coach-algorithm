package com.performance;

import com.performance.TaskResult;
import com.performance.TaskResultStatus;
import com.performance.PerformanceService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/admin/reports")
@Validated
public class PerformanceController {

    private final PerformanceService service;

    public PerformanceController(PerformanceService service) {
        this.service = service;
    }

    @PostMapping("/submit")
    public ResponseEntity<TaskResult> submit(@Valid @RequestBody TaskResult report) {
        TaskResult saved = service.submitReport(report);
        return ResponseEntity.created(URI.create("/api/admin/reports/" + saved.getId())).body(saved);
    }

    @GetMapping
    public List<TaskResult> list(
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
        return service.listByStatus(TaskResultStatus.PENDING);
    }

    @GetMapping("/{id}")
    public ResponseEntity<TaskResult> get(@PathVariable Long id) {
        return service.findById(id).map(ResponseEntity::ok).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @GetMapping("/statuses")
    public List<TaskResultStatus> statuses() {
        return List.of(TaskResultStatus.values());
    }

    @PostMapping("/{id}/approve")
    public ResponseEntity<TaskResult> approve(@PathVariable Long id,
                                              @RequestParam @NotBlank String reviewer,
                                              @RequestParam(required = false) String comment) {
        TaskResult r = service.approve(id, reviewer, comment == null ? "Approved" : comment);
        if (r == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(r);
    }

    @PostMapping("/{id}/reject")
    public ResponseEntity<TaskResult> reject(@PathVariable Long id,
                                             @RequestParam @NotBlank String reviewer,
                                             @RequestParam @NotBlank String reason) {
        TaskResult r = service.reject(id, reviewer, reason);
        if (r == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(r);
    }
}
