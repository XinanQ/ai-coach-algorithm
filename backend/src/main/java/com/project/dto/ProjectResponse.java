package com.project.dto;

public record ProjectResponse(
        String id,
        Long backendId,

        String name,
        String description,

        String startDate,
        String endDate,
        String reportDeadline,

        Boolean attachmentRequired,
        String attachmentInstructions,

        String status,
        String statusCode,

        Long organizationId,
        Long managerId,

        String owner,
        String ownerLevel,
        String ownerOrgId,

        String distributionStatus,
        String createdAt
){}