package com.project;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ProjectVisibleOrgRepository extends JpaRepository<ProjectVisibleOrg, Long> {

    List<ProjectVisibleOrg> findByProjectId(Long projectId);

    void deleteByProjectId(Long projectId);
}
