package com.decomposition.dto;

import com.decomposition.DecompositionRecord;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public class DecompositionListResponse {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private String id;
    private Long projectId;
    private String ownerRole;
    private String originType;
    private String receivedFrom;
    private String currentOrganization;
    private Long currentOrgId;
    private String currentLevel;
    private String nextLevel;
    private String status;
    private boolean readOnly;
    private List<TargetItem> targets;

    @SuppressWarnings("unchecked")
    public static DecompositionListResponse from(DecompositionRecord record) {
        DecompositionListResponse r = new DecompositionListResponse();
        r.setId(record.getExternalId() != null ? record.getExternalId() : ("stored-" + record.getId()));
        r.setProjectId(record.getProjectId());
        r.setOwnerRole(record.getOwnerRole());
        r.setOriginType(record.getOriginType());
        r.setReceivedFrom(record.getReceivedFrom());
        r.setCurrentOrganization(record.getCurrentOrganization());
        r.setCurrentOrgId(record.getCurrentOrgId());
        r.setCurrentLevel(record.getCurrentLevel());
        r.setNextLevel(record.getNextLevel());
        r.setStatus(record.getStatus());
        r.setReadOnly(Boolean.TRUE.equals(record.getReadOnly()));

        try {
            Map<String, Object> payload = MAPPER.readValue(record.getPayload(), Map.class);
            List<Map<String, Object>> rawTargets = (List<Map<String, Object>>) payload.getOrDefault("targets", Collections.emptyList());
            List<TargetItem> targets = rawTargets.stream().map(t -> {
                TargetItem ti = new TargetItem();
                Object tid = t.get("id");
                if (tid instanceof Number) ti.setId(((Number) tid).longValue());
                else if (tid instanceof String) { try { ti.setId(Long.valueOf((String) tid)); } catch (NumberFormatException ignored) {} }
                ti.setTarget((String) t.get("target"));
                ti.setLevel((String) t.get("level"));

                List<Map<String, Object>> rawIndicators = (List<Map<String, Object>>) t.getOrDefault("indicators", Collections.emptyList());
                List<IndicatorItem> indicators = rawIndicators.stream().map(ind -> {
                    IndicatorItem ii = new IndicatorItem();
                    Object iid = ind.get("indicatorId");
                    if (iid instanceof Number) ii.setIndicatorId(((Number) iid).longValue());
                    else if (iid instanceof String) { try { ii.setIndicatorId(Long.valueOf((String) iid)); } catch (NumberFormatException ignored) {} }
                    ii.setIndicator((String) ind.get("indicator"));
                    Object tt = ind.get("totalTask");
                    if (tt instanceof Number) ii.setTotalTask((Number) tt);
                    Object al = ind.get("allocated");
                    if (al instanceof Number) ii.setAllocated((Number) al);
                    Object ca = ind.get("currentAllocation");
                    if (ca instanceof Number) ii.setCurrentAllocation((Number) ca);
                    ii.setUnit((String) ind.get("unit"));
                    return ii;
                }).toList();
                ti.setIndicators(indicators);
                return ti;
            }).toList();
            r.setTargets(targets);
        } catch (Exception ignored) {
            r.setTargets(Collections.emptyList());
        }

        return r;
    }

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
    public boolean isReadOnly() { return readOnly; }
    public void setReadOnly(boolean readOnly) { this.readOnly = readOnly; }
    public List<TargetItem> getTargets() { return targets; }
    public void setTargets(List<TargetItem> targets) { this.targets = targets; }

    public static class TargetItem {
        private Long id;
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
