package com.performance;

import com.performance.TaskResult;
import com.performance.TaskResultStatus;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface PerformanceService {
    TaskResult submitReport(TaskResult report);
    List<TaskResult> listByStatus(TaskResultStatus status);
    List<TaskResult> listBySubmitter(Long submitterId);
    List<TaskResult> listByDateRange(LocalDate from, LocalDate to);
    Optional<TaskResult> findById(Long id);
    TaskResult approve(Long id, String reviewer, String comment);
    TaskResult reject(Long id, String reviewer, String reason);
}
