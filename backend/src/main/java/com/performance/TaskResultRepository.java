package com.performance;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface TaskResultRepository extends JpaRepository<TaskResult, Long> {
    List<TaskResult> findByStatus(TaskResultStatus status);
    List<TaskResult> findBySubmitterId(Long submitterId);
    List<TaskResult> findByReportDateBetween(LocalDate from, LocalDate to);
    List<TaskResult> findByIndicatorIdAndStatus(Long indicatorId, TaskResultStatus status);
    List<TaskResult> findByIndicatorIdAndSubmitterIdAndStatus(Long indicatorId, Long submitterId, TaskResultStatus status);
    List<TaskResult> findByIndicatorIdAndOrganizationIdInAndStatus(Long indicatorId, List<Long> organizationIds, TaskResultStatus status);
}
