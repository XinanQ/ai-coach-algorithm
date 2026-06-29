package com.miniapp.practice.init;

import com.miniapp.practice.client.AiCoachProperties;
import com.miniapp.practice.metadata.AiCoachMetadataService;
import com.miniapp.practice.metadata.AiCoachMetadataService.CustomerProfile;
import com.miniapp.practice.model.PracticeTask;
import com.miniapp.practice.repository.PracticeTaskRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.List;

/**
 * 小程序 AI 陪练默认任务初始化。
 *
 * 当前仅用于第一阶段联调/演示环境的默认 AI 陪练任务技术数据。
 * AI 场景标题、客户画像、背景、目标等业务内容由算法元数据动态提供，
 * 不在 Spring Boot 数据库中长期维护。
 */
@Component
public class PracticeTaskDataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(PracticeTaskDataInitializer.class);
    private static final List<String> LEGACY_MOCK_TASK_IDS = Arrays.asList(
            "practice-risk-disclosure-001",
            "practice-high-net-worth-needs-001",
            "practice-credit-card-installment-001",
            "practice-loan-overdue-reminder-001",
            "practice-complaint-comfort-001"
    );
    private final PracticeTaskRepository practiceTaskRepository;
    private final AiCoachMetadataService aiCoachMetadataService;
    private final AiCoachProperties aiCoachProperties;

    public PracticeTaskDataInitializer(PracticeTaskRepository practiceTaskRepository,
                                       AiCoachMetadataService aiCoachMetadataService,
                                       AiCoachProperties aiCoachProperties) {
        this.practiceTaskRepository = practiceTaskRepository;
        this.aiCoachMetadataService = aiCoachMetadataService;
        this.aiCoachProperties = aiCoachProperties;
    }

    @Override
    @Transactional
    public void run(String... args) {
        List<CustomerProfile> profiles = aiCoachMetadataService.getProfiles();
        if (profiles.isEmpty()) {
            log.warn("Skip AI coach practice task initialization because no customer profile is available. dataDir={}",
                    aiCoachProperties.getDataDir());
            return;
        }

        practiceTaskRepository.deleteByTaskIdIn(LEGACY_MOCK_TASK_IDS);

        int synced = 0;
        for (CustomerProfile profile : profiles) {
            if (profile.getSceneId().isEmpty()) {
                log.warn("Skip AI coach profile without scene_id. profile={}", profile);
                continue;
            }
            String taskId = buildTaskId(profile.getSceneId());
            PracticeTask task = practiceTaskRepository.findByTaskId(taskId)
                    .orElseGet(PracticeTask::new);
            syncTask(task, profile, taskId);
            practiceTaskRepository.save(task);
            synced++;
        }

        log.info("AI coach practice task initialization completed. dataDir={}, profiles={}, syncedTasks={}, removedLegacyMockTaskIds={}",
                aiCoachProperties.getDataDir(), profiles.size(), synced, LEGACY_MOCK_TASK_IDS);
    }

    private void syncTask(PracticeTask task, CustomerProfile profile, String taskId) {
        task.setTaskId(taskId);
        task.setAiSceneId(profile.getSceneId());
        task.setCustomerId(profile.getCustomerId());
        task.setSourceProfileHash(profile.getSourceProfileHash());
        task.setIsDefault(true);

        task.setTabType("self");
        task.setLevel("recommend");
        task.setStatus("PENDING");
        task.setDeadline("");
        task.setRewardPoints(40);
        task.setRounds(aiCoachProperties.getDefaultTotalRounds());
        task.setProgress(0);
    }

    private String buildTaskId(String sceneId) {
        return "practice-" + sceneId.toLowerCase().replace("_", "-");
    }
}
