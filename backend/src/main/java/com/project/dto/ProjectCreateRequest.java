package com.project.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.NotBlank;

/**
 * 创建项目请求 DTO
 *
 * 接收前端新增项目时提交的 JSON 数据
 * 兼容前端旧 mock 字段和后端真实字段之间的差异
 * 避免前端多传字段导致后端报错
 */

@JsonIgnoreProperties(ignoreUnknown = true)
public record ProjectCreateRequest(
        @NotBlank String name,
        String description,

        @NotBlank String startDate,
        @NotBlank String endDate,
        String reportDeadline,

        String status,

        String organizationId,
        String ownerOrgId,
        String managerId,

        @JsonAlias({"attachmentsRequired"})
        Boolean attachmentRequired,

        String attachmentInstructions
){}