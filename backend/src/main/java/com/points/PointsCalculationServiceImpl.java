package com.points;

import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.organization.Organization;
import com.performance.TaskResult;
import com.project.ProjectIndicator;
import com.project.ProjectIndicatorRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

@Service
@Transactional
public class PointsCalculationServiceImpl implements PointsCalculationService {

    private static final BigDecimal ONE = BigDecimal.ONE;

    private final ProjectIndicatorRepository projectIndicatorRepo;
    private final PointsLogRepository pointsLogRepo;
    private final EmployeeRepository employeeRepository;

    public PointsCalculationServiceImpl(ProjectIndicatorRepository projectIndicatorRepo,
                                        PointsLogRepository pointsLogRepo,
                                        EmployeeRepository employeeRepository) {
        this.projectIndicatorRepo = projectIndicatorRepo;
        this.pointsLogRepo = pointsLogRepo;
        this.employeeRepository = employeeRepository;
    }

    @Override
    public PointsLog calculateOnApprove(TaskResult report) {
        List<PointsLog> existing = pointsLogRepo.findByReportId(report.getId());
        if (!existing.isEmpty()) {
            return existing.get(0);
        }

        if (report.getProjectId() == null || report.getIndicatorId() == null) {
            throw new IllegalArgumentException("上报缺少 projectId 或 indicatorId");
        }
        if (report.getSubmitterId() == null) {
            throw new IllegalArgumentException("上报缺少 submitterId（员工 id）");
        }

        Employee employee = employeeRepository.findById(report.getSubmitterId())
                .orElseThrow(() -> new IllegalArgumentException("员工不存在，employeeId=" + report.getSubmitterId()));
        Organization employeeOrg = employee.getOrganization();
        if (employeeOrg == null) {
            throw new IllegalArgumentException("员工未关联机构，employeeId=" + report.getSubmitterId());
        }

        ProjectIndicator link = projectIndicatorRepo
                .findByProjectIdAndIndicatorId(report.getProjectId(), report.getIndicatorId())
                .orElseThrow(() -> new IllegalArgumentException("项目未挂接该指标"));

        BigDecimal pointsStandard = link.getPointsStandard();
        if (pointsStandard == null) {
            throw new IllegalArgumentException("该项目指标未配置计分标准 pointsStandard");
        }

        BigDecimal effectiveRatio = link.getRatio() != null ? link.getRatio() : ONE;
        BigDecimal quantity = parseQuantity(report.getResult());

        BigDecimal pointsDelta = quantity
                .multiply(pointsStandard)
                .multiply(effectiveRatio)
                .setScale(4, RoundingMode.HALF_UP);

        BigDecimal pointsTotal = sumHistoricalPoints(report.getSubmitterId(), report.getProjectId())
                .add(pointsDelta);

        PointsLog log = new PointsLog();
        log.setEmployeeId(report.getSubmitterId());
        log.setOrganizationId(employeeOrg.getId());
        log.setProjectId(report.getProjectId());
        log.setIndicatorId(report.getIndicatorId());
        log.setReportId(report.getId());
        log.setPointsDelta(pointsDelta);
        log.setPointsTotal(pointsTotal);
        log.setBizDate(report.getReportDate());
        log.setCalcDetail(String.format(
                "%s × %s × %s = %s",
                quantity, pointsStandard, effectiveRatio, pointsDelta));

        return pointsLogRepo.save(log);
    }

    private BigDecimal parseQuantity(String result) {
        try {
            return new BigDecimal(result.trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("上报数量格式无效: " + result);
        }
    }

    private BigDecimal sumHistoricalPoints(Long employeeId, Long projectId) {
        return pointsLogRepo.findByEmployeeIdAndProjectIdOrderByCreatedAtAsc(employeeId, projectId).stream()
                .map(PointsLog::getPointsDelta)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
