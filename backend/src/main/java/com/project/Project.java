package com.project;

import jakarta.persistence.*;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.LocalDate;

@Entity
@Table(name = "projects")
public class Project {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    private String name;
    private String description;
    @NotNull
    private LocalDate startDate;
    @NotNull
    private LocalDate endDate;
    private Long organizationId;
    private Long managerId;

    @Enumerated(EnumType.STRING)
    private ProjectStatus status;

    @NotNull
    private LocalDate reportDeadline;

    private Boolean attachmentsRequired = false;
    private String attachmentInstructions;

    public Project() {
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public LocalDate getStartDate() {
        return startDate;
    }

    public void setStartDate(LocalDate startDate) {
        this.startDate = startDate;
    }

    public LocalDate getEndDate() {
        return endDate;
    }

    public void setEndDate(LocalDate endDate) {
        this.endDate = endDate;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public void setOrganizationId(Long organizationId) {
        this.organizationId = organizationId;
    }

    public Long getManagerId() {
        return managerId;
    }

    public void setManagerId(Long managerId) {
        this.managerId = managerId;
    }

    public ProjectStatus getStatus() {
        return status;
    }

    public void setStatus(ProjectStatus status) {
        this.status = status;
    }

    public LocalDate getReportDeadline() {
        return reportDeadline;
    }

    public void setReportDeadline(LocalDate reportDeadline) {
        this.reportDeadline = reportDeadline;
    }

    public Boolean getAttachmentsRequired() {
        return attachmentsRequired;
    }

    public void setAttachmentsRequired(Boolean attachmentsRequired) {
        this.attachmentsRequired = attachmentsRequired;
    }

    public String getAttachmentInstructions() {
        return attachmentInstructions;
    }

    public void setAttachmentInstructions(String attachmentInstructions) {
        this.attachmentInstructions = attachmentInstructions;
    }

    @AssertTrue(message = "reportDeadline must fall between startDate and endDate")
    public boolean isReportDeadlineValid() {
        if (startDate == null || endDate == null || reportDeadline == null) {
            return true;
        }
        return !reportDeadline.isBefore(startDate) && !reportDeadline.isAfter(endDate);
    }

    @AssertTrue(message = "attachmentInstructions is required when attachments are required")
    public boolean isAttachmentInstructionsValid() {
        return !Boolean.TRUE.equals(attachmentsRequired) || (attachmentInstructions != null && !attachmentInstructions.isBlank());
    }
}
