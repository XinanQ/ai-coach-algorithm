package com.ranking;

import com.ranking.dto.RankingResponse;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

/**
 * 1.1.7.1 基础排名 API：汇总 points_logs。projectId / indicatorId 不传时分别表示全部项目 / 整项目各指标加总。
 */
@RestController
@RequestMapping("/api/admin/rankings")
public class RankingController {

    private final RankingService rankingService;

    public RankingController(RankingService rankingService) {
        this.rankingService = rankingService;
    }

    @GetMapping
    public RankingResponse list(
            @RequestParam(required = false) Long projectId,
            @RequestParam(required = false) Long indicatorId,
            @RequestParam(defaultValue = "employee") String level,
            @RequestParam(defaultValue = "MONTH") String period,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return rankingService.getRankings(
                projectId,
                indicatorId,
                parseLevel(level),
                parsePeriod(period),
                date
        );
    }

    private RankingLevel parseLevel(String level) {
        if (level == null || level.isBlank()) {
            return RankingLevel.EMPLOYEE;
        }
        try {
            return RankingLevel.valueOf(level.trim().toUpperCase());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("level 无效，可选: employee, outlet, branch, city（每次只能传一个）");
        }
    }

    private RankingPeriod parsePeriod(String period) {
        if (period == null || period.isBlank()) {
            return RankingPeriod.MONTH;
        }
        try {
            return RankingPeriod.valueOf(period.trim().toUpperCase());
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("period 无效，可选: DAY, WEEK, MONTH");
        }
    }
}
