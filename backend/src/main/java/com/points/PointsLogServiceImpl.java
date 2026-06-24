package com.points;

import com.auth.CurrentUserContext;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.performance.PerformanceService;
import com.performance.ReviewScopeService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
@Transactional(readOnly = true)
public class PointsLogServiceImpl implements PointsLogService {

    private final PointsLogRepository pointsLogRepo;
    private final PerformanceService performanceService;
    private final EmployeeRepository employeeRepository;
    private final ReviewScopeService reviewScopeService;

    public PointsLogServiceImpl(PointsLogRepository pointsLogRepo,
                                PerformanceService performanceService,
                                EmployeeRepository employeeRepository,
                                ReviewScopeService reviewScopeService) {
        this.pointsLogRepo = pointsLogRepo;
        this.performanceService = performanceService;
        this.employeeRepository = employeeRepository;
        this.reviewScopeService = reviewScopeService;
    }

    @Override
    public List<PointsLog> listVisible(Long reportId, Long employeeId) {
        if (reportId != null) {
            return performanceService.findById(reportId)
                    .map(report -> pointsLogRepo.findByReportId(report.getId()))
                    .orElse(List.of());
        }
        if (employeeId != null) {
            return listByEmployeeId(employeeId);
        }
        return listInVisibleScope();
    }

    private List<PointsLog> listByEmployeeId(Long employeeId) {
        if (!canAccessEmployeeLogs(employeeId)) {
            throw new IllegalArgumentException("无权限查看该员工的积分流水");
        }
        return pointsLogRepo.findByEmployeeIdOrderByCreatedAtDesc(employeeId);
    }

    private List<PointsLog> listInVisibleScope() {
        Set<Long> visibleOrgIds = resolveVisibleOrgIdsForCurrentUser();
        if (visibleOrgIds.isEmpty()) {
            return List.of();
        }
        return pointsLogRepo.findByOrganizationIdInOrderByCreatedAtDesc(visibleOrgIds);
    }

    private boolean canAccessEmployeeLogs(Long employeeId) {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId != null && currentId.equals(employeeId)) {
            return true;
        }

        Employee current = loadCurrentEmployee();
        if (current == null) {
            return false;
        }

        Employee target = employeeRepository.findByIdWithOrganization(employeeId).orElse(null);
        if (target == null || target.getOrganization() == null) {
            return false;
        }

        if (reviewScopeService.isReviewAdmin(current)) {
            return reviewScopeService.canReviewSubmitterOrg(current, target.getOrganization().getId());
        }

        return false;
    }

    private Set<Long> resolveVisibleOrgIdsForCurrentUser() {
        Employee current = loadCurrentEmployee();
        if (current == null || current.getOrganization() == null) {
            return Set.of();
        }

        if (reviewScopeService.isReviewAdmin(current)) {
            return reviewScopeService.resolveReviewableOrgIds(current);
        }

        return new HashSet<>(List.of(current.getOrganization().getId()));
    }

    private Employee loadCurrentEmployee() {
        Long currentId = CurrentUserContext.getEmployeeId();
        if (currentId == null) {
            return null;
        }
        return employeeRepository.findByIdWithOrganization(currentId).orElse(null);
    }
}
