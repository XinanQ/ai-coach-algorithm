package com.performance;

import com.auth.CurrentUserContext;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.performance.dto.ReportReviewItemResponse;
import com.performance.dto.ReportUpdateRequest;
import com.points.PointsCalculationService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Transactional
public class PerformanceServiceImpl implements PerformanceService {

    private final TaskResultRepository repo;
    private final PointsCalculationService pointsCalculationService;
    private final EmployeeRepository employeeRepository;
    private final ReviewScopeService reviewScopeService;

    public PerformanceServiceImpl(TaskResultRepository repo,
                                  PointsCalculationService pointsCalculationService,
                                  EmployeeRepository employeeRepository,
                                  ReviewScopeService reviewScopeService) {
        this.repo = repo;
        this.pointsCalculationService = pointsCalculationService;
        this.employeeRepository = employeeRepository;
        this.reviewScopeService = reviewScopeService;
    }

    @Override
    public TaskResult submitReport(TaskResult report) {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId == null) {
            throw new IllegalArgumentException("未登录，无法提交上报");
        }
        if (report.getSubmitterId() != null && !report.getSubmitterId().equals(currentId)) {
            throw new IllegalArgumentException("只能提交本人业绩上报");
        }

        Employee current = employeeRepository.findByIdWithOrganization(currentId).orElse(null);
        if (current != null && isCityOrBranchAdminLevel(current.getLevel())) {
            throw new IllegalArgumentException("CITY和BRANCH账号无需提交业绩上报，请在Web端审核员工上报");
        }
        report.setSubmitterId(currentId);
        if (current != null && (report.getSubmitter() == null || report.getSubmitter().isBlank())) {
            report.setSubmitter(current.getName());
        }
        if (current != null && current.getOrganization() != null && report.getOrganizationId() == null) {
            report.setOrganizationId(current.getOrganization().getId());
        }

