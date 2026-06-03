package com.project;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 项目-指标挂接（1.1.3.4），含 V1 积分标准（分/单位）。
 */
@Entity
@Table(
        name = "project_indicators",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_project_indicators_project_indicator",
                columnNames = {"project_id", "indicator_id"}
        )
)
public class ProjectIndicator {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "indicator_id", nullable = false)
    private Long indicatorId;

    @Column(length = 32)
    private String unit;

    @Column(precision = 8, scale = 4)
    private BigDecimal ratio;

    @Column(name = "points_standard", precision = 12, scale = 4)
    private BigDecimal pointsStandard;

    @Column(name = "points_unit", length = 32)
    private String pointsUnit;

    @Column(name = "big_order_threshold", precision = 14, scale = 2)
    private BigDecimal bigOrderThreshold;

    @Column(name = "marketing_star_quota")
    private Integer marketingStarQuota;

    @Enumerated(EnumType.STRING)
    @Column(name = "indicator_type", length = 16)
    private ProjectIndicatorType indicatorType;

    @Column(name = "target_value", precision = 14, scale = 2)
    private BigDecimal targetValue;

    @Column(name = "sort_order")
    private Integer sortOrder;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public ProjectIndicator() {
    }

    @PrePersist
    public void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        this.createdAt = now;
        this.updatedAt = now;
    }

    @PreUpdate
    public void preUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
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

    public String getUnit() {
        return unit;
    }

    public void setUnit(String unit) {
        this.unit = unit;
    }

    public BigDecimal getRatio() {
        return ratio;
    }

    public void setRatio(BigDecimal ratio) {
        this.ratio = ratio;
    }

    public BigDecimal getPointsStandard() {
        return pointsStandard;
    }

    public void setPointsStandard(BigDecimal pointsStandard) {
        this.pointsStandard = pointsStandard;
    }

    public String getPointsUnit() {
        return pointsUnit;
    }

    public void setPointsUnit(String pointsUnit) {
        this.pointsUnit = pointsUnit;
    }

    public BigDecimal getBigOrderThreshold() {
        return bigOrderThreshold;
    }

    public void setBigOrderThreshold(BigDecimal bigOrderThreshold) {
        this.bigOrderThreshold = bigOrderThreshold;
    }

    public Integer getMarketingStarQuota() {
        return marketingStarQuota;
    }

    public void setMarketingStarQuota(Integer marketingStarQuota) {
        this.marketingStarQuota = marketingStarQuota;
    }

    public ProjectIndicatorType getIndicatorType() {
        return indicatorType;
    }

    public void setIndicatorType(ProjectIndicatorType indicatorType) {
        this.indicatorType = indicatorType;
    }

    public BigDecimal getTargetValue() {
        return targetValue;
    }

    public void setTargetValue(BigDecimal targetValue) {
        this.targetValue = targetValue;
    }

    public Integer getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(Integer sortOrder) {
        this.sortOrder = sortOrder;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}
