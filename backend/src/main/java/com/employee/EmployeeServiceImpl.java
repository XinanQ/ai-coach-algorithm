package com.employee;

import com.auth.CurrentUserContext;
import com.employee.dto.EmployeeCreateRequest;
import com.employee.dto.EmployeeUpdateRequest;
import com.organization.Organization;
import com.organization.OrganizationService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Optional;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@Transactional
public class EmployeeServiceImpl implements EmployeeService {

    private final EmployeeRepository repo;
    private final OrganizationService organizationService;

    public EmployeeServiceImpl(EmployeeRepository repo,
                               OrganizationService organizationService) {
        this.repo = repo;
        this.organizationService = organizationService;
    }

    private List<Long> getVisibleOrganizationIds() {
        Long organizationId = CurrentUserContext.getOrganizationId();

        if (organizationId == null) {
            throw new IllegalArgumentException("Current user's organizationId cannot be null");
        }

        return organizationService.findSelfAndDescendantIds(organizationId);
    }

    private Organization getVisibleOrganizationOrThrow(Long organizationId) {
        if (organizationId == null) {
            throw new IllegalArgumentException("organizationId is required");
        }

        List<Long> visibleOrganizationIds = getVisibleOrganizationIds();

        if (!visibleOrganizationIds.contains(organizationId)) {
            throw new IllegalArgumentException("No permission to operate organization: " + organizationId);
        }

        return organizationService.findById(organizationId)
                .orElseThrow(() -> new IllegalArgumentException("Organization not found: " + organizationId));
    }

    @Override
    public List<Employee> findAll() {
        return repo.findAll();
    }

    @Override
    @Transactional(readOnly = true)
    public List<Employee> findVisibleEmployees() {
        List<Long> visibleOrganizationIds = getVisibleOrganizationIds();
        return repo.findByOrganization_IdIn(visibleOrganizationIds);
    }

    @Override
    @Transactional(readOnly = true)
    public Map<Long, Long> countVisibleEmployeesByOrganizationId() {
        return findVisibleEmployees().stream()
                .filter(employee -> employee.getOrganization() != null)
                .collect(Collectors.groupingBy(
                        employee -> employee.getOrganization().getId(),
                        Collectors.counting()
                ));
    }

    @Override
    @Transactional(readOnly = true)
    public Map<Long, Long> countVisibleAdminsByOrganizationId() {
        return findVisibleEmployees().stream()
                .filter(employee -> employee.getOrganization() != null)
                .filter(employee -> Boolean.TRUE.equals(employee.getIsAdmin()))
                .collect(Collectors.groupingBy(
                        employee -> employee.getOrganization().getId(),
                        Collectors.counting()
                ));
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<Employee> findVisibleById(Long id) {
        if (id == null) {
            throw new IllegalArgumentException("employeeId cannot be null");
        }

        return findVisibleEmployees().stream()
                .filter(employee -> id.equals(employee.getId()))
                .findFirst();
    }

    @Override
    public Optional<Employee> findById(Long id) {
        return repo.findById(id);
    }

    @Override
    public Employee createEmployee(EmployeeCreateRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("Employee create request cannot be null");
        }

        Organization organization = getVisibleOrganizationOrThrow(request.getOrganizationId());

        Employee employee = request.toEmployee();
        employee.setOrganization(organization);

        return repo.save(employee);
    }

    @Override
    public Employee updateVisibleEmployee(Long id, EmployeeUpdateRequest request) {
        if (request == null) {
            throw new IllegalArgumentException("Employee update request cannot be null");
        }

        Employee existing = findVisibleById(id)
                .orElseThrow(() -> new IllegalArgumentException("Employee not found or not visible: " + id));

        request.applyTo(existing);

        if (request.getOrganizationId() != null) {
            Organization organization = getVisibleOrganizationOrThrow(request.getOrganizationId());
            existing.setOrganization(organization);
        }

        return repo.save(existing);
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

        for (Employee employee : list) {
            Long organizationId = employee.getOrganization() == null
                    ? null
                    : employee.getOrganization().getId();

            Organization organization = getVisibleOrganizationOrThrow(organizationId);
            employee.setOrganization(organization);
        }

        return repo.saveAll(list);
    }

    @Override
    public byte[] exportToExcel() throws IOException {
        List<Employee> list = repo.findAll();
        return ExcelUtil.employeesToExcel(list);
    }

    @Override
    @Transactional(readOnly = true)
    public byte[] exportVisibleToExcel() throws IOException {
        List<Employee> list = findVisibleEmployees();
        return ExcelUtil.employeesToExcel(list);
    }
}