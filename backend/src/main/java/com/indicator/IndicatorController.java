package com.indicator;

import com.indicator.dto.*;
import com.task.Task;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.data.domain.Page;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/admin/indicators")
@Validated
public class IndicatorController {

    private final IndicatorService service;

    public IndicatorController(IndicatorService service) {
        this.service = service;
    }

    // ========== 1.1.3.1 指标库 ==========

    @GetMapping
    public Page<IndicatorResponse> list(
            @RequestParam(required = false) String businessLine,
            @RequestParam(required = false) Boolean enabled,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return service.listLibrary(businessLine, enabled, category, keyword, page, size);
    }

    @GetMapping("/{id}")
    public IndicatorResponse get(@PathVariable Long id) {
        return service.getLibraryById(id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<IndicatorResponse> create(@RequestBody IndicatorCreateRequest request) {
        IndicatorResponse saved = service.createLibrary(request);
        return ResponseEntity.created(URI.create("/api/admin/indicators/" + saved.getId())).body(saved);
    }

    @PutMapping("/{id}")
    public IndicatorResponse update(@PathVariable Long id, @RequestBody IndicatorUpdateRequest request) {
        return service.updateLibrary(id, request);
    }

    @PatchMapping("/{id}/status")
    public IndicatorResponse updateStatus(@PathVariable Long id, @RequestBody IndicatorStatusRequest request) {
        return service.updateLibraryStatus(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        service.deleteLibrary(id);
    }

    // ========== 1.1.3.2 分解 / 催办 ==========

    @PostMapping("/{id}/decompose")
    public ResponseEntity<Indicator> decompose(@PathVariable Long id, @Valid @RequestBody Indicator child) {
        Indicator saved = service.decompose(id, child);
        return ResponseEntity.ok(saved);
    }

    @GetMapping("/{id}/children")
    public List<Indicator> children(@PathVariable Long id) {
        return service.findChildren(id);
    }

    @PostMapping("/{id}/remind")
    public ResponseEntity<Void> remind(@PathVariable Long id, @RequestParam @NotBlank String message) {
        service.remind(id, message);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/{id}/reminders")
    public List<Task> reminders(@PathVariable Long id) {
        return service.findReminders(id);
    }
}
