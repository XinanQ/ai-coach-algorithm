package com.indicator;

import com.employee.EmployeeRepository;
import com.indicator.dto.*;
import com.organization.OrganizationRepository;
import com.project.ProjectIndicatorRepository;
import com.performance.TaskResult;
import com.performance.TaskResultRepository;
import com.performance.TaskResultStatus;
import com.task.Task;
import com.task.TaskRepository;
import jakarta.persistence.criteria.Predicate;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
@Transactional
public class IndicatorServiceImpl implements IndicatorService {

    private final IndicatorRepository indicatorRepo;
    private final TaskRepository taskRepo;
    private final TaskResultRepository taskResultRepo;
    private final OrganizationRepository organizationRepo;
    private final EmployeeRepository employeeRepo;
    private final ProjectIndicatorRepository projectIndicatorRepo;

    public IndicatorServiceImpl(IndicatorRepository indicatorRepo,
                                TaskRepository taskRepo,
                                TaskResultRepository taskResultRepo,
                                OrganizationRepository organizationRepo,
                                EmployeeRepository employeeRepo,
                                ProjectIndicatorRepository projectIndicatorRepo) {
        this.indicatorRepo = indicatorRepo;
        this.taskRepo = taskRepo;
        this.taskResultRepo = taskResultRepo;
        this.organizationRepo = organizationRepo;
        this.employeeRepo = employeeRepo;
        this.projectIndicatorRepo = projectIndicatorRepo;
    }

