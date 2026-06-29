package com.miniapp;

import com.miniapp.dto.MiniApiResponse;
import com.miniapp.dto.MiniWorkspaceSummaryResponse;
import com.miniapp.service.MiniAdminWorkspaceService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class MiniAdminWorkspaceController {

    private final MiniAdminWorkspaceService workspaceService;

    public MiniAdminWorkspaceController(MiniAdminWorkspaceService workspaceService) {
        this.workspaceService = workspaceService;
    }

    @GetMapping("/api/mini/admin/workspace/summary")
    public MiniApiResponse<MiniWorkspaceSummaryResponse> getSummary() {
        MiniWorkspaceSummaryResponse response = workspaceService.getSummary();
        return MiniApiResponse.success(response);
    }
}