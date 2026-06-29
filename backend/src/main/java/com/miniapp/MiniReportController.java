package com.miniapp;

import com.auth.CurrentUserContext;
import com.miniapp.dto.MiniApiResponse;
import com.performance.PerformanceService;
import com.performance.dto.ReportReviewItemResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
public class MiniReportController {

    private final PerformanceService performanceService;

    public MiniReportController(PerformanceService performanceService) {
        this.performanceService = performanceService;
    }

    @GetMapping("/api/mini/reports/history")
    public MiniApiResponse<List<ReportReviewItemResponse>> getMyReportHistory() {
        Long currentEmployeeId = CurrentUserContext.getEmployeeId();
        if (currentEmployeeId == null) {
            throw new IllegalArgumentException("未登录，无法查看本人上报历史");
        }
        return MiniApiResponse.success(performanceService.listBySubmitter(currentEmployeeId));
    }
}
