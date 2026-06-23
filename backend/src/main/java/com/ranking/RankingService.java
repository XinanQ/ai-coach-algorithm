package com.ranking;

import com.ranking.dto.RankingResponse;

import java.time.LocalDate;

public interface RankingService {

    RankingResponse getRankings(Long projectId,
                                Long indicatorId,
                                RankingLevel level,
                                RankingPeriod period,
                                LocalDate date);
}
