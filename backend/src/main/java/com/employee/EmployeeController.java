package com.employee;

import com.auth.UserAccount;
import com.auth.UserAccountRepository;
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
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/admin/employees")
public class EmployeeController {

    private final EmployeeService service;
    private final UserAccountRepository userAccountRepository;

    public EmployeeController(EmployeeService service, UserAccountRepository userAccountRepository) {
        this.service = service;
        this.userAccountRepository = userAccountRepository;
    }

    @GetMapping
    public List<EmployeeResponse> list() {
        List<Employee> employees = service.findVisibleEmployees();
        Map<Long, String> employeeNos = loadEmployeeNos(employees);
        return employees.stream()
                .map(employee -> EmployeeResponse.from(employee, employeeNos.get(employee.getId())))
                .collect(Collectors.toList());
    }

    @GetMapping("/{id}")
    public ResponseEntity<EmployeeResponse> get(@PathVariable Long id) {
        return service.findVisibleById(id)
                .map(employee -> {
                    String employeeNo = userAccountRepository.findByEmployeeId(employee.getId())
                            .map(UserAccount::getEmployeeNo)
                            .orElse(null);
                    return EmployeeResponse.from(employee, employeeNo);
                })
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<EmployeeResponse> create(@RequestBody EmployeeCreateRequest request) {
        Employee saved = service.createEmployee(request);
        return ResponseEntity.created(URI.create("/api/admin/employees/" + saved.getId()))
                .body(EmployeeResponse.from(saved));
    }

    @PutMapping("/{id}")
    public ResponseEntity<EmployeeResponse> update(@PathVariable Long id, @RequestBody EmployeeUpdateRequest request) {
        try {
            Employee updated = service.updateVisibleEmployee(id, request);
            return ResponseEntity.ok(EmployeeResponse.from(updated));
        } catch (IllegalArgumentException ex) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        return service.findVisibleById(id).map(existing -> {
            service.deleteById(existing.getId());
            return ResponseEntity.noContent().<Void>build();
        }).orElseGet(() -> ResponseEntity.notFound().build());
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
            byte[] data = service.exportVisibleToExcel();
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"));
            headers.set(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=employees.xlsx");
            return ResponseEntity.ok().headers(headers).body(data);
        } catch (Exception ex) {
            return ResponseEntity.internalServerError().build();
        }
    }

    private Map<Long, String> loadEmployeeNos(List<Employee> employees) {
        if (employees.isEmpty()) {
            return Map.of();
        }
        List<Long> ids = employees.stream().map(Employee::getId).collect(Collectors.toList());
        return userAccountRepository.findByEmployeeIdIn(ids).stream()
                .collect(Collectors.toMap(UserAccount::getEmployeeId, UserAccount::getEmployeeNo, (a, b) -> a));
    }
}
