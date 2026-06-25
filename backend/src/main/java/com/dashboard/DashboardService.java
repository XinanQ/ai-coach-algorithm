package com.dashboard;

import com.auth.CurrentUserContext;
import com.dashboard.dto.DashboardPendingReviewItem;
import com.dashboard.dto.DashboardProjectItem;
import com.dashboard.dto.DashboardSummaryResponse;
import com.employee.Employee;
import com.organization.Organization.OrgLevel;
import com.performance.PerformanceService;
import com.performance.ReviewScopeService;
import com.performance.TaskResult;
import com.performance.TaskResultRepository;
import com.performance.TaskResultStatus;
import com.performance.dto.ReportReviewItemResponse;
import com.project.Project;
import com.project.ProjectIndicator;
import com.project.ProjectIndicatorRepository;
import com.project.ProjectService;
import com.project.ProjectStatus;
import com.ranking.RankingLevel;
import com.ranking.RankingPeriod;
import com.ranking.RankingService;
import com.ranking.dto.RankingEntryResponse;
import com.ranking.dto.RankingResponse;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 首页看板聚合服务（1.1.8 闭环）。按登录用户角色范围，一次组装所有看板数据，
 * 复用排名、项目可见性、上报审核范围等既有能力，不引入新的范围逻辑。
 */
@Service
@Transactional(readOnly = true)
public class DashboardService {

    private static final int PROJECT_LIMIT = 6;
    private static final int RANKING_LIMIT = 5;
    private static final int SUB_UNIT_LIMIT = 6;
    private static final int PENDING_PREVIEW_LIMIT = 5;

    private final ProjectService projectService;
    private final RankingService rankingService;
    private final PerformanceService performanceService;
    private final ReviewScopeService reviewScopeService;
    private final ProjectIndicatorRepository projectIndicatorRepository;
    private final TaskResultRepository taskResultRepository;

    public DashboardService(ProjectService projectService,
                            RankingService rankingService,
                            PerformanceService performanceService,
                            ReviewScopeService reviewScopeService,
                            ProjectIndicatorRepository projectIndicatorRepository,
                            TaskResultRepository taskResultRepository) {
        this.projectService = projectService;
        this.rankingService = rankingService;
        this.performanceService = performanceService;
        this.reviewScopeService = reviewScopeService;
        this.projectIndicatorRepository = projectIndicatorRepository;
        this.taskResultRepository = taskResultRepository;
    }

