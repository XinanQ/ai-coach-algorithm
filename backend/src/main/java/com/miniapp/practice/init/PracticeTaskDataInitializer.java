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

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

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

        Set<String> expectedDefaultTaskIds = new LinkedHashSet<>();
        int synced = 0;
        for (CustomerProfile profile : profiles) {
            if (profile.getSceneId().isEmpty() || profile.getCustomerId().isEmpty()) {
                log.warn("Skip AI coach profile without scene_id or customer_id. sceneId={}, customerId={}",
                        profile.getSceneId(), profile.getCustomerId());
                continue;
            }
            String taskId = buildTaskId(profile.getCustomerId());
            if (!expectedDefaultTaskIds.add(taskId)) {
                log.warn("Skip duplicate AI coach customer profile task. taskId={}, customerId={}",
                        taskId, profile.getCustomerId());
                continue;
            }
            PracticeTask task = practiceTaskRepository.findByTaskId(taskId)
                    .orElseGet(PracticeTask::new);
            syncTask(task, profile, taskId);
            practiceTaskRepository.save(task);
            synced++;
        }

        List<PracticeTask> obsoleteDefaultTasks = practiceTaskRepository.findByIsDefaultTrue()
                .stream()
                .filter(task -> !expectedDefaultTaskIds.contains(task.getTaskId()))
                .toList();
        practiceTaskRepository.deleteAll(obsoleteDefaultTasks);

        log.info("AI coach practice task initialization completed. dataDir={}, profiles={}, syncedTasks={}, removedObsoleteDefaultTasks={}",
                aiCoachProperties.getDataDir(), profiles.size(), synced, obsoleteDefaultTasks.size());
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
        task.setRewardPoints(null);
        task.setRounds(aiCoachProperties.getDefaultTotalRounds());
        task.setProgress(0);
    }

    private String buildTaskId(String customerId) {
        return "practice-" + customerId.toLowerCase(Locale.ROOT).replace("_", "-");
    }
}
