package com.miniapp.practice.client.dto;

import com.miniapp.practice.dto.PracticeMessageResponse;

import java.util.List;

public class AiCoachDialogStartResponse {

    private String sessionId;
    private String taskId;
    private Integer round;
    private Integer totalRounds;
    private Integer liveScore;
    private List<PracticeMessageResponse> messages;
    private String source;

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

    public Integer getLiveScore() {
        return liveScore;
    }

    public void setLiveScore(Integer liveScore) {
        this.liveScore = liveScore;
    }

    public List<PracticeMessageResponse> getMessages() {
        return messages;
    }

    public void setMessages(List<PracticeMessageResponse> messages) {
        this.messages = messages;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }
}
