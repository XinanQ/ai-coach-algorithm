package com.ranking.dto;

import com.ranking.RankingLevel;
import com.ranking.RankingPeriod;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public class RankingResponse {

    private Long projectId;
    private Long indicatorId;
    private RankingLevel level;
    private RankingPeriod period;
    private LocalDate fromDate;
    private LocalDate toDate;
    private List<RankingEntryResponse> items = new ArrayList<>();

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

    public RankingLevel getLevel() {
        return level;
    }

    public void setLevel(RankingLevel level) {
        this.level = level;
    }

    public RankingPeriod getPeriod() {
        return period;
    }

    public void setPeriod(RankingPeriod period) {
        this.period = period;
    }

    public LocalDate getFromDate() {
        return fromDate;
    }

    public void setFromDate(LocalDate fromDate) {
        this.fromDate = fromDate;
    }

    public LocalDate getToDate() {
        return toDate;
    }

    public void setToDate(LocalDate toDate) {
        this.toDate = toDate;
    }

    public List<RankingEntryResponse> getItems() {
        return items;
    }

    public void setItems(List<RankingEntryResponse> items) {
        this.items = items;
    }
}
