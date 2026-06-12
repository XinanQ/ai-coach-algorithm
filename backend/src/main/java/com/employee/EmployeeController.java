package com.employee;

import com.employee.dto.EmployeeCreateRequest;
import com.employee.dto.EmployeeResponse;
import com.employee.dto.EmployeeUpdateRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.net.URI;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin/employees")
public class EmployeeController {

    private final EmployeeService service;

    public EmployeeController(EmployeeService service) {
        this.service = service;
    }

    @GetMapping
    public List<EmployeeResponse> list() {
        return service.findAll().stream()
                .map(EmployeeResponse::from)
                .collect(Collectors.toList());
    }

    @GetMapping("/{id}")
    public ResponseEntity<EmployeeResponse> get(@PathVariable Long id) {
        return service.findById(id)
                .map(EmployeeResponse::from)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<EmployeeResponse> create(@RequestBody EmployeeCreateRequest request) {
        Employee saved = service.save(request.toEmployee());
        return ResponseEntity.created(URI.create("/api/admin/employees/" + saved.getId()))
                .body(EmployeeResponse.from(saved));
    }

    @PutMapping("/{id}")
    public ResponseEntity<EmployeeResponse> update(@PathVariable Long id, @RequestBody EmployeeUpdateRequest request) {
        return service.findById(id).map(existing -> {
            request.applyTo(existing);
            Employee updated = service.save(existing);
            return ResponseEntity.ok(EmployeeResponse.from(updated));
        }).orElseGet(() -> ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        service.deleteById(id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/import")
    public ResponseEntity<?> importExcel(@RequestParam("file") MultipartFile file) {
        try {
            List<Employee> imported = service.importFromExcel(file);
            return ResponseEntity.ok().body("Imported " + imported.size() + " employees");
        } catch (Exception ex) {
            return ResponseEntity.badRequest().body("Failed to import: " + ex.getMessage());
        }
    }

    @GetMapping("/export")
    public ResponseEntity<byte[]> exportExcel() {
        try {
            byte[] data = service.exportToExcel();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
            headers.set(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=employees.xlsx");
            return ResponseEntity.ok().headers(headers).body(data);
        } catch (Exception ex) {
            return ResponseEntity.internalServerError().build();
        }
    }
}
