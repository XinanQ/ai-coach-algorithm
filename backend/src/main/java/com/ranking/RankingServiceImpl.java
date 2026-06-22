package com.ranking;

import com.auth.CurrentUserContext;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.organization.Organization;
import com.organization.Organization.OrgLevel;
import com.organization.OrganizationRepository;
import com.organization.OrganizationService;
import com.points.PointsLog;
import com.points.PointsLogRepository;
import com.ranking.dto.RankingEntryResponse;
import com.ranking.dto.RankingResponse;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
public class RankingServiceImpl implements RankingService {

    private final PointsLogRepository pointsLogRepo;
    private final OrganizationRepository organizationRepo;
    private final OrganizationService organizationService;
    private final EmployeeRepository employeeRepo;

    public RankingServiceImpl(PointsLogRepository pointsLogRepo,
                              OrganizationRepository organizationRepo,
                              OrganizationService organizationService,
                              EmployeeRepository employeeRepo) {
        this.pointsLogRepo = pointsLogRepo;
        this.organizationRepo = organizationRepo;
        this.organizationService = organizationService;
        this.employeeRepo = employeeRepo;
    }

    @Override
    public RankingResponse getRankings(Long projectId,
                                       Long indicatorId,
                                       RankingLevel level,
                                       RankingPeriod period,
                                       LocalDate date) {
        validateRequired();

        RankingLevel effectiveLevel = level != null ? level : RankingLevel.EMPLOYEE;
        RankingPeriod effectivePeriod = period != null ? period : RankingPeriod.MONTH;
        LocalDate anchorDate = date != null ? date : LocalDate.now();

        LocalDate fromDate = resolveFromDate(anchorDate, effectivePeriod);
        LocalDate toDate = resolveToDate(anchorDate, effectivePeriod);

        List<Long> visibleOrgIds = organizationService
                .findSelfAndDescendantIds(CurrentUserContext.getOrganizationId());
        Set<Long> visibleOrgSet = new HashSet<>(visibleOrgIds);

        List<PointsLog> logs = loadPointsLogs(projectId, indicatorId, fromDate, toDate, visibleOrgSet);

        Map<Long, Organization> orgById = organizationRepo.findAll().stream()
                .collect(Collectors.toMap(Organization::getId, o -> o, (a, b) -> a));

        List<RankingEntryResponse> items = switch (effectiveLevel) {
            case EMPLOYEE -> buildEmployeeRanking(logs, orgById);
            case OUTLET -> buildOrganizationRanking(logs, orgById, OrgLevel.OUTLET);
            case BRANCH -> buildOrganizationRanking(logs, orgById, OrgLevel.BRANCH);
            case CITY -> buildOrganizationRanking(logs, orgById, OrgLevel.CITY);
        };

        RankingResponse response = new RankingResponse();
        response.setProjectId(projectId);
        response.setIndicatorId(indicatorId);
        response.setLevel(effectiveLevel);
        response.setPeriod(effectivePeriod);
        response.setFromDate(fromDate);
        response.setToDate(toDate);
        response.setItems(items);
        return response;
    }

    private List<RankingEntryResponse> buildEmployeeRanking(List<PointsLog> logs,
                                                            Map<Long, Organization> orgById) {
        Map<Long, BigDecimal> totals = new HashMap<>();
        Map<Long, Long> employeeOrgIds = new HashMap<>();

        for (PointsLog log : logs) {
            if (log.getEmployeeId() == null) {
                continue;
            }
            totals.merge(log.getEmployeeId(), log.getPointsDelta(), BigDecimal::add);
            if (log.getOrganizationId() != null) {
                employeeOrgIds.putIfAbsent(log.getEmployeeId(), log.getOrganizationId());
            }
        }

        Map<Long, Employee> employees = employeeRepo.findAllById(totals.keySet()).stream()
                .collect(Collectors.toMap(Employee::getId, e -> e, (a, b) -> a));

        List<RankingEntryResponse> entries = new ArrayList<>();
        for (Map.Entry<Long, BigDecimal> entry : totals.entrySet()) {
            Long employeeId = entry.getKey();
            Employee employee = employees.get(employeeId);
            if (employee == null) {
                continue;
            }

            RankingEntryResponse row = new RankingEntryResponse();
            row.setId(employeeId);
            row.setName(employee.getName());
            row.setPoints(entry.getValue());

            Organization org = employee.getOrganization();
            if (org == null && employeeOrgIds.containsKey(employeeId)) {
                org = orgById.get(employeeOrgIds.get(employeeId));
            }
            if (org != null) {
                row.setOrganizationId(org.getId());
                row.setOrganization(org.getName());
            }
            entries.add(row);
        }

        return assignRanks(entries);
    }