        report.setStatus(TaskResultStatus.PENDING);
        report.setReceivedAt(LocalDateTime.now());
        return repo.save(report);
    }

    @Override
    @Transactional(readOnly = true)
    public List<ReportReviewItemResponse> listAll() {
        return toReviewItems(filterByViewableScope(repo.findAll()));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ReportReviewItemResponse> listByStatus(TaskResultStatus status) {
        return toReviewItems(filterByViewableScope(repo.findByStatus(status)));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ReportReviewItemResponse> listBySubmitter(Long submitterId) {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId != null && currentId.equals(submitterId)) {
            return toReviewItems(repo.findBySubmitterId(submitterId));
        }
        return toReviewItems(filterByViewableScope(repo.findBySubmitterId(submitterId)));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ReportReviewItemResponse> listByDateRange(LocalDate from, LocalDate to) {
        return toReviewItems(filterByViewableScope(repo.findByReportDateBetween(from, to)));
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<TaskResult> findById(Long id) {
        return repo.findById(id).filter(this::canAccessReport);
    }

    @Override
    public TaskResult updateReport(Long id, ReportUpdateRequest report) {
        return findById(id).map(existing -> {
            if (existing.getStatus() != TaskResultStatus.PENDING) {
                throw new IllegalArgumentException("仅待审核记录可修改");
            }
            if (!canUpdateReport(existing)) {
                throw new IllegalArgumentException("无权限修改该上报记录");
            }

            Long currentId = CurrentUserContext.getEmployeeId();
            boolean isSubmitter = currentId != null && currentId.equals(existing.getSubmitterId());

            if (isSubmitter) {
                if (report.getTaskId() != null) {
                    existing.setTaskId(report.getTaskId());
                }
                if (report.getProjectId() != null) {
                    existing.setProjectId(report.getProjectId());
                }
                if (report.getIndicatorId() != null) {
                    existing.setIndicatorId(report.getIndicatorId());
                }
                if (report.getOrganizationId() != null) {
                    existing.setOrganizationId(report.getOrganizationId());
                }
                if (report.getSubmitter() != null) {
                    existing.setSubmitter(report.getSubmitter());
                }
                if (report.getReportDate() != null) {
                    existing.setReportDate(report.getReportDate());
                }
                if (report.getResult() != null) {
                    existing.setResult(report.getResult());
                }
                if (report.getAttachmentUrl() != null) {
                    existing.setAttachmentUrl(report.getAttachmentUrl());
                }
            } else {
                // 审核管理员修改：与通过/驳回同权限，仅允许改正报内容字段
                if (report.getReportDate() != null) {
                    existing.setReportDate(report.getReportDate());
                }
                if (report.getResult() != null) {
                    existing.setResult(report.getResult());
                }
                if (report.getAttachmentUrl() != null) {
                    existing.setAttachmentUrl(report.getAttachmentUrl());
                }
            }

            if (existing.getResult() == null || existing.getResult().isBlank()) {
                throw new IllegalArgumentException("上报数量不能为空");
            }
            if (existing.getReportDate() == null) {
                throw new IllegalArgumentException("上报日期不能为空");
            }

            return repo.save(existing);
        }).orElse(null);
    }

    @Override
    public void deleteById(Long id) {
        findById(id).ifPresent(r -> repo.deleteById(id));
    }

    @Override
    public TaskResult approve(Long id, String reviewer, String comment) {
        TaskResult report = repo.findById(id).orElse(null);
        if (report == null) {
            return null;
        }
        assertCanReview(report);
        if (report.getStatus() != TaskResultStatus.PENDING) {
            throw new IllegalArgumentException("仅待审核记录可通过审核");
        }

        report.setStatus(TaskResultStatus.APPROVED);
        report.setAuditedBy(resolveAuditorName(reviewer));
        report.setAuditComment(comment);
        report.setAuditedAt(LocalDateTime.now());
        TaskResult saved = repo.save(report);
        pointsCalculationService.calculateOnApprove(saved);
        return saved;
    }

    @Override
    public TaskResult reject(Long id, String reviewer, String reason) {
        TaskResult report = repo.findById(id).orElse(null);
        if (report == null) {
            return null;
        }
        assertCanReview(report);
        if (report.getStatus() != TaskResultStatus.PENDING) {
            throw new IllegalArgumentException("仅待审核记录可驳回");
        }

        report.setStatus(TaskResultStatus.REJECTED);
        report.setAuditedBy(resolveAuditorName(reviewer));
        report.setAuditComment(reason);
        report.setAuditedAt(LocalDateTime.now());
        return repo.save(report);
    }

    private String resolveAuditorName(String reviewerParam) {
        Employee current = employeeRepository.findByIdWithOrganization(CurrentUserContext.getEmployeeId())
                .orElse(null);
        if (current != null && current.getName() != null && !current.getName().isBlank()) {
            return current.getName();
        }
        if (reviewerParam != null && !reviewerParam.isBlank()) {
            return reviewerParam;
        }
        return "admin";
    }

    private boolean isCityOrBranchAdminLevel(String level) {
        if (level == null || level.isBlank()) {
            return false;
        }
        String normalized = level.trim().toUpperCase();
        return "CITY".equals(normalized) || "BRANCH".equals(normalized);
    }

    private void assertCanReview(TaskResult report) {
        if (!canReviewReport(report)) {
            throw new IllegalArgumentException("无权限审核该机构的上报记录");
        }
    }

    private boolean canUpdateReport(TaskResult report) {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId == null) {
            return false;
        }
        if (currentId.equals(report.getSubmitterId())) {
            return true;
        }
        return canReviewReport(report);
    }

    private boolean canReviewReport(TaskResult report) {
        Long reviewerId = CurrentUserContext.getEmployeeId();
        if (reviewerId == null || report.getSubmitterId() == null) {
            return false;
        }

        Employee reviewer = employeeRepository.findByIdWithOrganization(reviewerId).orElse(null);
        if (!reviewScopeService.isReviewAdmin(reviewer)) {
            return false;
        }

        Employee submitter = employeeRepository.findByIdWithOrganization(report.getSubmitterId()).orElse(null);
        Long submitterOrgId = resolveSubmitterOrgId(report, submitter);
        if (submitterOrgId == null) {
            return false;
        }

        return reviewScopeService.canReviewSubmitterOrg(reviewer, submitterOrgId);
    }

    private boolean canAccessReport(TaskResult report) {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId != null && currentId.equals(report.getSubmitterId())) {
            return true;
        }
        return canReviewReport(report);
    }

    private List<TaskResult> filterByViewableScope(List<TaskResult> reports) {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId == null) {
            return List.of();
        }

        Employee current = employeeRepository.findByIdWithOrganization(currentId).orElse(null);
        if (current == null) {
            return List.of();
        }

        if (!reviewScopeService.isReviewAdmin(current)) {
            return reports.stream()
                    .filter(r -> currentId.equals(r.getSubmitterId()))
                    .collect(Collectors.toList());
        }

        Set<Long> visibleOrgIds = reviewScopeService.resolveViewableOrgIds(current);
        if (visibleOrgIds.isEmpty()) {
            return List.of();
        }

        Map<Long, Long> submitterOrgMap = loadSubmitterOrgMap(reports);

        return reports.stream()
                .filter(r -> {
                    Long orgId = resolveSubmitterOrgId(r, submitterOrgMap);
                    return orgId != null && visibleOrgIds.contains(orgId);
                })
                .collect(Collectors.toList());
    }

    private List<ReportReviewItemResponse> toReviewItems(List<TaskResult> reports) {
        Employee current = employeeRepository.findByIdWithOrganization(CurrentUserContext.getEmployeeId())
                .orElse(null);
        Map<Long, Long> submitterOrgMap = loadSubmitterOrgMap(reports);

        return reports.stream()
                .map(report -> {
                    boolean canReview = false;
                    if (current != null && reviewScopeService.isReviewAdmin(current)
                            && report.getStatus() == TaskResultStatus.PENDING) {
                        Long submitterOrgId = resolveSubmitterOrgId(report, submitterOrgMap);
                        canReview = submitterOrgId != null
                                && reviewScopeService.canReviewSubmitterOrg(current, submitterOrgId);
                    }
                    return ReportReviewItemResponse.from(report, canReview);
                })
                .collect(Collectors.toList());
    }

    private Long resolveSubmitterOrgId(TaskResult report, Map<Long, Long> submitterOrgMap) {
        if (report.getSubmitterId() != null) {
            Long orgId = submitterOrgMap.get(report.getSubmitterId());
            if (orgId != null) {
                return orgId;
            }
        }
        return report.getOrganizationId();
    }

    private Long resolveSubmitterOrgId(TaskResult report, Employee submitter) {
        if (submitter != null && submitter.getOrganization() != null) {
            return submitter.getOrganization().getId();
        }
        return report.getOrganizationId();
    }

    private Map<Long, Long> loadSubmitterOrgMap(List<TaskResult> reports) {
        Set<Long> submitterIds = reports.stream()
                .map(TaskResult::getSubmitterId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        if (submitterIds.isEmpty()) {
            return Map.of();
        }

        Map<Long, Long> result = new HashMap<>();
        for (Long submitterId : submitterIds) {
            employeeRepository.findByIdWithOrganization(submitterId).ifPresent(employee -> {
                if (employee.getOrganization() != null) {
                    result.put(employee.getId(), employee.getOrganization().getId());
                }
            });
        }
        return result;
    }
}
