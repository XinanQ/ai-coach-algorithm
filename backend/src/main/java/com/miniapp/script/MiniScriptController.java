package com.miniapp.script;

import com.miniapp.dto.MiniApiResponse;
import com.miniapp.script.dto.MiniScriptDetailResponse;
import com.miniapp.script.dto.MiniScriptSummaryResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 小程序话术库接口。
 *
 * 当前用于支持员工端底部 Tab「话术库」：
 * 1. 话术库列表页
 * 2. 话术详情页
 *
 * 仅提供查询接口，暂不提供新增、编辑、删除等话术库管理能力。
 */
@RestController
public class MiniScriptController {

    private final MiniScriptService miniScriptService;

    public MiniScriptController(MiniScriptService miniScriptService) {
        this.miniScriptService = miniScriptService;
    }

    /**
     * 获取话术库列表。
     */
    @GetMapping("/api/mini/scripts")
    public MiniApiResponse<List<MiniScriptSummaryResponse>> getScripts() {
        return MiniApiResponse.success(miniScriptService.getScripts());
    }

    /**
     * 获取话术详情。
     */
    @GetMapping("/api/mini/scripts/{scriptId}")
    public MiniApiResponse<MiniScriptDetailResponse> getScriptDetail(@PathVariable String scriptId) {
        return MiniApiResponse.success(miniScriptService.getScriptDetail(scriptId));
    }
}