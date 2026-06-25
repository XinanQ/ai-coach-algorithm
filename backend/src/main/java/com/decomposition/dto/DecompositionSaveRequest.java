package com.decomposition.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public class DecompositionSaveRequest {

    private String id;

    @NotNull
    private Long projectId;

    private String ownerRole;

    @NotBlank
    private String originType;

    private String receivedFrom;

    private String currentOrganization;

    @NotNull
    private Long currentOrgId;

    private String currentLevel;

    @NotBlank
    private String nextLevel;

    private String status;

    @NotNull
    private List<TargetItem> targets;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public String getOwnerRole() { return ownerRole; }
    public void setOwnerRole(String ownerRole) { this.ownerRole = ownerRole; }
    public String getOriginType() { return originType; }
    public void setOriginType(String originType) { this.originType = originType; }
    public String getReceivedFrom() { return receivedFrom; }
    public void setReceivedFrom(String receivedFrom) { this.receivedFrom = receivedFrom; }
    public String getCurrentOrganization() { return currentOrganization; }
    public void setCurrentOrganization(String currentOrganization) { this.currentOrganization = currentOrganization; }
    public Long getCurrentOrgId() { return currentOrgId; }
    public void setCurrentOrgId(Long currentOrgId) { this.currentOrgId = currentOrgId; }
    public String getCurrentLevel() { return currentLevel; }
    public void setCurrentLevel(String currentLevel) { this.currentLevel = currentLevel; }
    public String getNextLevel() { return nextLevel; }
    public void setNextLevel(String nextLevel) { this.nextLevel = nextLevel; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public List<TargetItem> getTargets() { return targets; }
    public void setTargets(List<TargetItem> targets) { this.targets = targets; }

    public static class TargetItem {
        @NotNull
        private Long id;

        @NotBlank
        private String target;

        private String level;

        private List<IndicatorItem> indicators;

        public Long getId() { return id; }
        public void setId(Long id) { this.id = id; }
        public String getTarget() { return target; }
        public void setTarget(String target) { this.target = target; }
        public String getLevel() { return level; }
        public void setLevel(String level) { this.level = level; }
        public List<IndicatorItem> getIndicators() { return indicators; }
        public void setIndicators(List<IndicatorItem> indicators) { this.indicators = indicators; }
    }

    public static class IndicatorItem {
        private Long indicatorId;
        private String indicator;
        private Number totalTask;
        private Number allocated;
        private Number currentAllocation;
        private String unit;

        public Long getIndicatorId() { return indicatorId; }
        public void setIndicatorId(Long indicatorId) { this.indicatorId = indicatorId; }
        public String getIndicator() { return indicator; }
        public void setIndicator(String indicator) { this.indicator = indicator; }
        public Number getTotalTask() { return totalTask; }
        public void setTotalTask(Number totalTask) { this.totalTask = totalTask; }
        public Number getAllocated() { return allocated; }
        public void setAllocated(Number allocated) { this.allocated = allocated; }
        public Number getCurrentAllocation() { return currentAllocation; }
        public void setCurrentAllocation(Number currentAllocation) { this.currentAllocation = currentAllocation; }
        public String getUnit() { return unit; }
        public void setUnit(String unit) { this.unit = unit; }
    }
}
