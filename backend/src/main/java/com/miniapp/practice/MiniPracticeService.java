package com.miniapp.practice;

import com.auth.CurrentUserContext;
import com.miniapp.practice.client.AiCoachClient;
import com.miniapp.practice.client.AiCoachProperties;
import com.miniapp.practice.client.dto.AiCoachDialogFinishRequest;
import com.miniapp.practice.client.dto.AiCoachDialogFinishResponse;
import com.miniapp.practice.client.dto.AiCoachDialogReplyRequest;
import com.miniapp.practice.client.dto.AiCoachDialogReplyResponse;
import com.miniapp.practice.client.dto.AiCoachDialogStartRequest;
import com.miniapp.practice.client.dto.AiCoachDialogStartResponse;
import com.miniapp.practice.dto.PracticeDialogFinishResponse;
import com.miniapp.practice.dto.PracticeDialogReplyResponse;
import com.miniapp.practice.dto.PracticeDialogStartResponse;
import com.miniapp.practice.dto.PracticeTaskDetailResponse;
import com.miniapp.practice.dto.PracticeTaskListResponse;
import com.miniapp.practice.dto.PracticeTaskSummaryResponse;
import com.miniapp.practice.metadata.AiCoachMetadataService;
import com.miniapp.practice.metadata.AiCoachMetadataService.BusinessSceneMetadata;
import com.miniapp.practice.metadata.AiCoachMetadataService.CustomerProfile;
import com.miniapp.practice.model.PracticeTask;
import com.miniapp.practice.repository.PracticeTaskRepository;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Service
public class MiniPracticeService {
    private final AiCoachClient aiCoachClient;
    private final AiCoachProperties aiCoachProperties;
    private final PracticeTaskRepository practiceTaskRepository;
    private final AiCoachMetadataService aiCoachMetadataService;

    public MiniPracticeService(
            AiCoachClient aiCoachClient,
            AiCoachProperties aiCoachProperties,
            PracticeTaskRepository practiceTaskRepository,
            AiCoachMetadataService aiCoachMetadataService) {
        this.aiCoachClient = aiCoachClient;
        this.aiCoachProperties = aiCoachProperties;
        this.practiceTaskRepository = practiceTaskRepository;
        this.aiCoachMetadataService = aiCoachMetadataService;
    }

    public PracticeTaskListResponse getTasks(String tab) {
        String tabType = (tab == null || tab.trim().isEmpty()) ? "assigned" : tab;
        List<TaskSummaryContext> contexts = practiceTaskRepository.findByTabTypeOrderByIdAsc(tabType)
                .stream()
                .map(this::toTaskSummaryContext)
                .toList();
        Map<String, Long> titleCounts = contexts.stream()
                .collect(Collectors.groupingBy(TaskSummaryContext::baseTitle, Collectors.counting()));
        List<PracticeTaskSummaryResponse> tasks = contexts.stream()
                .map(context -> toSummaryResponse(
                        context,
                        titleCounts.getOrDefault(context.baseTitle(), 0L) > 1
                ))
                .toList();

        return new PracticeTaskListResponse(
                null,
                null,
                null,
                null,
                null,
                tasks
        );
    }

    public PracticeTaskDetailResponse getTaskDetail(String taskId) {
        PracticeTask task = findTask(taskId);
        CustomerProfile profile = findProfile(task);
        BusinessSceneMetadata businessSceneMetadata = aiCoachMetadataService.findBusinessConfigBySceneId(task.getAiSceneId())
                .orElse(null);

        PracticeTaskDetailResponse response = new PracticeTaskDetailResponse();
        response.setTaskId(task.getTaskId());
        response.setAiSceneId(profile.getSceneId());
        response.setTitle(profile.getSceneName());
        response.setScene(resolveSceneName(profile, businessSceneMetadata));
        response.setRounds(resolveRounds(task));
        response.setCustomerName(profile.getCustomerType());
        response.setCustomerDesc(firstNonBlank(profile.getPersonality(), profile.getConcern()));
        response.setTags(profile.getExpectedIntents());
        response.setBackground(profile.getOpeningQuestion());
        response.setGoal(profile.getFollowupStrategy());
        response.setDifficulty(profile.getDifficultyLevel());
        // 展示口径待产品或算法 metadata 明确，当前不展示内部评分 must_points，避免误导员工。
        response.setRequirements(Collections.emptyList());
        response.setDuration("");
        response.setProgress(task.getProgress());
        response.setScriptId("");
        return response;
    }

