package com.miniapp.script.dto;

import java.util.List;

/**
 * 小程序话术库列表项响应 DTO。
 *
 * 用于 GET /api/mini/scripts。
 * 保留原有 scriptId / scene / title / tags / date 字段，
 * 并补充算法知识块的结构化元数据。
 */
public class MiniScriptSummaryResponse {

    private String scriptId;
    private String chunkId;
    private String sceneId;
    private String scene;
    private String title;
    private String businessName;
    private String knowledgeType;
    private List<String> tags;
    private String sourceFile;
    private String sourceName;
    private String date;

    public MiniScriptSummaryResponse() {
    }

    public MiniScriptSummaryResponse(String scriptId, String scene, String title, List<String> tags, String date) {
        this.scriptId = scriptId;
        this.scene = scene;
        this.title = title;
        this.tags = tags;
        this.date = date;
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

    public String getDate() {
        return date;
    }

    public void setDate(String date) {
        this.date = date;
    }
}