    public DashboardSummaryResponse getSummary() {
        Employee me = CurrentUserContext.get();
        if (me == null) {
            throw new IllegalArgumentException("当前用户未登录或登录已失效");
        }

        LocalDate today = LocalDate.now();
        boolean isManager = reviewScopeService.isReviewAdmin(me);

        DashboardSummaryResponse res = new DashboardSummaryResponse();
        res.setName(me.getName());
        res.setOrganizationName(me.getOrganization() == null ? null : me.getOrganization().getName());
        res.setViewType(isManager ? "MANAGER" : "EMPLOYEE");

        // —— 项目可见列表 + 进行中项目真实完成率 ——
        List<Project> visibleProjects = projectService.findVisibleForCurrentUser();
        res.setVisibleProjectCount(visibleProjects.size());

        Map<Long, BigDecimal> approvedByProject = sumApprovedResultByProject();
        List<DashboardProjectItem> projectItems = new ArrayList<>();
        List<Integer> completionRates = new ArrayList<>();
        int activeCount = 0;

        for (Project project : visibleProjects) {
            boolean active = project.getStatus() == ProjectStatus.ACTIVE;
            if (active) {
                activeCount++;
            }
            if (active && projectItems.size() < PROJECT_LIMIT) {
                Integer rate = computeCompletionRate(project.getId(), approvedByProject);

                DashboardProjectItem item = new DashboardProjectItem();
                item.setId(project.getId());
                item.setName(project.getName());
                item.setCompletionRate(rate);
                item.setDaysToDeadline(project.getEndDate() == null
                        ? null
                        : (int) ChronoUnit.DAYS.between(today, project.getEndDate()));

                if (rate != null) {
                    completionRates.add(rate);
                }
                projectItems.add(item);
            }
        }
        res.setActiveProjectCount(activeCount);
        res.setProjects(projectItems);
        res.setOverallCompletionRate(averageOrNull(completionRates));

        // —— 范围内本月员工积分排行（已按登录机构范围过滤）——
        RankingResponse employeeRanking =
                rankingService.getRankings(null, null, RankingLevel.EMPLOYEE, RankingPeriod.MONTH, today);

        BigDecimal scopePoints = BigDecimal.ZERO;
        for (RankingEntryResponse entry : employeeRanking.getItems()) {
            if (entry.getPoints() != null) {
                scopePoints = scopePoints.add(entry.getPoints());
            }
        }
        res.setScopePoints(scopePoints);
        res.setRankings(limit(employeeRanking.getItems(), RANKING_LIMIT));

        if (isManager) {
            // —— 待审核上报（按可审核机构范围过滤）——
            Set<Long> reviewableOrgIds = reviewScopeService.resolveReviewableOrgIds(me);
            List<ReportReviewItemResponse> pending =
                    performanceService.listByStatus(TaskResultStatus.PENDING);

            List<DashboardPendingReviewItem> pendingItems = new ArrayList<>();
            int pendingCount = 0;
            for (ReportReviewItemResponse report : pending) {
                if (report.getOrganizationId() == null
                        || !reviewableOrgIds.contains(report.getOrganizationId())) {
                    continue;
                }
                pendingCount++;
                if (pendingItems.size() < PENDING_PREVIEW_LIMIT) {
                    DashboardPendingReviewItem item = new DashboardPendingReviewItem();
                    item.setId(report.getId());
                    item.setSubmitter(report.getSubmitter());
                    item.setResult(report.getResult());
                    item.setReportDate(report.getReportDate() == null ? null : report.getReportDate().toString());
                    pendingItems.add(item);
                }
            }
            res.setPendingReviewCount(pendingCount);
            res.setPendingReviews(pendingItems);
            res.setMonthReportCount(countMonthReportsInScope(reviewableOrgIds, today));

            // —— 下属单位业绩对比 ——
            RankingLevel subLevel = resolveSubLevel(me);
            res.setSubUnitLevelName(subUnitLevelName(subLevel));
            RankingResponse subRanking =
                    rankingService.getRankings(null, null, subLevel, RankingPeriod.MONTH, today);
            res.setSubUnits(limit(subRanking.getItems(), SUB_UNIT_LIMIT));
        } else {
            // —— 员工视图 ——
            res.setPendingReviewCount(0);
            res.setPendingReviews(List.of());
            res.setSubUnits(List.of());

            Long meId = me.getId();
            res.setTodayReported(hasReportedToday(meId, today));
            res.setMonthReportCount(countMyMonthReports(meId, today));

            RankingEntryResponse self = null;
            for (RankingEntryResponse entry : employeeRanking.getItems()) {
                if (entry.getId() != null && entry.getId().equals(meId)) {
                    self = entry;
                    break;
                }
            }
            res.setMyScore(self == null ? BigDecimal.ZERO : self.getPoints());
            res.setMyRank(self == null ? null : self.getRank());
            res.setMyRankScope(me.getOrganization() == null
                    ? "本月"
                    : me.getOrganization().getName() + " · 本月");
        }

        return res;
    }

    /** 一次取出全部已审核上报，按项目累加上报值（result 解析为数值），供完成率复用。 */
    private Map<Long, BigDecimal> sumApprovedResultByProject() {
        Map<Long, BigDecimal> byProject = new HashMap<>();
        for (TaskResult report : taskResultRepository.findByStatus(TaskResultStatus.APPROVED)) {
            if (report.getProjectId() == null) {
                continue;
            }
            byProject.merge(report.getProjectId(), parseNumber(report.getResult()), BigDecimal::add);
        }
        return byProject;
    }

