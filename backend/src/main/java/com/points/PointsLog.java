package com.points;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 积分变动日志（审核/计算后写入）
 */
@Entity
@Table(name = "points_logs")
public class PointsLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "employee_id", nullable = false)
    private Long employeeId;

    @Column(name = "organization_id")
    private Long organizationId;

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "indicator_id")
    private Long indicatorId;

    @Column(name = "report_id")
    private Long reportId;

    @Column(name = "points_delta", nullable = false, precision = 12, scale = 4)
    private BigDecimal pointsDelta;

    @Column(name = "points_total", precision = 14, scale = 4)
    private BigDecimal pointsTotal;

    @Column(name = "rule_id")
    private Long ruleId;

    @Column(name = "calc_detail", columnDefinition = "TEXT")
    private String calcDetail;

    @Column(name = "biz_date")
    private LocalDate bizDate;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    public PointsLog() {
    }

    @PrePersist
    public void prePersist() {
        if (this.createdAt == null) {
            this.createdAt = LocalDateTime.now();
        }
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getEmployeeId() {
        return employeeId;
    }

    public void setEmployeeId(Long employeeId) {
        this.employeeId = employeeId;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public void setOrganizationId(Long organizationId) {
        this.organizationId = organizationId;
    }

    public Long getProjectId() {
        return projectId;
    }

    public void setProjectId(Long projectId) {
        this.projectId = projectId;
    }

    public Long getIndicatorId() {
        return indicatorId;
    }

    public void setIndicatorId(Long indicatorId) {
        this.indicatorId = indicatorId;
    }

    public Long getReportId() {
        return reportId;
    }

    public void setReportId(Long reportId) {
        this.reportId = reportId;
    }

    public BigDecimal getPointsDelta() {
        return pointsDelta;
    }

    public void setPointsDelta(BigDecimal pointsDelta) {
        this.pointsDelta = pointsDelta;
    }

    public BigDecimal getPointsTotal() {
        return pointsTotal;
    }

    public void setPointsTotal(BigDecimal pointsTotal) {
        this.pointsTotal = pointsTotal;
    }

    public Long getRuleId() {
        return ruleId;
    }

    public void setRuleId(Long ruleId) {
        this.ruleId = ruleId;
    }

    public String getCalcDetail() {
        return calcDetail;
    }

    public void setCalcDetail(String calcDetail) {
        this.calcDetail = calcDetail;
    }

    public LocalDate getBizDate() {
        return bizDate;
    }

    public void setBizDate(LocalDate bizDate) {
        this.bizDate = bizDate;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
