package com.miniapp.dto;

public class MiniHomeResponse {

    private String name;
    private String level;
    private Boolean isAdmin;

    private Long organizationId;
    private String organizationName;

    private Integer monthlyScore;
    private Integer scoreTarget;
    private Integer completionRate;
    private Integer rank;
    private String rankScope;
    private Boolean todayReported;
    private Integer pendingPracticeTaskCount;

    public MiniHomeResponse() {
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public Boolean getIsAdmin() {
        return isAdmin;
    }

    public void setIsAdmin(Boolean isAdmin) {
        this.isAdmin = isAdmin;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public void setOrganizationId(Long organizationId) {
        this.organizationId = organizationId;
    }

    public String getOrganizationName() {
        return organizationName;
    }

    public void setOrganizationName(String organizationName) {
        this.organizationName = organizationName;
    }

    public Integer getMonthlyScore() {
        return monthlyScore;
    }

    public void setMonthlyScore(Integer monthlyScore) {
        this.monthlyScore = monthlyScore;
    }

    public Integer getScoreTarget() {
        return scoreTarget;
    }

    public void setScoreTarget(Integer scoreTarget) {
        this.scoreTarget = scoreTarget;
    }

    public Integer getCompletionRate() {
        return completionRate;
    }

    public void setCompletionRate(Integer completionRate) {
        this.completionRate = completionRate;
    }

    public Integer getRank() {
        return rank;
    }

    public void setRank(Integer rank) {
        this.rank = rank;
    }

    public String getRankScope() {
        return rankScope;
    }

    public void setRankScope(String rankScope) {
        this.rankScope = rankScope;
    }

    public Boolean getTodayReported() {
        return todayReported;
    }

    public void setTodayReported(Boolean todayReported) {
        this.todayReported = todayReported;
    }

    public Integer getPendingPracticeTaskCount() {
        return pendingPracticeTaskCount;
    }

    public void setPendingPracticeTaskCount(Integer pendingPracticeTaskCount) {
        this.pendingPracticeTaskCount = pendingPracticeTaskCount;
    }
}