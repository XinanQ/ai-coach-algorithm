package com.decomposition;

import com.decomposition.dto.DecompositionContextResponse;
import com.decomposition.dto.DecompositionListResponse;
import com.decomposition.dto.DecompositionSaveRequest;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/decompositions")
@Validated
public class DecompositionController {

    private final DecompositionService service;

    public DecompositionController(DecompositionService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<?> list(@RequestParam(required = false) String role,
                                  @RequestParam(required = false) Long organizationId,
                                  @RequestParam(required = false) Long projectId) {
        List<DecompositionListResponse> result = service.list(role, organizationId, projectId);
        if (projectId != null) {
            if (result.isEmpty()) return ResponseEntity.ok().body(null);
            return ResponseEntity.ok(result.get(0));
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/{id}")
    public ResponseEntity<DecompositionListResponse> getById(@PathVariable Long id) {
        DecompositionListResponse result = service.findById(id);
        if (result == null) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(result);
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> save(@Valid @RequestBody DecompositionSaveRequest request) {
        Map<String, Object> result = service.save(request);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/context")
    public ResponseEntity<DecompositionContextResponse> getContext() {
        DecompositionContextResponse ctx = service.getContext();
        return ResponseEntity.ok(ctx);
    }
}
