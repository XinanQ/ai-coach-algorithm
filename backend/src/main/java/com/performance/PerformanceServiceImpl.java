package com.performance;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@Transactional
public class PerformanceServiceImpl implements PerformanceService {

    private final TaskResultRepository repo;

    public PerformanceServiceImpl(TaskResultRepository repo) {
        this.repo = repo;
    }

    @Override
    public TaskResult submitReport(TaskResult report) {
        report.setStatus(TaskResultStatus.PENDING);
        report.setReceivedAt(LocalDateTime.now());
        return repo.save(report);
    }

    @Override
    public List<TaskResult> listAll() {
        return repo.findAll();
    }

    @Override
    public List<TaskResult> listByStatus(TaskResultStatus status) {
        return repo.findByStatus(status);
    }

    @Override
    public List<TaskResult> listBySubmitter(Long submitterId) {
        return repo.findBySubmitterId(submitterId);
    }

    @Override
    public List<TaskResult> listByDateRange(LocalDate from, LocalDate to) {
        return repo.findByReportDateBetween(from, to);
    }

    @Override
    public Optional<TaskResult> findById(Long id) {
        return repo.findById(id);
    }

    @Override
    public TaskResult updateReport(Long id, TaskResult report) {
        return repo.findById(id).map(existing -> {
            existing.setTaskId(report.getTaskId());
            existing.setProjectId(report.getProjectId());
            existing.setIndicatorId(report.getIndicatorId());
            existing.setOrganizationId(report.getOrganizationId());
            existing.setSubmitter(report.getSubmitter());
            existing.setSubmitterId(report.getSubmitterId());
            existing.setReportDate(report.getReportDate());
            existing.setResult(report.getResult());
            existing.setAttachmentUrl(report.getAttachmentUrl());
            if (report.getStatus() != null) {
                existing.setStatus(report.getStatus());
            }
            return repo.save(existing);
        }).orElse(null);
    }

    @Override
    public void deleteById(Long id) {
        repo.deleteById(id);
    }

    @Override
    public TaskResult approve(Long id, String reviewer, String comment) {
        return repo.findById(id).map(r -> {
            r.setStatus(TaskResultStatus.APPROVED);
            r.setAuditedBy(reviewer);
            r.setAuditComment(comment);
            r.setAuditedAt(LocalDateTime.now());
            return repo.save(r);
        }).orElse(null);
    }

    @Override
    public TaskResult reject(Long id, String reviewer, String reason) {
        return repo.findById(id).map(r -> {
            r.setStatus(TaskResultStatus.REJECTED);
            r.setAuditedBy(reviewer);
            r.setAuditComment(reason);
            r.setAuditedAt(LocalDateTime.now());
            return repo.save(r);
        }).orElse(null);
    }
}
