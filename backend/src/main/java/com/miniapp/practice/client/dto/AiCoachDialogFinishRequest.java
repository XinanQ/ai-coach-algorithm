package com.miniapp.practice.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class AiCoachDialogFinishRequest {

    @JsonProperty("session_id")
    private String sessionId;

    public AiCoachDialogFinishRequest() {
    }

    public AiCoachDialogFinishRequest(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }
}
