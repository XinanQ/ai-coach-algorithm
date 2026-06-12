package com.project.dto;

import com.project.ProjectIndicatorType;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class ProjectIndicatorResponse {

    private Long id;
    private Long projectId;
    private Long indicatorId;
    private String indicatorName;
    private String indicatorCode;
    private String unit;
    private BigDecimal ratio;
    private BigDecimal pointsStandard;
    private String pointsUnit;
    private BigDecimal bigOrderThreshold;
    private Integer marketingStarQuota;
    private ProjectIndicatorType indicatorType;
    private BigDecimal targetValue;
    private Integer sortOrder;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

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

    public String getIndicatorName() {
        return indicatorName;
    }

    public void setIndicatorName(String indicatorName) {
        this.indicatorName = indicatorName;
    }

    public String getIndicatorCode() {
        return indicatorCode;
    }

    public void setIndicatorCode(String indicatorCode) {
        this.indicatorCode = indicatorCode;
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