    @Override
    @Transactional(readOnly = true)
    public Page<IndicatorResponse> listLibrary(String businessLine, Boolean enabled,
                                               String category, String keyword,
                                               int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "id"));
        Specification<Indicator> spec = buildSpec(businessLine, enabled, category, keyword);
        return indicatorRepo.findAll(spec, pageable).map(this::toResponse);
    }

    @Override
    @Transactional(readOnly = true)
    public IndicatorResponse getLibraryById(Long id) {
        Indicator indicator = indicatorRepo.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("指标不存在: " + id));
        return toResponse(indicator);
    }

    @Override
    public IndicatorResponse createLibrary(IndicatorCreateRequest req) {
        validateCreate(req);
        String code = req.getCode().trim();
        if (indicatorRepo.existsByCode(code)) {
            throw new IllegalArgumentException("指标编码已存在: " + code);
        }

        Indicator indicator = new Indicator();
        indicator.setName(req.getName().trim());
        indicator.setCode(code);
        indicator.setUnit(req.getUnit());
        indicator.setCategory(req.getCategory());
        indicator.setBusinessLine(req.getBusinessLine());
        indicator.setDescription(req.getDescription());
        indicator.setEnabled(req.getEnabled() != null ? req.getEnabled() : true);

        return toResponse(indicatorRepo.save(indicator));
    }

    @Override
    public IndicatorResponse updateLibrary(Long id, IndicatorUpdateRequest req) {
        Indicator indicator = indicatorRepo.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("指标不存在: " + id));

        validateUpdate(req);
        String code = req.getCode().trim();
        if (indicatorRepo.existsByCodeAndIdNot(code, id)) {
            throw new IllegalArgumentException("指标编码已存在: " + code);
        }

        indicator.setName(req.getName().trim());
        indicator.setCode(code);
        indicator.setUnit(req.getUnit());
        indicator.setCategory(req.getCategory());
        indicator.setBusinessLine(req.getBusinessLine());
        indicator.setDescription(req.getDescription());
        if (req.getEnabled() != null) {
            indicator.setEnabled(req.getEnabled());
        }

        return toResponse(indicatorRepo.save(indicator));
    }

    @Override
    public IndicatorResponse updateLibraryStatus(Long id, IndicatorStatusRequest req) {
        if (req.getEnabled() == null) {
            throw new IllegalArgumentException("enabled 不能为空");
        }
        Indicator indicator = indicatorRepo.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("指标不存在: " + id));
        indicator.setEnabled(req.getEnabled());
        return toResponse(indicatorRepo.save(indicator));
    }

    @Override
    public void deleteLibrary(Long id) {
        if (!indicatorRepo.existsById(id)) {
            throw new IllegalArgumentException("指标不存在: " + id);
        }
        if (projectIndicatorRepo.existsByIndicatorId(id)) {
            throw new IllegalArgumentException("该指标已被项目挂接，无法删除；请先在相关项目中移除该指标后再删除");
        }
        indicatorRepo.deleteById(id);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Indicator> findChildren(Long parentId) {
        return indicatorRepo.findByParentId(parentId);
    }

    @Override
    @Transactional(readOnly = true)
    public IndicatorProgressResponse getProgress(Long id) {
        Indicator root = indicatorRepo.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("指标不存在: " + id));
        return buildProgress(root);
    }

    private IndicatorProgressResponse toProgressResponse(Indicator e) {
        IndicatorProgressResponse r = new IndicatorProgressResponse();
        r.setId(e.getId());
        r.setName(e.getName());
        r.setCode(e.getCode());
        r.setUnit(e.getUnit());
        r.setCategory(e.getCategory());
        r.setBusinessLine(e.getBusinessLine());
        r.setDescription(e.getDescription());
        r.setTargetValue(e.getTargetValue());
        r.setTargetOrgId(e.getTargetOrgId());
        r.setTargetEmployeeId(e.getTargetEmployeeId());
        r.setParentId(e.getParentId());
        r.setLevel(e.getLevel());
        r.setStatus(e.getStatus());
        r.setEnabled(e.getEnabled());
        r.setCreatedAt(e.getCreatedAt());
        r.setUpdatedAt(e.getUpdatedAt());
        return r;
    }

    private IndicatorProgressResponse buildProgress(Indicator indicator) {
        IndicatorProgressResponse response = toProgressResponse(indicator);
        BigDecimal completedValue = computeCompletedValue(indicator);
        response.setCompletedValue(completedValue);
        if (indicator.getTargetValue() != null && indicator.getTargetValue().compareTo(BigDecimal.ZERO) > 0) {
            response.setPercentComplete(completedValue
                    .divide(indicator.getTargetValue(), 4, RoundingMode.HALF_UP)
                    .multiply(BigDecimal.valueOf(100)));
        } else {
            response.setPercentComplete(BigDecimal.ZERO);
        }

        List<IndicatorProgressResponse> children = new ArrayList<>();
        for (Indicator child : indicatorRepo.findByParentId(indicator.getId())) {
            children.add(buildProgress(child));
        }
        response.setChildren(children);
        return response;
    }

    private BigDecimal computeCompletedValue(Indicator indicator) {
        List<TaskResult> reports;
        if (indicator.getTargetEmployeeId() != null) {
            reports = taskResultRepo.findByIndicatorIdAndSubmitterIdAndStatus(
                    indicator.getId(), indicator.getTargetEmployeeId(), TaskResultStatus.APPROVED);
        } else if (indicator.getTargetOrgId() != null) {
            List<Long> orgIds = collectOrganizationAndDescendants(indicator.getTargetOrgId());
            reports = taskResultRepo.findByIndicatorIdAndOrganizationIdInAndStatus(
                    indicator.getId(), orgIds, TaskResultStatus.APPROVED);
        } else {
            reports = taskResultRepo.findByIndicatorIdAndStatus(indicator.getId(), TaskResultStatus.APPROVED);
        }
        return reports.stream()
                .map(this::parseReportValue)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    private BigDecimal parseReportValue(TaskResult report) {
        if (report == null || report.getResult() == null) {
            return BigDecimal.ZERO;
        }
        String text = report.getResult().trim();
        Matcher matcher = Pattern.compile("[-+]?(?:\\d+\\.\\d*|\\.\\d+)").matcher(text);
        if (matcher.find()) {
            try {
                return new BigDecimal(matcher.group());
            } catch (NumberFormatException e) {
                return BigDecimal.ZERO;
            }
        }
        return BigDecimal.ZERO;
    }

    private List<Long> collectOrganizationAndDescendants(Long rootOrgId) {
        List<Long> ids = new ArrayList<>();
        ids.add(rootOrgId);
        collectDescendants(rootOrgId, ids);
        return ids;
    }

    private void collectDescendants(Long parentId, List<Long> ids) {
        List<com.organization.Organization> children = organizationRepo.findByParentId(parentId);
        for (com.organization.Organization child : children) {
            ids.add(child.getId());
            collectDescendants(child.getId(), ids);
        }
    }

    @Override
    public Indicator decompose(Long id, Indicator child) {
        if (child.getTargetOrgId() != null && child.getTargetEmployeeId() != null) {
            throw new IllegalArgumentException("targetOrgId 和 targetEmployeeId 不能同时设置");
        }
        if (child.getTargetValue() == null) {
            throw new IllegalArgumentException("目标值 targetValue 不能为空");
        }
        child.setParentId(id);
        if (child.getLevel() == null) {
            indicatorRepo.findById(id).ifPresent(parent -> child.setLevel((parent.getLevel() == null ? 0 : parent.getLevel()) + 1));
        }
        if (child.getStatus() == null) {
            child.setStatus("OPEN");
        }
        Indicator saved = indicatorRepo.save(child);
        Task t = new Task();
        t.setType("INDICATOR_DECOMPOSE");
        t.setTitle("Indicator decomposition created");
        t.setTargetType("INDICATOR");
        t.setTargetId(saved.getId());
        t.setPayload("ParentId=" + id + ";ChildId=" + saved.getId());
        t.setStatus("OPEN");
        t.setCreatedAt(LocalDateTime.now());
        t.setUpdatedAt(LocalDateTime.now());
        taskRepo.save(t);
        return saved;
    }

    @Override
    public void remind(Long id, String message) {
        Task t = new Task();
        t.setType("REMINDER");
        t.setTitle("Indicator reminder");
        t.setTargetType("INDICATOR");
        t.setTargetId(id);
        t.setPayload(message);
        t.setStatus("OPEN");
        t.setCreatedAt(LocalDateTime.now());
        t.setUpdatedAt(LocalDateTime.now());
        taskRepo.save(t);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Task> findReminders(Long indicatorId) {
        return taskRepo.findByTypeAndTargetTypeAndTargetId("REMINDER", "INDICATOR", indicatorId);
    }

    private void validateCreate(IndicatorCreateRequest req) {
        if (req == null) {
            throw new IllegalArgumentException("请求不能为空");
        }
        if (!StringUtils.hasText(req.getName())) {
            throw new IllegalArgumentException("指标名称不能为空");
        }
        if (!StringUtils.hasText(req.getCode())) {
            throw new IllegalArgumentException("指标编码不能为空");
        }
    }

    private void validateUpdate(IndicatorUpdateRequest req) {
        if (req == null) {
            throw new IllegalArgumentException("请求不能为空");
        }
        if (!StringUtils.hasText(req.getName())) {
            throw new IllegalArgumentException("指标名称不能为空");
        }
        if (!StringUtils.hasText(req.getCode())) {
            throw new IllegalArgumentException("指标编码不能为空");
        }
    }

    private Specification<Indicator> buildSpec(String businessLine, Boolean enabled,
                                                 String category, String keyword) {
        return (root, query, cb) -> {
            List<Predicate> predicates = new ArrayList<>();
            if (StringUtils.hasText(businessLine)) {
                predicates.add(cb.equal(root.get("businessLine"), businessLine.trim()));
            }
            if (enabled != null) {
                predicates.add(cb.equal(root.get("enabled"), enabled));
            }
            if (StringUtils.hasText(category)) {
                predicates.add(cb.equal(root.get("category"), category.trim()));
            }
            if (StringUtils.hasText(keyword)) {
                String pattern = "%" + keyword.trim() + "%";
                predicates.add(cb.or(
                        cb.like(root.get("name"), pattern),
                        cb.like(root.get("code"), pattern)
                ));
            }
            return cb.and(predicates.toArray(new Predicate[0]));
        };
    }

    private IndicatorResponse toResponse(Indicator e) {
        IndicatorResponse r = new IndicatorResponse();
        r.setId(e.getId());
        r.setName(e.getName());
        r.setCode(e.getCode());
        r.setUnit(e.getUnit());
        r.setCategory(e.getCategory());
        r.setBusinessLine(e.getBusinessLine());
        r.setDescription(e.getDescription());
        r.setTargetValue(e.getTargetValue());
        r.setTargetOrgId(e.getTargetOrgId());
        r.setTargetEmployeeId(e.getTargetEmployeeId());
        r.setParentId(e.getParentId());
        r.setLevel(e.getLevel());
        r.setStatus(e.getStatus());
        r.setEnabled(e.getEnabled());
        r.setCreatedAt(e.getCreatedAt());
        r.setUpdatedAt(e.getUpdatedAt());
        return r;
    }
}