    public PracticeDialogStartResponse startDialog(String taskId) {
        PracticeTask task = findTask(taskId);
        if (task.getAiSceneId() == null || task.getAiSceneId().trim().isEmpty()) {
            throw new RuntimeException("陪练任务未配置 AI 场景：" + taskId);
        }
        CustomerProfile profile = findProfile(task);
        Integer totalRounds = task.getRounds() == null ? aiCoachProperties.getDefaultTotalRounds() : task.getRounds();
        String customerId = task.getCustomerId();
        if (customerId == null || customerId.trim().isEmpty()) {
            throw new RuntimeException("陪练任务未配置客户画像：" + taskId);
        }
        String difficulty = profile.getDifficultyLevel();
        if (difficulty != null && difficulty.trim().isEmpty()) {
            difficulty = null;
        }
        AiCoachDialogStartResponse aiResponse = aiCoachClient.start(new AiCoachDialogStartRequest(
                currentUserId(),
                task.getAiSceneId(),
                task.getTaskId(),
                customerId.trim(),
                totalRounds,
                difficulty,
                false
        ));
        PracticeDialogStartResponse response = new PracticeDialogStartResponse();
        response.setSessionId(aiResponse.getSessionId());
        response.setTaskId(aiResponse.getTaskId());
        response.setRound(aiResponse.getRound());
        response.setTotalRounds(aiResponse.getTotalRounds());
        response.setDifficultyLevel(aiResponse.getDifficultyLevel());
        response.setDifficultyRecommendation(aiResponse.getDifficultyRecommendation());
        response.setMessages(aiResponse.getMessages());
        return response;
    }

    private TaskSummaryContext toTaskSummaryContext(PracticeTask task) {
        CustomerProfile profile = findProfile(task);
        BusinessSceneMetadata businessSceneMetadata = aiCoachMetadataService.findBusinessConfigBySceneId(task.getAiSceneId())
                .orElse(null);
        return new TaskSummaryContext(
                task,
                profile,
                businessSceneMetadata,
                buildDisplayTitle(profile)
        );
    }

    private PracticeTaskSummaryResponse toSummaryResponse(TaskSummaryContext context, boolean appendCustomerId) {
        PracticeTask task = context.task();
        CustomerProfile profile = context.profile();
        String displayTitle = context.baseTitle();
        if (appendCustomerId) {
            displayTitle = displayTitle + " · " + profile.getCustomerId();
        }
        return new PracticeTaskSummaryResponse(
                task.getTaskId(),
                profile.getSceneName(),
                displayTitle,
                resolveSceneName(profile, context.businessSceneMetadata()),
                profile.getDifficultyLevel(),
                profile.getExpectedIntents(),
                firstNonBlank(task.getLevel(), "recommend"),
                resolveLevelText(task.getLevel()),
                task.getStatus(),
                resolveStatusText(task.getStatus()),
                task.getDeadline(),
                task.getRewardPoints()
        );
    }

    private String buildDisplayTitle(CustomerProfile profile) {
        String title = Stream.of(
                        profile.getSceneName(),
                        profile.getCustomerType(),
                        profile.getDifficultyLevel()
                )
                .filter(value -> value != null && !value.trim().isEmpty())
                .collect(Collectors.joining(" · "));
        return title.isEmpty() ? profile.getCustomerId() : title;
    }

    private PracticeTask findTask(String taskId) {
        return practiceTaskRepository.findByTaskId(taskId)
                .orElseThrow(() -> new RuntimeException("未找到陪练任务：" + taskId));
    }

    private CustomerProfile findProfile(PracticeTask task) {
        CustomerProfile profile = aiCoachMetadataService.findProfileByCustomerId(task.getCustomerId())
                .orElseThrow(() -> new RuntimeException("AI 陪练客户画像不可用，请稍后重试"));
        if (!task.getAiSceneId().equals(profile.getSceneId())) {
            throw new RuntimeException("陪练任务的 AI 场景与客户画像不匹配：" + task.getTaskId());
        }
        return profile;
    }

