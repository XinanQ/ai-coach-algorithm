package com.employee;

import com.employee.Employee;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Optional;

public interface EmployeeService {
    List<Employee> findAll();
    Optional<Employee> findById(Long id);
    Employee save(Employee employee);
    void deleteById(Long id);
    List<Employee> importFromExcel(MultipartFile file) throws IOException;
    byte[] exportToExcel() throws IOException;
}
