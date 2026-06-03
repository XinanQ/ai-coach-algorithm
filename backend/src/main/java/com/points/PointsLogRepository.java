package com.points;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface PointsLogRepository extends JpaRepository<PointsLog, Long> {

    List<PointsLog> findByEmployeeIdOrderByCreatedAtDesc(Long employeeId);

    List<PointsLog> findByProjectIdAndBizDateBetween(Long projectId, LocalDate from, LocalDate to);

    List<PointsLog> findByReportId(Long reportId);
}
