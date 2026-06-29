package com.miniapp.practice.dto;

public class PracticeDialogReplyResponse {

    private Integer round;
    private Integer totalRounds;
    private PracticeMessageResponse message;
    private Boolean finished;

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

}
