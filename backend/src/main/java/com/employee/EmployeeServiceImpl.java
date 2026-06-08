package com.employee;

import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.employee.ExcelUtil;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class EmployeeServiceImpl implements EmployeeService {

    private final EmployeeRepository repo;

    public EmployeeServiceImpl(EmployeeRepository repo) {
        this.repo = repo;
    }

    @Override
    public List<Employee> findAll() {
        return repo.findAll();
    }

    @Override
    public Optional<Employee> findById(Long id) {
        return repo.findById(id);
    }

    @Override
    public Employee save(Employee employee) {
        return repo.save(employee);
    }

    @Override
    public void deleteById(Long id) {
        repo.deleteById(id);
    }

    @Override
    public List<Employee> importFromExcel(MultipartFile file) throws IOException {
        List<Employee> list = ExcelUtil.parseEmployees(file.getInputStream());
        return repo.saveAll(list);
    }

    @Override
    public byte[] exportToExcel() throws IOException {
        List<Employee> list = repo.findAll();
        return ExcelUtil.employeesToExcel(list);
    }
}
