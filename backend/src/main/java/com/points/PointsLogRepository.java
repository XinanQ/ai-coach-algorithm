package com.points;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface PointsLogRepository extends JpaRepository<PointsLog, Long> {

    List<PointsLog> findByEmployeeIdOrderByCreatedAtDesc(Long employeeId);

    List<PointsLog> findByProjectIdAndBizDateBetween(Long projectId, LocalDate from, LocalDate to);

    List<PointsLog> findByIndicatorIdAndBizDateBetween(Long indicatorId, LocalDate from, LocalDate to);

    List<PointsLog> findByBizDateBetween(LocalDate from, LocalDate to);

    List<PointsLog> findByProjectIdAndIndicatorIdAndBizDateBetween(
            Long projectId, Long indicatorId, LocalDate from, LocalDate to);

    List<PointsLog> findByReportId(Long reportId);

    boolean existsByReportId(Long reportId);

    List<PointsLog> findByEmployeeIdAndProjectIdOrderByCreatedAtAsc(Long employeeId, Long projectId);
}
