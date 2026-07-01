package com.miniapp.script;

import com.miniapp.practice.metadata.AiCoachMetadataService;
import com.miniapp.practice.metadata.AiCoachMetadataService.MarketingKnowledgeChunk;
import com.miniapp.script.dto.MiniScriptDetailResponse;
import com.miniapp.script.dto.MiniScriptSummaryResponse;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 小程序话术库业务服务。
 *
 * 数据动态读取自 AI 算法项目的 marketing_chunks.json。
 */
@Service
public class MiniScriptService {

    private final AiCoachMetadataService aiCoachMetadataService;

    public MiniScriptService(AiCoachMetadataService aiCoachMetadataService) {
        this.aiCoachMetadataService = aiCoachMetadataService;
    }

    /**
     * 获取小程序话术库列表。
     *
     * 前端期望 data 直接是数组，因此 Controller 会直接返回 List<MiniScriptSummaryResponse>。
     */
    public List<MiniScriptSummaryResponse> getScripts() {
        return aiCoachMetadataService.getMarketingKnowledgeChunks().stream()
                .filter(this::isEmployeeVisible)
                .map(this::toSummaryResponse)
                .collect(Collectors.toList());
    }

    /**
     * 获取小程序话术详情。
     *
     * @param scriptId 算法知识块 chunk_id
     * @return 话术详情
     */
    public MiniScriptDetailResponse getScriptDetail(String scriptId) {
        MarketingKnowledgeChunk chunk = aiCoachMetadataService.findMarketingKnowledgeChunkById(scriptId)
                .filter(this::isEmployeeVisible)
                .orElseThrow(() -> new RuntimeException("未找到可展示的话术内容：" + scriptId));
        return toDetailResponse(chunk);
    }

    private boolean isEmployeeVisible(MarketingKnowledgeChunk chunk) {
        return chunk.isEnabled()
                && "pass".equals(chunk.getComplianceStatus())
                && !firstNonBlank(chunk.getTutorViewText(), chunk.getContent()).isEmpty();
    }

    private MiniScriptSummaryResponse toSummaryResponse(MarketingKnowledgeChunk chunk) {
        MiniScriptSummaryResponse response = new MiniScriptSummaryResponse();
        response.setScriptId(chunk.getChunkId());
        response.setChunkId(chunk.getChunkId());
        response.setSceneId(chunk.getSceneId());
        response.setScene(chunk.getSceneName());
        response.setTitle(chunk.getTitle());
        response.setBusinessName(chunk.getBusinessName());
        response.setKnowledgeType(chunk.getKnowledgeType());
        response.setTags(Collections.emptyList());
        response.setSourceFile(chunk.getSourceFile());
        response.setSourceName(extractFileName(chunk.getSourceFile()));
        response.setDate(chunk.getCreatedAt());
        return response;
    }

    private MiniScriptDetailResponse toDetailResponse(MarketingKnowledgeChunk chunk) {
        MiniScriptDetailResponse response = new MiniScriptDetailResponse();
        response.setScriptId(chunk.getChunkId());
        response.setChunkId(chunk.getChunkId());
        response.setSceneId(chunk.getSceneId());
        response.setScene(chunk.getSceneName());
        response.setTitle(chunk.getTitle());
        response.setBusinessName(chunk.getBusinessName());
        response.setKnowledgeType(chunk.getKnowledgeType());
        response.setTags(Collections.emptyList());
        response.setStandard(firstNonBlank(chunk.getTutorViewText(), chunk.getContent()));
        response.setContent(chunk.getContent());
        response.setSourceFile(chunk.getSourceFile());
        response.setSourceName(extractFileName(chunk.getSourceFile()));
        response.setComplianceStatus(chunk.getComplianceStatus());
        response.setReviewStatus(chunk.getReviewStatus());
        response.setSourceTaskId("");
        response.setMine("");
        response.setSource(chunk.getSourceFile());
        return response;
    }

    private String firstNonBlank(String primary, String fallback) {
        if (primary != null && !primary.trim().isEmpty()) {
            return primary;
        }
        if (fallback != null && !fallback.trim().isEmpty()) {
            return fallback;
        }
        return "";
    }

    private String extractFileName(String sourceFile) {
        if (sourceFile == null || sourceFile.trim().isEmpty()) {
            return "";
        }
        int separatorIndex = Math.max(sourceFile.lastIndexOf('/'), sourceFile.lastIndexOf('\\'));
        return separatorIndex >= 0 ? sourceFile.substring(separatorIndex + 1) : sourceFile;
    }
}
