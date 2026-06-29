package com.miniapp.practice.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class AiCoachProperties {

    private final String baseUrl;
    private final Integer defaultTotalRounds;
    private final String dataDir;

    public AiCoachProperties(
            @Value("${ai.coach.base-url}") String baseUrl,
            @Value("${ai.coach.default-total-rounds:3}") Integer defaultTotalRounds,
            @Value("${ai.coach.data-dir:../ai-coach-algorithm}") String dataDir) {
        this.baseUrl = trimTrailingSlash(baseUrl);
        this.defaultTotalRounds = defaultTotalRounds;
        this.dataDir = dataDir == null ? "" : dataDir.trim();
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public Integer getDefaultTotalRounds() {
        return defaultTotalRounds;
    }

    public String getDataDir() {
        return dataDir;
    }

    private String trimTrailingSlash(String value) {
        if (value == null) {
            return "";
        }
        String trimmed = value.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed;
    }
}
