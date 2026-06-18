package com.points;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/admin/points-logs")
public class PointsLogController {

    private final PointsLogRepository repo;

    public PointsLogController(PointsLogRepository repo) {
        this.repo = repo;
    }

    @GetMapping
    public List<PointsLog> list(@RequestParam(required = false) Long reportId,
                                @RequestParam(required = false) Long employeeId) {
        if (reportId != null) {
            return repo.findByReportId(reportId);
        }
        if (employeeId != null) {
            return repo.findByEmployeeIdOrderByCreatedAtDesc(employeeId);
        }
        return repo.findAll();
    }
}
