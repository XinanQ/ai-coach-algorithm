package com.organization;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;

import java.util.List;
import java.util.Optional;

public interface OrganizationService {
    List<Organization> findAll();
    List<Organization> findTree();
    Optional<Organization> findById(Long id);
    Organization save(Organization org);
    void deleteById(Long id);
    List<Organization> findByLevel(OrgLevel level);
}
