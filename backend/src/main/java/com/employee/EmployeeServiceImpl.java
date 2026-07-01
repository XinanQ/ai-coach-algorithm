package com.employee;

import com.auth.CurrentUserContext;
import com.employee.dto.EmployeeCreateRequest;
import com.employee.dto.EmployeeImportPreviewItem;
import com.employee.dto.EmployeeImportPreviewResponse;
import com.employee.dto.EmployeeUpdateRequest;
import com.organization.Organization;
import com.organization.OrganizationService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
        EmployeeLevelResolver.applyInferredLevel(employee);

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

        EmployeeLevelResolver.applyInferredLevel(existing);

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
        List<ExcelUtil.ParsedEmployeeRow> rows = ExcelUtil.parseEmployeeRows(file.getInputStream());
        List<Long> visibleOrganizationIds = getVisibleOrganizationIds();
        Map<Long, Organization> orgById = organizationService.findVisibleOrganizations().stream()
                .collect(Collectors.toMap(Organization::getId, org -> org, (a, b) -> a));
        Map<String, Organization> orgByName = buildOrganizationByName(orgById.values());

        List<Employee> toSave = new ArrayList<>();
        for (ExcelUtil.ParsedEmployeeRow parsedRow : rows) {
            Employee employee = parsedRow.employee();
            String error = resolveAndAttachOrganization(
                    employee, visibleOrganizationIds, orgById, orgByName);
            if (error != null) {
                throw new IllegalArgumentException("第 " + parsedRow.rowIndex() + " 行：" + error);
            }
            toSave.add(employee);
        }

        return repo.saveAll(toSave);
    }

    @Override
    @Transactional(readOnly = true)
    public EmployeeImportPreviewResponse previewImport(MultipartFile file) throws IOException {
        List<ExcelUtil.ParsedEmployeeRow> rows = ExcelUtil.parseEmployeeRows(file.getInputStream());
        List<Long> visibleOrganizationIds = getVisibleOrganizationIds();
        Map<Long, Organization> orgById = organizationService.findVisibleOrganizations().stream()
                .collect(Collectors.toMap(Organization::getId, org -> org, (a, b) -> a));
        Map<String, Organization> orgByName = buildOrganizationByName(orgById.values());

        EmployeeImportPreviewResponse response = new EmployeeImportPreviewResponse();
        List<EmployeeImportPreviewItem> items = new ArrayList<>();
        int validCount = 0;
        int invalidCount = 0;

        for (ExcelUtil.ParsedEmployeeRow parsedRow : rows) {
            Employee employee = parsedRow.employee();
            EmployeeImportPreviewItem item = new EmployeeImportPreviewItem();
            item.setRowIndex(parsedRow.rowIndex());
            item.setName(employee.getName());
            item.setEmail(employee.getEmail());
            item.setPosition(employee.getPosition());
            item.setAge(employee.getAge());
            item.setDepartment(employee.getDepartment());
            item.setWorkType(employee.getWorkType());
            item.setIsNew(employee.getIsNew());
            item.setIsAdmin(employee.getIsAdmin());
            item.setIsInProject(employee.getIsInProject());

            if (employee.getOrganization() != null && employee.getOrganization().getName() != null) {
                item.setOrganizationName(employee.getOrganization().getName());
            }

            String error = resolveAndAttachOrganization(
                    employee, visibleOrganizationIds, orgById, orgByName);
            if (employee.getOrganization() != null) {
                item.setOrganizationId(employee.getOrganization().getId());
                item.setOrganizationName(employee.getOrganization().getName());
            }
            item.setLevel(employee.getLevel());

            if (error == null) {
                item.setValid(true);
                validCount++;
            } else {
                item.setValid(false);
                item.setErrorMessage(error);
                invalidCount++;
            }
            items.add(item);
        }

        response.setItems(items);
        response.setValidCount(validCount);
        response.setInvalidCount(invalidCount);
        return response;
    }

    @Override
    @Transactional(readOnly = true)
    public byte[] exportImportTemplate() throws IOException {
        return ExcelUtil.buildImportTemplate(organizationService.findVisibleOrganizations());
    }

    private Map<String, Organization> buildOrganizationByName(Iterable<Organization> organizations) {
        Map<String, Organization> orgByName = new HashMap<>();
        for (Organization org : organizations) {
            if (org.getName() != null && !org.getName().isBlank()) {
                orgByName.putIfAbsent(org.getName().trim(), org);
            }
        }
        return orgByName;
    }

    /**
     * 解析 Excel 中的机构：优先机构ID，否则按机构名称匹配；成功则写回 employee.organization。
     */
    private String resolveAndAttachOrganization(Employee employee,
                                                List<Long> visibleOrganizationIds,
                                                Map<Long, Organization> orgById,
                                                Map<String, Organization> orgByName) {
        if (employee.getName() == null || employee.getName().isBlank()) {
            return "姓名不能为空";
        }
        if ("示例员工".equals(employee.getName().trim())) {
            return "请删除模板中的示例行后再导入";
        }
        if (employee.getEmail() == null || employee.getEmail().isBlank()) {
            return "邮箱不能为空";
        }

        Organization input = employee.getOrganization();
        if (input == null) {
            return "所属机构不能为空，请填写机构名称或从下拉选择";
        }

        Organization resolved = null;
        if (input.getId() != null) {
            resolved = orgById.get(input.getId());
            if (resolved == null) {
                return "机构ID不存在: " + input.getId();
            }
        } else if (input.getName() != null && !input.getName().isBlank()) {
            resolved = orgByName.get(input.getName().trim());
            if (resolved == null) {
                return "机构名称不存在: " + input.getName().trim() + "（请从下拉列表选择所属机构）";
            }
        } else {
            return "所属机构不能为空，请填写机构名称或从下拉选择";
        }

        if (!visibleOrganizationIds.contains(resolved.getId())) {
            return "无权操作该机构: " + resolved.getName();
        }

        employee.setOrganization(resolved);
        EmployeeLevelResolver.applyInferredLevel(employee);
        return null;
    }

    @Override
    public byte[] exportToExcel() throws IOException {
        List<Employee> list = repo.findAll();
        return ExcelUtil.employeesToExcel(list);
    }

    @Override
    @Transactional(readOnly = true)
    public byte[] exportVisibleToExcel() throws IOException {
        List<Long> visibleOrganizationIds = getVisibleOrganizationIds();
        List<Employee> list = repo.findByOrganization_IdInWithOrganization(visibleOrganizationIds);
        return ExcelUtil.employeesToExcel(list);
    }
}