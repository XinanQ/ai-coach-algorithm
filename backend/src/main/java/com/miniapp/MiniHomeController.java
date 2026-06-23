package com.miniapp;

import com.miniapp.dto.MiniApiResponse;
import com.miniapp.dto.MiniHomeResponse;
import com.miniapp.service.MiniHomeService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class MiniHomeController {

    private final MiniHomeService miniHomeService;

    public MiniHomeController(MiniHomeService miniHomeService) {
        this.miniHomeService = miniHomeService;
    }

    @GetMapping("/api/mini/home")
    public MiniApiResponse<MiniHomeResponse> getHome() {
        MiniHomeResponse response = miniHomeService.getCurrentUserHome();
        return MiniApiResponse.success(response);
    }
}