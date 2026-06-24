package com.project.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.NotBlank;

import java.util.List;


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

        String attachmentInstructions,

        // 参与机构范围（机构 id 列表）；为空表示不限制
        List<Long> visibleOrgIds
) {
}