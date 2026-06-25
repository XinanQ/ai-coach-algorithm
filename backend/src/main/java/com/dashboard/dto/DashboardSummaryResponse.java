package com.dashboard.dto;

import com.ranking.dto.RankingEntryResponse;

import java.math.BigDecimal;
import java.util.List;

/**
 * 首页看板聚合返回。一次请求按登录角色范围返回全部看板数据。
 * viewType = MANAGER（管理者）/ EMPLOYEE（普通员工），前端据此切换布局。
 * 管理者用 projects / pendingReviews / subUnits / rankings；员工用 todayReported / myScore / myRank。
 */
public class DashboardSummaryResponse {

    private String name;
    private String organizationName;
    private String viewType;

    private int visibleProjectCount;
    private int activeProjectCount;
    private int pendingReviewCount;
    private int monthReportCount;
    private BigDecimal scopePoints;
    private Integer overallCompletionRate;

    private List<DashboardProjectItem> projects;
    private List<DashboardPendingReviewItem> pendingReviews;
    private List<RankingEntryResponse> subUnits;
    private String subUnitLevelName;
    private List<RankingEntryResponse> rankings;

    private Boolean todayReported;
    private BigDecimal myScore;
    private Integer myRank;
    private String myRankScope;

    public DashboardSummaryResponse() {
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getOrganizationName() {
        return organizationName;
    }

    public void setOrganizationName(String organizationName) {
        this.organizationName = organizationName;
    }

    public String getViewType() {
        return viewType;
    }

    public void setViewType(String viewType) {
        this.viewType = viewType;
    }

    public int getVisibleProjectCount() {
        return visibleProjectCount;
    }

    public void setVisibleProjectCount(int visibleProjectCount) {
        this.visibleProjectCount = visibleProjectCount;
    }

    public int getActiveProjectCount() {
        return activeProjectCount;
    }

    public void setActiveProjectCount(int activeProjectCount) {
        this.activeProjectCount = activeProjectCount;
    }

    public int getPendingReviewCount() {
        return pendingReviewCount;
    }

    public void setPendingReviewCount(int pendingReviewCount) {
        this.pendingReviewCount = pendingReviewCount;
    }

    public int getMonthReportCount() {
        return monthReportCount;
    }

    public void setMonthReportCount(int monthReportCount) {
        this.monthReportCount = monthReportCount;
    }

    public BigDecimal getScopePoints() {
        return scopePoints;
    }

    public void setScopePoints(BigDecimal scopePoints) {
        this.scopePoints = scopePoints;
    }

    public Integer getOverallCompletionRate() {
        return overallCompletionRate;
    }

    public void setOverallCompletionRate(Integer overallCompletionRate) {
        this.overallCompletionRate = overallCompletionRate;
    }

    public List<DashboardProjectItem> getProjects() {
        return projects;
    }

    public void setProjects(List<DashboardProjectItem> projects) {
        this.projects = projects;
    }

    public List<DashboardPendingReviewItem> getPendingReviews() {
        return pendingReviews;
    }

    public void setPendingReviews(List<DashboardPendingReviewItem> pendingReviews) {
        this.pendingReviews = pendingReviews;
    }

    public List<RankingEntryResponse> getSubUnits() {
        return subUnits;
    }

    public void setSubUnits(List<RankingEntryResponse> subUnits) {
        this.subUnits = subUnits;
    }

    public String getSubUnitLevelName() {
        return subUnitLevelName;
    }

    public void setSubUnitLevelName(String subUnitLevelName) {
        this.subUnitLevelName = subUnitLevelName;
    }

    public List<RankingEntryResponse> getRankings() {
        return rankings;
    }

    public void setRankings(List<RankingEntryResponse> rankings) {
        this.rankings = rankings;
    }

    public Boolean getTodayReported() {
        return todayReported;
    }

    public void setTodayReported(Boolean todayReported) {
        this.todayReported = todayReported;
    }

    public BigDecimal getMyScore() {
        return myScore;
    }

    public void setMyScore(BigDecimal myScore) {
        this.myScore = myScore;
    }

    public Integer getMyRank() {
        return myRank;
    }

    public void setMyRank(Integer myRank) {
        this.myRank = myRank;
    }

    public String getMyRankScope() {
        return myRankScope;
    }

    public void setMyRankScope(String myRankScope) {
        this.myRankScope = myRankScope;
    }
}
