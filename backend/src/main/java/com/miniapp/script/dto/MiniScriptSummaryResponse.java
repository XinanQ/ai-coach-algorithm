package com.miniapp.script.dto;

import java.util.List;

/**
 * 小程序话术库列表项响应 DTO。
 *
 * 用于 GET /api/mini/scripts。
 * 字段需要与小程序前端 mock/script.js 保持一致：
 * scriptId / scene / title / tags / date。
 */
public class MiniScriptSummaryResponse {

    private String scriptId;
    private String scene;
    private String title;
    private List<String> tags;
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

    public String getDate() {
        return date;
    }

    public void setDate(String date) {
        this.date = date;
    }
}