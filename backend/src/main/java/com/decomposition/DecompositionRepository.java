package com.decomposition;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DecompositionRepository extends JpaRepository<DecompositionRecord, Long> {
    List<DecompositionRecord> findByOwnerRole(String ownerRole);
    List<DecompositionRecord> findByOwnerRoleAndCurrentOrgId(String ownerRole, Long currentOrgId);
    List<DecompositionRecord> findByProjectId(Long projectId);
    List<DecompositionRecord> findByProjectIdAndCurrentOrgId(Long projectId, Long currentOrgId);
    List<DecompositionRecord> findByCurrentOrgId(Long currentOrgId);
    List<DecompositionRecord> findByOwnerRoleAndCurrentOrgIdAndProjectId(String ownerRole, Long currentOrgId, Long projectId);
    java.util.Optional<DecompositionRecord> findByExternalId(String externalId);
    List<DecompositionRecord> findAllByExternalId(String externalId);
}
