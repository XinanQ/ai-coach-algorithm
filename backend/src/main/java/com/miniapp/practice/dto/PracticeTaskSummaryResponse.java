package com.miniapp.practice.dto;

import java.util.List;

public class PracticeTaskSummaryResponse {

    private String taskId;
    private String title;
    private String displayTitle;
    private String scene;
    private String difficulty;
    private List<String> tags;
    private String level;
    private String levelText;
    private String status;
    private String statusText;
    private String deadline;
    private Integer rewardPoints;

    public PracticeTaskSummaryResponse() {
    }

    public PracticeTaskSummaryResponse(String taskId,
                                       String title,
                                       String displayTitle,
                                       String scene,
                                       String difficulty,
                                       List<String> tags,
                                       String level,
                                       String levelText,
                                       String status,
                                       String statusText,
                                       String deadline,
                                       Integer rewardPoints) {
        this.taskId = taskId;
        this.title = title;
        this.displayTitle = displayTitle;
        this.scene = scene;
        this.difficulty = difficulty;
        this.tags = tags;
        this.level = level;
        this.levelText = levelText;
        this.status = status;
        this.statusText = statusText;
        this.deadline = deadline;
        this.rewardPoints = rewardPoints;
    }

    public String getTaskId() {
        return taskId;
    }

    public void setTaskId(String taskId) {
        this.taskId = taskId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDisplayTitle() {
        return displayTitle;
    }

    public void setDisplayTitle(String displayTitle) {
        this.displayTitle = displayTitle;
    }

    public String getScene() {
        return scene;
    }

    public void setScene(String scene) {
        this.scene = scene;
    }

    public String getDifficulty() {
        return difficulty;
    }

    public void setDifficulty(String difficulty) {
        this.difficulty = difficulty;
    }

    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public String getLevelText() {
        return levelText;
    }

    public void setLevelText(String levelText) {
        this.levelText = levelText;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getStatusText() {
        return statusText;
    }

    public void setStatusText(String statusText) {
        this.statusText = statusText;
    }

    public String getDeadline() {
        return deadline;
    }

    public void setDeadline(String deadline) {
        this.deadline = deadline;
    }

    public Integer getRewardPoints() {
        return rewardPoints;
    }

    public void setRewardPoints(Integer rewardPoints) {
        this.rewardPoints = rewardPoints;
    }
}
