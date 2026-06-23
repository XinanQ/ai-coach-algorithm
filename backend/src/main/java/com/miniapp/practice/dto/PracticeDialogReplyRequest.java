package com.miniapp.practice.dto;

public class PracticeDialogReplyRequest {

    private String sessionId;
    private String text;

    public PracticeDialogReplyRequest() {
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }
}