    private List<RankingEntryResponse> buildOrganizationRanking(List<PointsLog> logs,
                                                                Map<Long, Organization> orgById,
                                                                OrgLevel targetLevel) {
        Map<Long, BigDecimal> totals = new HashMap<>();

        for (PointsLog log : logs) {
            Long bucketOrgId = resolveOrgAtLevel(log.getOrganizationId(), targetLevel, orgById);
            if (bucketOrgId == null) {
                continue;
            }
            totals.merge(bucketOrgId, log.getPointsDelta(), BigDecimal::add);
        }

        List<RankingEntryResponse> entries = new ArrayList<>();
        for (Map.Entry<Long, BigDecimal> entry : totals.entrySet()) {
            Organization org = orgById.get(entry.getKey());
            if (org == null) {
                continue;
            }

            RankingEntryResponse row = new RankingEntryResponse();
            row.setId(org.getId());
            row.setName(org.getName());
            row.setOrganizationId(org.getId());
            row.setOrganization(org.getName());
            row.setPoints(entry.getValue());
            entries.add(row);
        }

        return assignRanks(entries);
    }

    private List<RankingEntryResponse> assignRanks(List<RankingEntryResponse> entries) {
        entries.sort(Comparator
                .comparing(RankingEntryResponse::getPoints).reversed()
                .thenComparing(RankingEntryResponse::getId));
        int rank = 1;
        for (int i = 0; i < entries.size(); i++) {
            if (i > 0 && entries.get(i).getPoints().compareTo(entries.get(i - 1).getPoints()) != 0) {
                rank++;
            }
            entries.get(i).setRank(rank);
        }
        return entries;
    }

    private Long resolveOrgAtLevel(Long orgId, OrgLevel targetLevel, Map<Long, Organization> orgById) {
        Organization current = orgById.get(orgId);
        while (current != null) {
            if (current.getLevel() == targetLevel) {
                return current.getId();
            }
            current = current.getParent() != null ? orgById.get(current.getParent().getId()) : null;
        }
        return null;
    }

    private LocalDate resolveFromDate(LocalDate anchor, RankingPeriod period) {
        return switch (period) {
            case DAY -> anchor;
            case WEEK -> anchor.with(DayOfWeek.MONDAY);
            case MONTH -> anchor.withDayOfMonth(1);
        };
    }

    private LocalDate resolveToDate(LocalDate anchor, RankingPeriod period) {
        return switch (period) {
            case DAY -> anchor;
            case WEEK -> anchor.with(DayOfWeek.MONDAY).plusDays(6);
            case MONTH -> anchor.withDayOfMonth(anchor.lengthOfMonth());
        };
    }

    private List<PointsLog> loadPointsLogs(Long projectId,
                                           Long indicatorId,
                                           LocalDate fromDate,
                                           LocalDate toDate,
                                           Set<Long> visibleOrgSet) {
        List<PointsLog> rawLogs;
        if (projectId != null && indicatorId != null) {
            rawLogs = pointsLogRepo.findByProjectIdAndIndicatorIdAndBizDateBetween(
                    projectId, indicatorId, fromDate, toDate);
        } else if (projectId != null) {
            rawLogs = pointsLogRepo.findByProjectIdAndBizDateBetween(projectId, fromDate, toDate);
        } else if (indicatorId != null) {
            rawLogs = pointsLogRepo.findByIndicatorIdAndBizDateBetween(indicatorId, fromDate, toDate);
        } else {
            rawLogs = pointsLogRepo.findByBizDateBetween(fromDate, toDate);
        }

        return rawLogs.stream()
                .filter(log -> log.getOrganizationId() != null && visibleOrgSet.contains(log.getOrganizationId()))
                .collect(Collectors.toList());
    }

    private void validateRequired() {
        if (CurrentUserContext.getOrganizationId() == null) {
            throw new IllegalArgumentException("Current user's organizationId cannot be null");
        }
    }
}
