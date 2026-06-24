package com.miniapp.practice;

import com.miniapp.dto.MiniApiResponse;
import com.miniapp.practice.dto.PracticeDialogFinishRequest;
import com.miniapp.practice.dto.PracticeDialogFinishResponse;
import com.miniapp.practice.dto.PracticeDialogReplyRequest;
import com.miniapp.practice.dto.PracticeDialogReplyResponse;
import com.miniapp.practice.dto.PracticeDialogStartRequest;
import com.miniapp.practice.dto.PracticeDialogStartResponse;
import com.miniapp.practice.dto.PracticeTaskDetailResponse;
import com.miniapp.practice.dto.PracticeTaskListResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class MiniPracticeController {

    private final MiniPracticeService miniPracticeService;

    public MiniPracticeController(MiniPracticeService miniPracticeService) {
        this.miniPracticeService = miniPracticeService;
    }

    @GetMapping("/api/mini/practice/tasks")
    public MiniApiResponse<PracticeTaskListResponse> getTasks(
            @RequestParam(defaultValue = "assigned") String tab) {
        PracticeTaskListResponse response = miniPracticeService.getTasks(tab);
        return MiniApiResponse.success(response);
    }

    @GetMapping("/api/mini/practice/tasks/{taskId}")
    public MiniApiResponse<PracticeTaskDetailResponse> getTaskDetail(
            @PathVariable String taskId) {
        PracticeTaskDetailResponse response = miniPracticeService.getTaskDetail(taskId);
        return MiniApiResponse.success(response);
    }

    @PostMapping("/api/mini/practice/dialog/start")
    public MiniApiResponse<PracticeDialogStartResponse> startDialog(
            @RequestBody PracticeDialogStartRequest request) {
        PracticeDialogStartResponse response = miniPracticeService.startDialog(request.getTaskId());
        return MiniApiResponse.success(response);
    }

    @PostMapping("/api/mini/practice/dialog/reply")
    public MiniApiResponse<PracticeDialogReplyResponse> replyDialog(
            @RequestBody PracticeDialogReplyRequest request) {
        PracticeDialogReplyResponse response = miniPracticeService.replyDialog(
                request.getSessionId(),
                request.getText()
        );
        return MiniApiResponse.success(response);
    }

    @PostMapping("/api/mini/practice/dialog/finish")
    public MiniApiResponse<PracticeDialogFinishResponse> finishDialog(
            @RequestBody PracticeDialogFinishRequest request) {
        PracticeDialogFinishResponse response = miniPracticeService.finishDialog(request.getSessionId());
        return MiniApiResponse.success(response);
    }
}