package com.points;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/admin/points-logs")
public class PointsLogController {

    private final PointsLogService service;

    public PointsLogController(PointsLogService service) {
        this.service = service;
    }

    @GetMapping
    public List<PointsLog> list(@RequestParam(required = false) Long reportId,
                                @RequestParam(required = false) Long employeeId) {
        return service.listVisible(reportId, employeeId);
    }
}