    private String currentUserId() {
        Long employeeId = CurrentUserContext.getEmployeeId();
        if (employeeId == null) {
            throw new RuntimeException("当前登录员工不存在");
        }
        return employeeId.toString();
    }

    private String resolveSceneName(CustomerProfile profile, BusinessSceneMetadata businessSceneMetadata) {
        if (businessSceneMetadata != null && !businessSceneMetadata.getBusinessName().isEmpty()) {
            return businessSceneMetadata.getBusinessName();
        }
        return profile.getSceneName();
    }

    private Integer resolveRounds(PracticeTask task) {
        return task.getRounds() == null ? aiCoachProperties.getDefaultTotalRounds() : task.getRounds();
    }

    private String resolveLevelText(String level) {
        if ("must".equals(level)) {
            return "必须完成";
        }
        if ("recommend".equals(level)) {
            return "强烈推荐";
        }
        return "";
    }

    private String resolveStatusText(String status) {
        if ("IN_PROGRESS".equals(status)) {
            return "进行中";
        }
        if ("DONE".equals(status) || "FINISHED".equals(status)) {
            return "已完成";
        }
        if ("PENDING".equals(status) || "NOT_STARTED".equals(status)) {
            return "待完成";
        }
        return "";
    }

    private String firstNonBlank(String primary, String fallback) {
        if (primary != null && !primary.trim().isEmpty()) {
            return primary;
        }
        if (fallback != null && !fallback.trim().isEmpty()) {
            return fallback;
        }
        return "";
    }

    public PracticeDialogReplyResponse replyDialog(String sessionId, String text) {
        if (sessionId == null || sessionId.trim().isEmpty()) {
            throw new RuntimeException("Session id cannot be empty");
        }
        if (text == null || text.trim().isEmpty()) {
            throw new RuntimeException("Reply text cannot be empty");
        }

        AiCoachDialogReplyResponse aiResponse = aiCoachClient.reply(
                new AiCoachDialogReplyRequest(sessionId.trim(), text.trim())
        );
        PracticeDialogReplyResponse response = new PracticeDialogReplyResponse();
        response.setRound(aiResponse.getRound());
        response.setTotalRounds(aiResponse.getTotalRounds());
        response.setMessage(aiResponse.getMessage());
        response.setFinished(aiResponse.getFinished());
        return response;
    }

    public PracticeDialogFinishResponse finishDialog(String sessionId) {
        if (sessionId == null || sessionId.trim().isEmpty()) {
            throw new RuntimeException("Session id cannot be empty");
        }

        AiCoachDialogFinishResponse aiResponse = aiCoachClient.finish(new AiCoachDialogFinishRequest(sessionId.trim()));
        PracticeDialogFinishResponse response = new PracticeDialogFinishResponse();

        // resultId 暂作为算法结果引用；taskId 是 start 时传入并由算法会话原样返回的业务任务 ID。
        response.setResultId(aiResponse.getResultId());
        response.setTaskId(aiResponse.getTaskId());

        // 以下为算法真实评分字段，直接透传。
        response.setScore(aiResponse.getScore());
        response.setDimensionScores(aiResponse.getDimensionScores());
        response.setWeakTags(aiResponse.getWeakTags());
        response.setSuggestion(aiResponse.getSuggestion());
        response.setSource(aiResponse.getSource());

        // 以下字段当前是算法联调占位或 Java 业务字段，暂为兼容透传；后续由历史、积分、经验和认证模块覆盖。
        response.setScoreDelta(aiResponse.getScoreDelta());
        response.setRewardPoints(aiResponse.getRewardPoints());
        response.setRewardExp(aiResponse.getRewardExp());
        response.setCertificationTitle(aiResponse.getCertificationTitle());
        response.setCertificationDesc(aiResponse.getCertificationDesc());
        return response;
    }

    private record TaskSummaryContext(
            PracticeTask task,
            CustomerProfile profile,
            BusinessSceneMetadata businessSceneMetadata,
            String baseTitle
    ) {
    }

}
