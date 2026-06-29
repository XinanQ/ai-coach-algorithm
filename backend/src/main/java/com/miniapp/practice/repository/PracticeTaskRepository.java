package com.miniapp.practice.repository;

import com.miniapp.practice.model.PracticeTask;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface PracticeTaskRepository extends JpaRepository<PracticeTask, Long> {

    List<PracticeTask> findByTabTypeOrderByIdAsc(String tabType);

    Optional<PracticeTask> findByTaskId(String taskId);

    boolean existsByTaskId(String taskId);

    void deleteByTaskIdIn(Collection<String> taskIds);
}
