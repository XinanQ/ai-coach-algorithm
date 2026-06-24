package com.miniapp.practice.dto;

public class PracticeDimensionScoreResponse {

    private String name;
    private Integer score;
    private String level;

    public PracticeDimensionScoreResponse() {
    }

    public PracticeDimensionScoreResponse(String name, Integer score, String level) {
        this.name = name;
        this.score = score;
        this.level = level;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public Integer getScore() {
        return score;
    }

    public void setScore(Integer score) {
        this.score = score;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }
}