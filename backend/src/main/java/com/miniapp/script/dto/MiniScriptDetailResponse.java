package com.miniapp.script.dto;

import java.util.List;

/**
 * 小程序话术详情响应 DTO。
 *
 * 用于 GET /api/mini/scripts/{scriptId}。
 * standard 字段用于兼容现有详情页，内容来自算法知识块的 tutor_view_text。
 */
public class MiniScriptDetailResponse {

    private String scriptId;
    private String chunkId;
    private String sceneId;
    private String scene;
    private String title;
    private String businessName;
    private String knowledgeType;
    private List<String> tags;
    private String standard;
    private String content;
    private String sourceFile;
    private String sourceName;
    private String complianceStatus;
    private String reviewStatus;
    private String sourceTaskId;
    private String mine;
    private String source;

    public MiniScriptDetailResponse() {
    }

    public MiniScriptDetailResponse(
            String scriptId,
            String scene,
            String title,
            List<String> tags,
            String standard,
            String sourceTaskId,
            String mine,
            String source
    ) {
        this.scriptId = scriptId;
        this.scene = scene;
        this.title = title;
        this.tags = tags;
        this.standard = standard;
        this.sourceTaskId = sourceTaskId;
        this.mine = mine;
        this.source = source;
    }

    public String getScriptId() {
        return scriptId;
    }

    public void setScriptId(String scriptId) {
        this.scriptId = scriptId;
    }

    public String getChunkId() {
        return chunkId;
    }

    public void setChunkId(String chunkId) {
        this.chunkId = chunkId;
    }

    public String getSceneId() {
        return sceneId;
    }

    public void setSceneId(String sceneId) {
        this.sceneId = sceneId;
    }

    public String getScene() {
        return scene;
    }

    public void setScene(String scene) {
        this.scene = scene;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getBusinessName() {
        return businessName;
    }

    public void setBusinessName(String businessName) {
        this.businessName = businessName;
    }

    public String getKnowledgeType() {
        return knowledgeType;
    }

    public void setKnowledgeType(String knowledgeType) {
        this.knowledgeType = knowledgeType;
    }

    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public String getStandard() {
        return standard;
    }

    public void setStandard(String standard) {
        this.standard = standard;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getSourceFile() {
        return sourceFile;
    }

    public void setSourceFile(String sourceFile) {
        this.sourceFile = sourceFile;
    }

    public String getSourceName() {
        return sourceName;
    }

    public void setSourceName(String sourceName) {
        this.sourceName = sourceName;
    }

    public String getComplianceStatus() {
        return complianceStatus;
    }

    public void setComplianceStatus(String complianceStatus) {
        this.complianceStatus = complianceStatus;
    }

    public String getReviewStatus() {
        return reviewStatus;
    }

    public void setReviewStatus(String reviewStatus) {
        this.reviewStatus = reviewStatus;
    }

    public String getSourceTaskId() {
        return sourceTaskId;
    }

    public void setSourceTaskId(String sourceTaskId) {
        this.sourceTaskId = sourceTaskId;
    }

    public String getMine() {
        return mine;
    }

    public void setMine(String mine) {
        this.mine = mine;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }
}
