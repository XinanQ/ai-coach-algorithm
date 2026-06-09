package com.project;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ProjectIndicatorRepository extends JpaRepository<ProjectIndicator, Long> {

    List<ProjectIndicator> findByProjectIdOrderBySortOrderAscIdAsc(Long projectId);

    List<ProjectIndicator> findByIndicatorId(Long indicatorId);

    boolean existsByProjectIdAndIndicatorId(Long projectId, Long indicatorId);
}
