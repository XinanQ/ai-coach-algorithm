package com.performance.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.performance.TaskResult;
import com.performance.TaskResultStatus;

import java.time.LocalDate;
import java.time.LocalDateTime;

public class ReportReviewItemResponse {

    private Long id;
    private Long taskId;
    private Long projectId;
    private Long indicatorId;
    private Long organizationId;
    private String submitter;
    private Long submitterId;
    private LocalDate reportDate;
    private String result;
    private String attachmentUrl;
    private TaskResultStatus status;
    private String auditComment;
    private String auditedBy;
    private LocalDateTime auditedAt;
    private LocalDateTime receivedAt;
    private boolean canReview;

    public static ReportReviewItemResponse from(TaskResult report, boolean canReview) {
        ReportReviewItemResponse item = new ReportReviewItemResponse();
        item.setId(report.getId());
        item.setTaskId(report.getTaskId());
        item.setProjectId(report.getProjectId());
        item.setIndicatorId(report.getIndicatorId());
        item.setOrganizationId(report.getOrganizationId());
        item.setSubmitter(report.getSubmitter());
        item.setSubmitterId(report.getSubmitterId());
        item.setReportDate(report.getReportDate());
        item.setResult(report.getResult());
        item.setAttachmentUrl(report.getAttachmentUrl());
        item.setStatus(report.getStatus());
        item.setAuditComment(report.getAuditComment());
        item.setAuditedBy(report.getAuditedBy());
        item.setAuditedAt(report.getAuditedAt());
        item.setReceivedAt(report.getReceivedAt());
        item.setCanReview(canReview);
        return item;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public Long getIndicatorId() { return indicatorId; }
    public void setIndicatorId(Long indicatorId) { this.indicatorId = indicatorId; }
    public Long getOrganizationId() { return organizationId; }
    public void setOrganizationId(Long organizationId) { this.organizationId = organizationId; }
    public String getSubmitter() { return submitter; }
    public void setSubmitter(String submitter) { this.submitter = submitter; }
    public Long getSubmitterId() { return submitterId; }
    public void setSubmitterId(Long submitterId) { this.submitterId = submitterId; }
    public LocalDate getReportDate() { return reportDate; }
    public void setReportDate(LocalDate reportDate) { this.reportDate = reportDate; }
    public String getResult() { return result; }
    public void setResult(String result) { this.result = result; }
    public String getAttachmentUrl() { return attachmentUrl; }
    public void setAttachmentUrl(String attachmentUrl) { this.attachmentUrl = attachmentUrl; }
    public TaskResultStatus getStatus() { return status; }
    public void setStatus(TaskResultStatus status) { this.status = status; }
    public String getAuditComment() { return auditComment; }
    public void setAuditComment(String auditComment) { this.auditComment = auditComment; }
    public String getAuditedBy() { return auditedBy; }
    public void setAuditedBy(String auditedBy) { this.auditedBy = auditedBy; }
    public LocalDateTime getAuditedAt() { return auditedAt; }
    public void setAuditedAt(LocalDateTime auditedAt) { this.auditedAt = auditedAt; }
    public LocalDateTime getReceivedAt() { return receivedAt; }
    public void setReceivedAt(LocalDateTime receivedAt) { this.receivedAt = receivedAt; }

    @JsonProperty("canReview")
    public boolean isCanReview() { return canReview; }
    public void setCanReview(boolean canReview) { this.canReview = canReview; }
}
