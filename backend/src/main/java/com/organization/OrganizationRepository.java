package com.organization;

import com.organization.Organization.OrgLevel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

@Repository
public interface OrganizationRepository extends JpaRepository<Organization, Long> {

    List<Organization> findByLevel(OrgLevel level);

    List<Organization> findByParentId(Long parentId);

    List<Organization> findByIdIn(Collection<Long> ids);

    List<Organization> findByLevelAndIdIn(OrgLevel level, Collection<Long> ids);

    @Query("SELECT o FROM Organization o LEFT JOIN FETCH o.parent WHERE o.id = :id")
    Optional<Organization> findByIdWithParent(Long id);
}