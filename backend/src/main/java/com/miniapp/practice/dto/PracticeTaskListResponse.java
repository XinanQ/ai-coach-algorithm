package com.miniapp.practice.dto;

import java.util.List;

public class PracticeTaskListResponse {

    private String levelName;
    private Integer points;
    private Integer target;
    private Integer streakDays;
    private Integer weekGain;
    private List<PracticeTaskSummaryResponse> list;

    public PracticeTaskListResponse() {
    }

    public PracticeTaskListResponse(String levelName,
                                    Integer points,
                                    Integer target,
                                    Integer streakDays,
                                    Integer weekGain,
                                    List<PracticeTaskSummaryResponse> list) {
        this.levelName = levelName;
        this.points = points;
        this.target = target;
        this.streakDays = streakDays;
        this.weekGain = weekGain;
        this.list = list;
    }

    public String getLevelName() {
        return levelName;
    }

    public void setLevelName(String levelName) {
        this.levelName = levelName;
    }

    public Integer getPoints() {
        return points;
    }

    public void setPoints(Integer points) {
        this.points = points;
    }

    public Integer getTarget() {
        return target;
    }

    public void setTarget(Integer target) {
        this.target = target;
    }

    public Integer getStreakDays() {
        return streakDays;
    }

    public void setStreakDays(Integer streakDays) {
        this.streakDays = streakDays;
    }

    public Integer getWeekGain() {
        return weekGain;
    }

    public void setWeekGain(Integer weekGain) {
        this.weekGain = weekGain;
    }

    public List<PracticeTaskSummaryResponse> getList() {
        return list;
    }

    public void setList(List<PracticeTaskSummaryResponse> list) {
        this.list = list;
    }
}