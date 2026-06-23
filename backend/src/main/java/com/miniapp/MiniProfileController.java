package com.miniapp;

import com.miniapp.dto.MiniApiResponse;
import com.miniapp.dto.MiniProfileResponse;
import com.miniapp.service.MiniProfileService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class MiniProfileController {

    private final MiniProfileService miniProfileService;

    public MiniProfileController(MiniProfileService miniProfileService) {
        this.miniProfileService = miniProfileService;
    }

    @GetMapping("/api/mini/profile")
    public MiniApiResponse<MiniProfileResponse> getProfile() {
        MiniProfileResponse response = miniProfileService.getCurrentUserProfile();
        return MiniApiResponse.success(response);
    }
}