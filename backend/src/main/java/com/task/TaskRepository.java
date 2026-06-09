package com.task;

import com.task.Task;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TaskRepository extends JpaRepository<Task, Long> {
    List<Task> findByTypeAndTargetTypeAndTargetId(String type, String targetType, Long targetId);
    List<Task> findByTargetTypeAndTargetId(String targetType, Long targetId);
}
