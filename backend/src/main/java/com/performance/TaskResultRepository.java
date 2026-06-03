package com.performance;

import com.performance.TaskResult;
import com.performance.TaskResultStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface TaskResultRepository extends JpaRepository<TaskResult, Long> {
    List<TaskResult> findByStatus(TaskResultStatus status);
    List<TaskResult> findBySubmitterId(Long submitterId);
    List<TaskResult> findByReportDateBetween(LocalDate from, LocalDate to);
}
