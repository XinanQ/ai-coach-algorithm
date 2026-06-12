package com.project;

import com.indicator.IndicatorRepository;
import com.project.dto.ProjectIndicatorCreateRequest;
import com.project.dto.ProjectIndicatorResponse;
import com.project.dto.ProjectIndicatorUpdateRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional
public class ProjectIndicatorServiceImpl implements ProjectIndicatorService {

    private final ProjectIndicatorRepository projectIndicatorRepo;
    private final ProjectRepository projectRepo;
    private final IndicatorRepository indicatorRepo;

    public ProjectIndicatorServiceImpl(ProjectIndicatorRepository projectIndicatorRepo,
                                       ProjectRepository projectRepo,
                                       IndicatorRepository indicatorRepo) {
        this.projectIndicatorRepo = projectIndicatorRepo;
        this.projectRepo = projectRepo;
        this.indicatorRepo = indicatorRepo;
    }

    @Override
    @Transactional(readOnly = true)
    public List<ProjectIndicatorResponse> listByProject(Long projectId) {
        ensureProjectExists(projectId);
        return projectIndicatorRepo.findByProjectIdOrderBySortOrderAscIdAsc(projectId).stream()
                .map(this::toResponse)
                .toList();
    }

    @Override
    @Transactional(readOnly = true)
    public ProjectIndicatorResponse get(Long projectId, Long id) {
        ensureProjectExists(projectId);
        return toResponse(findLinkInProject(projectId, id));
    }

    @Override
    public ProjectIndicatorResponse create(Long projectId, ProjectIndicatorCreateRequest req) {
        ensureProjectExists(projectId);
        if (req == null || req.getIndicatorId() == null) {
            throw new IllegalArgumentException("indicatorId 不能为空");
        }
        Long indicatorId = req.getIndicatorId();
        if (!indicatorRepo.existsById(indicatorId)) {
            throw new IllegalArgumentException("指标不存在: " + indicatorId);
        }
        if (projectIndicatorRepo.existsByProjectIdAndIndicatorId(projectId, indicatorId)) {
            throw new IllegalArgumentException("该项目已挂接该指标");
        }

        ProjectIndicator link = new ProjectIndicator();
        link.setProjectId(projectId);
        link.setIndicatorId(indicatorId);
        applyCreateFields(link, req);
        return toResponse(projectIndicatorRepo.save(link));
    }

    @Override
    public ProjectIndicatorResponse update(Long projectId, Long id, ProjectIndicatorUpdateRequest req) {
        ensureProjectExists(projectId);
        ProjectIndicator link = findLinkInProject(projectId, id);
        if (req != null) {
            applyUpdateFields(link, req);
        }
        return toResponse(projectIndicatorRepo.save(link));
    }

    @Override
    public void delete(Long projectId, Long id) {
        ensureProjectExists(projectId);
        ProjectIndicator link = findLinkInProject(projectId, id);
        projectIndicatorRepo.delete(link);
    }

    private void ensureProjectExists(Long projectId) {
        if (!projectRepo.existsById(projectId)) {
            throw new IllegalArgumentException("项目不存在: " + projectId);
        }
    }

    private ProjectIndicator findLinkInProject(Long projectId, Long id) {
        return projectIndicatorRepo.findByIdAndProjectId(id, projectId)
                .orElseThrow(() -> new IllegalArgumentException("项目指标挂接不存在: " + id));
    }

    private void applyCreateFields(ProjectIndicator link, ProjectIndicatorCreateRequest req) {
        link.setUnit(req.getUnit());
        link.setRatio(req.getRatio());
        link.setPointsStandard(req.getPointsStandard());
        link.setPointsUnit(req.getPointsUnit());
        link.setBigOrderThreshold(req.getBigOrderThreshold());
        link.setMarketingStarQuota(req.getMarketingStarQuota());
        link.setIndicatorType(req.getIndicatorType());
        link.setTargetValue(req.getTargetValue());
        link.setSortOrder(req.getSortOrder());
    }

    private void applyUpdateFields(ProjectIndicator link, ProjectIndicatorUpdateRequest req) {
        if (req.getUnit() != null) {
            link.setUnit(req.getUnit());
        }
        if (req.getRatio() != null) {
            link.setRatio(req.getRatio());
        }
        if (req.getPointsStandard() != null) {
            link.setPointsStandard(req.getPointsStandard());
        }
        if (req.getPointsUnit() != null) {
            link.setPointsUnit(req.getPointsUnit());
        }
        if (req.getBigOrderThreshold() != null) {
            link.setBigOrderThreshold(req.getBigOrderThreshold());
        }
        if (req.getMarketingStarQuota() != null) {
            link.setMarketingStarQuota(req.getMarketingStarQuota());
        }
        if (req.getIndicatorType() != null) {
            link.setIndicatorType(req.getIndicatorType());
        }
        if (req.getTargetValue() != null) {
            link.setTargetValue(req.getTargetValue());
        }
        if (req.getSortOrder() != null) {
            link.setSortOrder(req.getSortOrder());
        }
    }

    private ProjectIndicatorResponse toResponse(ProjectIndicator link) {
        ProjectIndicatorResponse r = new ProjectIndicatorResponse();
        r.setId(link.getId());
        r.setProjectId(link.getProjectId());
        r.setIndicatorId(link.getIndicatorId());
        r.setUnit(link.getUnit());
        r.setRatio(link.getRatio());
        r.setPointsStandard(link.getPointsStandard());
        r.setPointsUnit(link.getPointsUnit());
        r.setBigOrderThreshold(link.getBigOrderThreshold());
        r.setMarketingStarQuota(link.getMarketingStarQuota());
        r.setIndicatorType(link.getIndicatorType());
        r.setTargetValue(link.getTargetValue());
        r.setSortOrder(link.getSortOrder());
        r.setCreatedAt(link.getCreatedAt());
        r.setUpdatedAt(link.getUpdatedAt());

        indicatorRepo.findById(link.getIndicatorId()).ifPresent(indicator -> {
            r.setIndicatorName(indicator.getName());
            r.setIndicatorCode(indicator.getCode());
        });
        return r;
    }
}
