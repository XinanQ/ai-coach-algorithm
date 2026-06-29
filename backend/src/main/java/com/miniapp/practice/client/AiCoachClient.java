package com.miniapp.practice.client;

import com.miniapp.practice.client.dto.AiCoachDialogFinishRequest;
import com.miniapp.practice.client.dto.AiCoachDialogFinishResponse;
import com.miniapp.practice.client.dto.AiCoachDialogReplyRequest;
import com.miniapp.practice.client.dto.AiCoachDialogReplyResponse;
import com.miniapp.practice.client.dto.AiCoachDialogStartRequest;
import com.miniapp.practice.client.dto.AiCoachDialogStartResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

@Component
public class AiCoachClient {

    private static final Logger log = LoggerFactory.getLogger(AiCoachClient.class);
    private static final String USER_MESSAGE = "AI 陪练服务暂不可用，请稍后重试";
    private static final int CONNECT_TIMEOUT_MS = 5000;
    private static final int READ_TIMEOUT_MS = 30000;

    private final AiCoachProperties properties;
    private final RestTemplate restTemplate;

    public AiCoachClient(AiCoachProperties properties) {
        this.properties = properties;
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(CONNECT_TIMEOUT_MS);
        requestFactory.setReadTimeout(READ_TIMEOUT_MS);
        this.restTemplate = new RestTemplate(requestFactory);
    }

    public AiCoachDialogStartResponse start(AiCoachDialogStartRequest request) {
        AiCoachDialogStartResponse response = post("/dialog/start", request, AiCoachDialogStartResponse.class);
        validateStartResponse(response);
        return response;
    }

    public AiCoachDialogReplyResponse reply(AiCoachDialogReplyRequest request) {
        AiCoachDialogReplyResponse response = post("/dialog/reply", request, AiCoachDialogReplyResponse.class);
        validateReplyResponse(response);
        return response;
    }

    public AiCoachDialogFinishResponse finish(AiCoachDialogFinishRequest request) {
        AiCoachDialogFinishResponse response = post("/dialog/finish", request, AiCoachDialogFinishResponse.class);
        validateFinishResponse(response);
        return response;
    }

    private <T> T post(String path, Object request, Class<T> responseType) {
        String url = properties.getBaseUrl() + path;
        try {
            T response = restTemplate.postForObject(url, request, responseType);
            if (response == null) {
                throw new IllegalStateException("AI coach response is empty: " + path);
            }
            return response;
        } catch (HttpStatusCodeException ex) {
            log.error("AI coach returned non-2xx status. url={}, status={}, body={}",
                    url, ex.getStatusCode(), ex.getResponseBodyAsString(), ex);
            throw new RuntimeException(USER_MESSAGE, ex);
        } catch (ResourceAccessException ex) {
            log.error("AI coach service is not reachable or timed out. url={}", url, ex);
            throw new RuntimeException(USER_MESSAGE, ex);
        } catch (RestClientException | IllegalStateException ex) {
            log.error("AI coach request failed. url={}", url, ex);
            throw new RuntimeException(USER_MESSAGE, ex);
        }
    }

    private void validateStartResponse(AiCoachDialogStartResponse response) {
        requireText(response.getSessionId(), "sessionId");
        requireText(response.getTaskId(), "taskId");
        requireNonNull(response.getRound(), "round");
        requireNonNull(response.getTotalRounds(), "totalRounds");
        requireNonNull(response.getLiveScore(), "liveScore");
        requireNonNull(response.getMessages(), "messages");
        requireText(response.getSource(), "source");
    }

    private void validateReplyResponse(AiCoachDialogReplyResponse response) {
        requireNonNull(response.getRound(), "round");
        requireNonNull(response.getTotalRounds(), "totalRounds");
        requireNonNull(response.getLiveScore(), "liveScore");
        requireNonNull(response.getFinished(), "finished");
        requireText(response.getSource(), "source");
        if (!response.getFinished()) {
            requireNonNull(response.getMessage(), "message");
            requireText(response.getMessage().getContent(), "message.content");
        }
    }

    private void validateFinishResponse(AiCoachDialogFinishResponse response) {
        requireText(response.getResultId(), "resultId");
        requireText(response.getTaskId(), "taskId");
        requireNonNull(response.getScore(), "score");
        requireNonNull(response.getScoreDelta(), "scoreDelta");
        requireNonNull(response.getCertificationTitle(), "certificationTitle");
        requireNonNull(response.getCertificationDesc(), "certificationDesc");
        requireNonNull(response.getDimensionScores(), "dimensionScores");
        requireNonNull(response.getRewardPoints(), "rewardPoints");
        requireNonNull(response.getRewardExp(), "rewardExp");
        requireNonNull(response.getWeakTags(), "weakTags");
        requireNonNull(response.getSuggestion(), "suggestion");
        requireText(response.getSource(), "source");
    }

    private void requireText(String value, String fieldName) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalStateException("AI coach response missing field: " + fieldName);
        }
    }

    private void requireNonNull(Object value, String fieldName) {
        if (value == null) {
            throw new IllegalStateException("AI coach response missing field: " + fieldName);
        }
    }
}