    /** 完成率 = 已审核上报值之和 / 项目各指标目标值之和 × 100；无目标值返回 null。 */
    private Integer computeCompletionRate(Long projectId, Map<Long, BigDecimal> approvedByProject) {
        List<ProjectIndicator> indicators =
                projectIndicatorRepository.findByProjectIdOrderBySortOrderAscIdAsc(projectId);

        BigDecimal targetSum = BigDecimal.ZERO;
        for (ProjectIndicator indicator : indicators) {
            if (indicator.getTargetValue() != null) {
                targetSum = targetSum.add(indicator.getTargetValue());
            }
        }
        if (targetSum.compareTo(BigDecimal.ZERO) <= 0) {
            return null;
        }

        BigDecimal achieved = approvedByProject.getOrDefault(projectId, BigDecimal.ZERO);
        int rate = achieved.multiply(BigDecimal.valueOf(100))
                .divide(targetSum, 0, RoundingMode.HALF_UP)
                .intValue();
        return Math.max(0, Math.min(100, rate));
    }

    private int countMonthReportsInScope(Set<Long> scopeOrgIds, LocalDate today) {
        if (scopeOrgIds == null || scopeOrgIds.isEmpty()) {
            return 0;
        }
        LocalDate from = today.withDayOfMonth(1);
        LocalDate to = today.withDayOfMonth(today.lengthOfMonth());
        int count = 0;
        for (TaskResult report : taskResultRepository.findByReportDateBetween(from, to)) {
            if (report.getOrganizationId() != null && scopeOrgIds.contains(report.getOrganizationId())) {
                count++;
            }
        }
        return count;
    }

    private int countMyMonthReports(Long employeeId, LocalDate today) {
        if (employeeId == null) {
            return 0;
        }
        LocalDate from = today.withDayOfMonth(1);
        LocalDate to = today.withDayOfMonth(today.lengthOfMonth());
        int count = 0;
        for (TaskResult report : taskResultRepository.findBySubmitterId(employeeId)) {
            LocalDate date = report.getReportDate();
            if (date != null && !date.isBefore(from) && !date.isAfter(to)) {
                count++;
            }
        }
        return count;
    }

    private boolean hasReportedToday(Long employeeId, LocalDate today) {
        if (employeeId == null) {
            return false;
        }
        for (TaskResult report : taskResultRepository.findBySubmitterId(employeeId)) {
            if (today.equals(report.getReportDate())) {
                return true;
            }
        }
        return false;
    }

    /** 管理者下属对比层级：市行→支行、支行→网点、网点→员工。 */
    private RankingLevel resolveSubLevel(Employee me) {
        OrgLevel level = me.getOrganization() == null ? null : me.getOrganization().getLevel();
        if (level == null) {
            return RankingLevel.BRANCH;
        }
        return switch (level) {
            case HEADQUARTERS, PROVINCE, CITY -> RankingLevel.BRANCH;
            case BRANCH -> RankingLevel.OUTLET;
            case OUTLET -> RankingLevel.EMPLOYEE;
        };
    }

    private String subUnitLevelName(RankingLevel level) {
        return switch (level) {
            case BRANCH -> "支行";
            case OUTLET -> "网点";
            case EMPLOYEE -> "员工";
            case CITY -> "市行";
        };
    }

    /** 直接复用排名标准类型 RankingEntryResponse，仅取前 N 条。 */
    private List<RankingEntryResponse> limit(List<RankingEntryResponse> entries, int max) {
        return entries.size() <= max ? entries : new ArrayList<>(entries.subList(0, max));
    }

    private Integer averageOrNull(List<Integer> values) {
        if (values.isEmpty()) {
            return null;
        }
        int sum = 0;
        for (int value : values) {
            sum += value;
        }
        return Math.round((float) sum / values.size());
    }

    private BigDecimal parseNumber(String raw) {
        if (raw == null || raw.isBlank()) {
            return BigDecimal.ZERO;
        }
        try {
            return new BigDecimal(raw.trim());
        } catch (NumberFormatException ex) {
            return BigDecimal.ZERO;
        }
    }
}
