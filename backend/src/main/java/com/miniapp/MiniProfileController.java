package com.miniapp;

import com.auth.CurrentUserContext;
import com.auth.UserAccount;
import com.auth.UserAccountRepository;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.organization.Organization;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
public class MiniProfileController {

    private final EmployeeRepository employeeRepository;
    private final UserAccountRepository userAccountRepository;

    public MiniProfileController(EmployeeRepository employeeRepository,
                                 UserAccountRepository userAccountRepository) {
        this.employeeRepository = employeeRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @GetMapping("/api/mini/profile")
    public ResponseEntity<Map<String, Object>> getProfile() {
        Long currentEmployeeId = CurrentUserContext.getEmployeeId();

        Employee employee = employeeRepository.findByIdWithOrganization(currentEmployeeId)
                .orElseThrow(() -> new RuntimeException("Current employee not found"));

        UserAccount account = userAccountRepository.findByEmployeeId(currentEmployeeId)
                .orElse(null);

        Organization organization = employee.getOrganization();

        Map<String, Object> data = new HashMap<>();
        data.put("employeeId", employee.getId());
        data.put("employeeNo", account == null ? null : account.getEmployeeNo());
        data.put("name", employee.getName());
        data.put("email", employee.getEmail());
        data.put("position", employee.getPosition());
        data.put("department", employee.getDepartment());
        data.put("level", employee.getLevel());
        data.put("isAdmin", employee.getIsAdmin());
        data.put("isInProject", employee.getIsInProject());

        data.put("organizationId", organization == null ? null : organization.getId());
        data.put("organizationName", organization == null ? null : organization.getName());
        data.put("organizationCode", organization == null ? null : organization.getCode());
        data.put("organizationLevel", organization == null || organization.getLevel() == null
                ? null
                : organization.getLevel().name());

        Map<String, Object> body = new HashMap<>();
        body.put("code", 200);
        body.put("message", "Success");
        body.put("data", data);

        return ResponseEntity.ok(body);
    }
}