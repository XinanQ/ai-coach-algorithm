package com.miniapp.practice.dto;

import java.util.List;
import java.util.Map;

public class PracticeDialogStartResponse {

    private String sessionId;
    private String taskId;
    private Integer round;
    private Integer totalRounds;
    private String difficultyLevel;
    private Map<String, Object> difficultyRecommendation;
    private List<PracticeMessageResponse> messages;

    public PracticeDialogStartResponse() {
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public Integer getRound() {
        return round;
    }

    public void setRound(Integer round) {
        this.round = round;
    }

    public Integer getTotalRounds() {
        return totalRounds;
    }

    public void setTotalRounds(Integer totalRounds) {
        this.totalRounds = totalRounds;
    }

    public String getDifficultyLevel() {
        return difficultyLevel;
    }

    public void setDifficultyLevel(String difficultyLevel) {
        this.difficultyLevel = difficultyLevel;
    }

    public Map<String, Object> getDifficultyRecommendation() {
        return difficultyRecommendation;
    }

    public void setDifficultyRecommendation(Map<String, Object> difficultyRecommendation) {
        this.difficultyRecommendation = difficultyRecommendation;
    }

    public List<PracticeMessageResponse> getMessages() {
        return messages;
    }

    public void setMessages(List<PracticeMessageResponse> messages) {
        this.messages = messages;
    }

}
