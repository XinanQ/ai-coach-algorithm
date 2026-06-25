package com.performance;

import com.performance.dto.ReportReviewItemResponse;
import com.performance.dto.ReportUpdateRequest;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface PerformanceService {
    TaskResult submitReport(TaskResult report);
    List<ReportReviewItemResponse> listAll();
    List<ReportReviewItemResponse> listByStatus(TaskResultStatus status);
    List<ReportReviewItemResponse> listBySubmitter(Long submitterId);
    List<ReportReviewItemResponse> listByDateRange(LocalDate from, LocalDate to);
    Optional<TaskResult> findById(Long id);
    TaskResult updateReport(Long id, ReportUpdateRequest report);
    void deleteById(Long id);
    TaskResult approve(Long id, String reviewer, String comment);
    TaskResult reject(Long id, String reviewer, String reason);
}
