package com.decomposition;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "decomposition_record")
public class DecompositionRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String externalId;

    private Long projectId;

    private String ownerRole;

    private String originType;

    private String receivedFrom;

    private String currentOrganization;

    private Long currentOrgId;

    private String currentLevel;

    private String nextLevel;

    private String status;

    private Boolean readOnly;

    @Lob
    @Column(columnDefinition = "LONGTEXT")
    private String payload;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    @PrePersist
    public void prePersist() {
        createdAt = LocalDateTime.now();
        updatedAt = createdAt;
    }

    @PreUpdate
    public void preUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getExternalId() { return externalId; }
    public void setExternalId(String externalId) { this.externalId = externalId; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public String getOwnerRole() { return ownerRole; }
    public void setOwnerRole(String ownerRole) { this.ownerRole = ownerRole; }
    public String getOriginType() { return originType; }
    public void setOriginType(String originType) { this.originType = originType; }
    public String getReceivedFrom() { return receivedFrom; }
    public void setReceivedFrom(String receivedFrom) { this.receivedFrom = receivedFrom; }
    public String getCurrentOrganization() { return currentOrganization; }
    public void setCurrentOrganization(String currentOrganization) { this.currentOrganization = currentOrganization; }
    public Long getCurrentOrgId() { return currentOrgId; }
    public void setCurrentOrgId(Long currentOrgId) { this.currentOrgId = currentOrgId; }
    public String getCurrentLevel() { return currentLevel; }
    public void setCurrentLevel(String currentLevel) { this.currentLevel = currentLevel; }
    public String getNextLevel() { return nextLevel; }
    public void setNextLevel(String nextLevel) { this.nextLevel = nextLevel; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Boolean getReadOnly() { return readOnly; }
    public void setReadOnly(Boolean readOnly) { this.readOnly = readOnly; }
    public String getPayload() { return payload; }
    public void setPayload(String payload) { this.payload = payload; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
