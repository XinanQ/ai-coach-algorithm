package com.miniapp.dto;

public class MiniWorkspaceSummaryResponse {

    private Integer taskCompletionRate;
    private String taskCompletionRateCompareText;

    private Double averageScore;
    private String averageScoreCompareText;

    private Integer pendingTaskCount;
    private Integer highRiskScriptCount;

    public MiniWorkspaceSummaryResponse() {
    }

    public Integer getTaskCompletionRate() {
        return taskCompletionRate;
    }

    public void setTaskCompletionRate(Integer taskCompletionRate) {
        this.taskCompletionRate = taskCompletionRate;
    }

    public String getTaskCompletionRateCompareText() {
        return taskCompletionRateCompareText;
    }

    public void setTaskCompletionRateCompareText(String taskCompletionRateCompareText) {
        this.taskCompletionRateCompareText = taskCompletionRateCompareText;
    }

    public Double getAverageScore() {
        return averageScore;
    }

    public void setAverageScore(Double averageScore) {
        this.averageScore = averageScore;
    }

    public String getAverageScoreCompareText() {
        return averageScoreCompareText;
    }

    public void setAverageScoreCompareText(String averageScoreCompareText) {
        this.averageScoreCompareText = averageScoreCompareText;
    }

    public Integer getPendingTaskCount() {
        return pendingTaskCount;
    }

    public void setPendingTaskCount(Integer pendingTaskCount) {
        this.pendingTaskCount = pendingTaskCount;
    }

    public Integer getHighRiskScriptCount() {
        return highRiskScriptCount;
    }

    public void setHighRiskScriptCount(Integer highRiskScriptCount) {
        this.highRiskScriptCount = highRiskScriptCount;
    }
}