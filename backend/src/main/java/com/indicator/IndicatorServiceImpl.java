package com.indicator;

import com.indicator.dto.*;
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

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
@Transactional
public class IndicatorServiceImpl implements IndicatorService {

    private final IndicatorRepository indicatorRepo;
    private final TaskRepository taskRepo;

    public IndicatorServiceImpl(IndicatorRepository indicatorRepo, TaskRepository taskRepo) {
        this.indicatorRepo = indicatorRepo;
        this.taskRepo = taskRepo;
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
        indicatorRepo.deleteById(id);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Indicator> findChildren(Long parentId) {
        return indicatorRepo.findByParentId(parentId);
    }

    @Override
    public Indicator decompose(Long id, Indicator child) {
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
        r.setEnabled(e.getEnabled());
        r.setCreatedAt(e.getCreatedAt());
        r.setUpdatedAt(e.getUpdatedAt());
        return r;
    }
}
