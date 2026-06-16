package com.organization;

import com.organization.Organization.OrgLevel;

import java.util.List;
import java.util.Optional;

public interface OrganizationService {

    List<Organization> findAll();

    List<Organization> findTree();

    List<Organization> findVisibleOrganizations();

    List<Organization> findVisibleTree();

    Optional<Organization> findById(Long id);

    Optional<Organization> findVisibleById(Long id);

    Organization save(Organization org);

    void deleteById(Long id);

    List<Organization> findByLevel(OrgLevel level);

    List<Organization> findVisibleByLevel(OrgLevel level);

    List<Long> findSelfAndDescendantIds(Long organizationId);
}