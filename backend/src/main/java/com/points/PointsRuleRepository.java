package com.points;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PointsRuleRepository extends JpaRepository<PointsRule, Long> {

    List<PointsRule> findByEnabledTrueOrderByPriorityAscIdAsc();

    List<PointsRule> findByProjectIdAndEnabledTrue(Long projectId);

    List<PointsRule> findByIndicatorIdAndEnabledTrue(Long indicatorId);
}
