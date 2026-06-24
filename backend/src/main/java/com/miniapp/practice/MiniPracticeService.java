package com.miniapp.practice;

import com.miniapp.practice.dto.PracticeDialogFinishResponse;
import com.miniapp.practice.dto.PracticeDialogReplyResponse;
import com.miniapp.practice.dto.PracticeDialogStartResponse;
import com.miniapp.practice.dto.PracticeDimensionScoreResponse;
import com.miniapp.practice.dto.PracticeMessageResponse;
import com.miniapp.practice.dto.PracticeTaskDetailResponse;
import com.miniapp.practice.dto.PracticeTaskListResponse;
import com.miniapp.practice.dto.PracticeTaskSummaryResponse;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class MiniPracticeService {
    private static final int TOTAL_ROUNDS = 3;
    private static final String SOURCE_RULE_BASED = "RULE_BASED";

    private final Map<String, PracticeSession> sessions = new ConcurrentHashMap<>();

    public PracticeTaskListResponse getTasks(String tab) {
        List<PracticeTaskSummaryResponse> tasks = new ArrayList<>();

        if ("self".equals(tab)) {
            tasks.add(new PracticeTaskSummaryResponse(
                    "l1",
                    "信用卡分期回访",
                    "信用卡",
                    "recommend",
                    "强烈推荐",
                    "PENDING",
                    "待完成",
                    "",
                    40
            ));
            tasks.add(new PracticeTaskSummaryResponse(
                    "l2",
                    "贷款逾期提醒",
                    "贷款",
                    "recommend",
                    "强烈推荐",
                    "PENDING",
                    "待完成",
                    "",
                    40
            ));
            tasks.add(new PracticeTaskSummaryResponse(
                    "l3",
                    "客户投诉安抚",
                    "投诉",
                    "recommend",
                    "强烈推荐",
                    "PENDING",
                    "待完成",
                    "",
                    40
            ));
        } else if ("done".equals(tab)) {
            tasks.add(new PracticeTaskSummaryResponse(
                    "t0",
                    "存款推荐话术",
                    "存款推荐",
                    "must",
                    "必须完成",
                    "DONE",
                    "已完成",
                    "2026-06-10",
                    50
            ));
        } else {
            tasks.add(new PracticeTaskSummaryResponse(
                    "t1",
                    "风险揭示话术",
                    "理财产品风险揭示",
                    "must",
                    "必须完成",
                    "IN_PROGRESS",
                    "进行中",
                    "2026-06-28",
                    50
            ));
            tasks.add(new PracticeTaskSummaryResponse(
                    "t2",
                    "高净值客户需求挖掘",
                    "需求挖掘",
                    "recommend",
                    "强烈推荐",
                    "PENDING",
                    "待完成",
                    "2026-07-05",
                    60
            ));
        }

        return new PracticeTaskListResponse(
                "Lv5 专业进阶",
                1260,
                1800,
                7,
                320,
                tasks
        );
    }

    public PracticeTaskDetailResponse getTaskDetail(String taskId) {
        PracticeTaskDetailResponse response = new PracticeTaskDetailResponse();

        response.setTaskId(taskId);
        response.setTitle(resolveTitle(taskId));
        response.setScene(resolveScene(taskId));
        response.setRounds(3);

        response.setCustomerName("王女士");
        response.setCustomerDesc("35岁，企业白领，有一笔闲置资金");
        response.setTags(Arrays.asList("流动性担忧", "利率敏感", "风险厌恶"));

        response.setBackground("客户近期有一笔闲置资金，关注收益的同时担心资金随时可能需要支取。请你结合客户情况，推荐合适的产品并打消其顾虑。");
        response.setGoal("完成 3 轮对话，覆盖产品收益、流动性方案与风险说明。");
        response.setRequirements(Arrays.asList("完成 3 轮对话", "综合得分 ≥ 80 分"));

        response.setDuration("15-20 分钟");
        response.setProgress(0);
        response.setScriptId("s1");

        return response;
    }

    public PracticeDialogStartResponse startDialog(String taskId) {
        String sessionId = "s-" + UUID.randomUUID();

        PracticeSession session = new PracticeSession();
        session.setSessionId(sessionId);
        session.setTaskId(taskId);
        session.setCurrentRound(1);
        session.getMessages().add(new PracticeMessageResponse(
                "ai",
                buildFirstQuestion(taskId)
        ));

        sessions.put(sessionId, session);

        PracticeDialogStartResponse response = new PracticeDialogStartResponse();
        response.setSessionId(sessionId);
        response.setTaskId(taskId);
        response.setRound(1);
        response.setTotalRounds(TOTAL_ROUNDS);
        response.setLiveScore(70);
        response.setMessages(session.getMessages());
        response.setSource(SOURCE_RULE_BASED);

        return response;
    }

    public PracticeDialogReplyResponse replyDialog(String sessionId, String text) {
        PracticeSession session = sessions.get(sessionId);

        if (session == null) {
            throw new RuntimeException("Practice session not found");
        }

        if (text == null || text.trim().isEmpty()) {
            throw new RuntimeException("Reply text cannot be empty");
        }

        session.getMessages().add(new PracticeMessageResponse("user", text));

        int answeredRound = session.getCurrentRound();

        PracticeDialogReplyResponse response = new PracticeDialogReplyResponse();
        response.setTotalRounds(TOTAL_ROUNDS);
        response.setSource(SOURCE_RULE_BASED);

        if (answeredRound >= TOTAL_ROUNDS) {
            response.setRound(TOTAL_ROUNDS);
            response.setLiveScore(84);
            response.setMessage(null);
            response.setFinished(true);
            return response;
        }

        int nextRound = answeredRound + 1;
        session.setCurrentRound(nextRound);

        PracticeMessageResponse aiMessage = new PracticeMessageResponse(
                "ai",
                buildFollowUpQuestion(nextRound)
        );
        session.getMessages().add(aiMessage);

        response.setRound(nextRound);
        response.setLiveScore(calculateMockLiveScore(nextRound));
        response.setMessage(aiMessage);
        response.setFinished(false);

        return response;
    }

    public PracticeDialogFinishResponse finishDialog(String sessionId) {
        PracticeSession session = sessions.get(sessionId);

        if (session == null) {
            throw new RuntimeException("Practice session not found");
        }

        PracticeDialogFinishResponse response = new PracticeDialogFinishResponse();

        response.setResultId("r-" + UUID.randomUUID());
        response.setTaskId(session.getTaskId());
        response.setScore(82);
        response.setScoreDelta(6);
        response.setCertificationTitle("新晋「合规揭示达人」");
        response.setCertificationDesc("合规表达达标，完成专项认证");

        response.setDimensionScores(Arrays.asList(
                new PracticeDimensionScoreResponse("合规度", 92, "优秀"),
                new PracticeDimensionScoreResponse("共情力", 84, "良好"),
                new PracticeDimensionScoreResponse("逻辑结构", 86, "优秀"),
                new PracticeDimensionScoreResponse("异议处理", 80, "良好")
        ));

        response.setRewardPoints(80);
        response.setRewardExp(120);
        response.setWeakTags(Arrays.asList("流动性解释不足", "风险提示不足"));
        response.setSuggestion("回答基本覆盖了产品要点，但对客户流动性需求的应对不够具体，建议补充活期与定期搭配方案的说明。");
        response.setSource(SOURCE_RULE_BASED);

        return response;
    }

    private String buildFirstQuestion(String taskId) {
        return "您好，我最近想了解一下存款产品，有没有收益比较高又安全的推荐？";
    }

    private String buildFollowUpQuestion(int round) {
        if (round == 2) {
            return "如果资金需要随时支取，您会怎么建议呢？";
        }
        return "如果我比较担心风险，您能再具体说明一下安全吗？";
    }

    private Integer calculateMockLiveScore(int round) {
        if (round == 2) {
            return 78;
        }
        if (round == 3) {
            return 84;
        }
        return 70;
    }

    private String resolveTitle(String taskId) {
        if ("t1".equals(taskId)) {
            return "风险揭示话术";
        }
        if ("t2".equals(taskId)) {
            return "高净值客户需求挖掘";
        }
        if ("l1".equals(taskId)) {
            return "信用卡分期回访";
        }
        if ("l2".equals(taskId)) {
            return "贷款逾期提醒";
        }
        if ("l3".equals(taskId)) {
            return "客户投诉安抚";
        }
        if ("t0".equals(taskId)) {
            return "存款推荐话术";
        }
        return "存款推荐";
    }

    private String resolveScene(String taskId) {
        if ("t1".equals(taskId)) {
            return "理财产品风险揭示";
        }
        if ("t2".equals(taskId)) {
            return "需求挖掘";
        }
        if ("l1".equals(taskId)) {
            return "信用卡";
        }
        if ("l2".equals(taskId)) {
            return "贷款";
        }
        if ("l3".equals(taskId)) {
            return "投诉";
        }
        if ("t0".equals(taskId)) {
            return "存款推荐";
        }
        return "存款推荐";
    }

    private static class PracticeSession {

        private String sessionId;
        private String taskId;
        private Integer currentRound;
        private final List<PracticeMessageResponse> messages = new ArrayList<>();

        public String getSessionId() {
            return sessionId;
        }

        public void setSessionId(String sessionId) {
            this.sessionId = sessionId;
        }

        public String getTaskId() {
            return taskId;
        }

        public void setTaskId(String taskId) {
            this.taskId = taskId;
        }

        public Integer getCurrentRound() {
            return currentRound;
        }

        public void setCurrentRound(Integer currentRound) {
            this.currentRound = currentRound;
        }

        public List<PracticeMessageResponse> getMessages() {
            return messages;
        }
    }
}