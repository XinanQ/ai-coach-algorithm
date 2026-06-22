package com.project.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.NotBlank;


@JsonIgnoreProperties(ignoreUnknown = true)
public record ProjectCreateRequest(
        @NotBlank String name,
        String description,

        @NotBlank String startDate,
        @NotBlank String endDate,
        String reportDeadline,

        String status,

        String organizationId,
        String managerId,

        @JsonAlias({"attachmentsRequired"})
        Boolean attachmentRequired,

        String attachmentInstructions
) {
}