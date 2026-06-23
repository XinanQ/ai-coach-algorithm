package com.miniapp.practice.dto;

import java.util.List;

public class PracticeDialogFinishResponse {

    private String resultId;
    private String taskId;
    private Integer score;
    private Integer scoreDelta;
    private String certificationTitle;
    private String certificationDesc;
    private List<PracticeDimensionScoreResponse> dimensionScores;
    private Integer rewardPoints;
    private Integer rewardExp;
    private List<String> weakTags;
    private String suggestion;
    private String source;

    public PracticeDialogFinishResponse() {
    }

    public String getResultId() {
        return resultId;
    }

    public void setResultId(String resultId) {
        this.resultId = resultId;
    }

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public Integer getScore() {
        return score;
    }

    public void setScore(Integer score) {
        this.score = score;
    }

    public Integer getScoreDelta() {
        return scoreDelta;
    }

    public void setScoreDelta(Integer scoreDelta) {
        this.scoreDelta = scoreDelta;
    }

    public String getCertificationTitle() {
        return certificationTitle;
    }

    public void setCertificationTitle(String certificationTitle) {
        this.certificationTitle = certificationTitle;
    }

    public String getCertificationDesc() {
        return certificationDesc;
    }

    public void setCertificationDesc(String certificationDesc) {
        this.certificationDesc = certificationDesc;
    }

    public List<PracticeDimensionScoreResponse> getDimensionScores() {
        return dimensionScores;
    }

    public void setDimensionScores(List<PracticeDimensionScoreResponse> dimensionScores) {
        this.dimensionScores = dimensionScores;
    }

    public Integer getRewardPoints() {
        return rewardPoints;
    }

    public void setRewardPoints(Integer rewardPoints) {
        this.rewardPoints = rewardPoints;
    }

    public Integer getRewardExp() {
        return rewardExp;
    }

    public void setRewardExp(Integer rewardExp) {
        this.rewardExp = rewardExp;
    }

    public List<String> getWeakTags() {
        return weakTags;
    }

    public void setWeakTags(List<String> weakTags) {
        this.weakTags = weakTags;
    }

    public String getSuggestion() {
        return suggestion;
    }

    public void setSuggestion(String suggestion) {
        this.suggestion = suggestion;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }
}