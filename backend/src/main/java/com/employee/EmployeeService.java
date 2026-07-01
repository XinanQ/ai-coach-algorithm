package com.employee;

import com.employee.dto.EmployeeCreateRequest;
import com.employee.dto.EmployeeImportPreviewResponse;
import com.employee.dto.EmployeeUpdateRequest;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Optional;
import java.util.Map;

public interface EmployeeService {

    List<Employee> findAll();

    List<Employee> findVisibleEmployees();

    Optional<Employee> findById(Long id);

    Optional<Employee> findVisibleById(Long id);

    Employee createEmployee(EmployeeCreateRequest request);

    Employee updateVisibleEmployee(Long id, EmployeeUpdateRequest request);

    Employee save(Employee employee);

    void deleteById(Long id);

    List<Employee> importFromExcel(MultipartFile file) throws IOException;

    EmployeeImportPreviewResponse previewImport(MultipartFile file) throws IOException;

    byte[] exportImportTemplate() throws IOException;

    byte[] exportToExcel() throws IOException;

    byte[] exportVisibleToExcel() throws IOException;

    Map<Long, Long> countVisibleEmployeesByOrganizationId();

    Map<Long, Long> countVisibleAdminsByOrganizationId();
}