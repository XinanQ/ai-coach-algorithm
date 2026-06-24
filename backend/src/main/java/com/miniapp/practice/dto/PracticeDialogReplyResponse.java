package com.miniapp.practice.dto;

public class PracticeDialogReplyResponse {

    private Integer round;
    private Integer totalRounds;
    private Integer liveScore;
    private PracticeMessageResponse message;
    private Boolean finished;
    private String source;

    public PracticeDialogReplyResponse() {
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

    public PracticeMessageResponse getMessage() {
        return message;
    }

    public void setMessage(PracticeMessageResponse message) {
        this.message = message;
    }

    public Boolean getFinished() {
        return finished;
    }

    public void setFinished(Boolean finished) {
        this.finished = finished;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }
}