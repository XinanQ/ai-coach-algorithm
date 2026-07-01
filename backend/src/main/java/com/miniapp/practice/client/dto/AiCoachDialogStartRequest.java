package com.miniapp.practice.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class AiCoachDialogStartRequest {

    @JsonProperty("user_id")
    private String userId;

    @JsonProperty("scene_id")
    private String sceneId;

    @JsonProperty("task_id")
    private String taskId;

    @JsonProperty("customer_id")
    private String customerId;

    @JsonProperty("total_rounds")
    private Integer totalRounds;

    private String difficulty;

    @JsonProperty("auto_difficulty")
    private Boolean autoDifficulty;

    public AiCoachDialogStartRequest() {
    }

    public AiCoachDialogStartRequest(String userId,
                                     String sceneId,
                                     String taskId,
                                     String customerId,
                                     Integer totalRounds,
                                     String difficulty,
                                     Boolean autoDifficulty) {
        this.userId = userId;
        this.sceneId = sceneId;
        this.taskId = taskId;
        this.customerId = customerId;
        this.totalRounds = totalRounds;
        this.difficulty = difficulty;
        this.autoDifficulty = autoDifficulty;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getSceneId() {
        return sceneId;
    }

    public void setSceneId(String sceneId) {
        this.sceneId = sceneId;
    }

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public String getCustomerId() {
        return customerId;
    }

    public void setCustomerId(String customerId) {
        this.customerId = customerId;
    }

    public Integer getTotalRounds() {
        return totalRounds;
    }

    public void setTotalRounds(Integer totalRounds) {
        this.totalRounds = totalRounds;
    }

    public String getDifficulty() {
        return difficulty;
    }

    public void setDifficulty(String difficulty) {
        this.difficulty = difficulty;
    }

    public Boolean getAutoDifficulty() {
        return autoDifficulty;
    }

    public void setAutoDifficulty(Boolean autoDifficulty) {
        this.autoDifficulty = autoDifficulty;
    }
}
