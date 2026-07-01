package com.miniapp.practice.client.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class AiCoachDialogReplyRequest {

    @JsonProperty("session_id")
    private String sessionId;

    @JsonProperty("employee_message")
    private String employeeMessage;

    public AiCoachDialogReplyRequest() {
    }

    public AiCoachDialogReplyRequest(String sessionId, String employeeMessage) {
        this.sessionId = sessionId;
        this.employeeMessage = employeeMessage;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getEmployeeMessage() {
        return employeeMessage;
    }

    public void setEmployeeMessage(String employeeMessage) {
        this.employeeMessage = employeeMessage;
    }
}
