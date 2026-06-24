package com.miniapp.script.dto;

import java.util.List;

/**
 * 小程序话术详情响应 DTO。
 *
 * 用于 GET /api/mini/scripts/{scriptId}。
 * 字段需要与小程序前端详情页保持一致：
 * detail.js 中复制按钮读取的是 detail.standard，
 * 因此这里必须返回 standard，而不是 standardScript。
 */
public class MiniScriptDetailResponse {

    private String scriptId;
    private String scene;
    private String title;
    private List<String> tags;
    private String standard;
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