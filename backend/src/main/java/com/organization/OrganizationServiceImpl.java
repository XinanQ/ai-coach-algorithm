package com.organization;

import com.auth.CurrentUserContext;
import com.organization.Organization.OrgLevel;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
@Transactional
public class OrganizationServiceImpl implements OrganizationService {

    private final OrganizationRepository repo;

    public OrganizationServiceImpl(OrganizationRepository repo) {
        this.repo = repo;
    }

    @Override
    public List<Organization> findAll() {
        return repo.findAll();
    }

    @Override
    public List<Organization> findTree() {
        List<Organization> all = repo.findAll();
        return all.stream()
                .filter(o -> o.getParent() == null)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional(readOnly = true)
    public List<Organization> findVisibleOrganizations() {
        List<Long> visibleIds = findSelfAndDescendantIds(getCurrentOrganizationId());
        return repo.findByIdIn(visibleIds);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Organization> findVisibleTree() {
        Organization root = repo.findById(getCurrentOrganizationId())
                .orElseThrow(() -> new IllegalArgumentException(
                        "Organization not found: " + getCurrentOrganizationId()
                ));

        return List.of(root);
    }

    @Override
    public Optional<Organization> findById(Long id) {
        return repo.findById(id);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<Organization> findVisibleById(Long id) {
        if (id == null) {
            return Optional.empty();
        }

        List<Long> visibleIds = findSelfAndDescendantIds(getCurrentOrganizationId());

        if (!visibleIds.contains(id)) {
            return Optional.empty();
        }

        return repo.findById(id);
    }

    @Override
    public Organization save(Organization org) {
        return repo.save(org);
    }

    @Override
    public void deleteById(Long id) {
        repo.deleteById(id);
    }

    @Override
    public List<Organization> findByLevel(OrgLevel level) {
        return repo.findByLevel(level);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Organization> findVisibleByLevel(OrgLevel level) {
        List<Long> visibleIds = findSelfAndDescendantIds(getCurrentOrganizationId());
        return repo.findByLevelAndIdIn(level, visibleIds);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Long> findSelfAndDescendantIds(Long organizationId) {
        if (organizationId == null) {
            throw new IllegalArgumentException("organizationId cannot be null");
        }

        if (!repo.existsById(organizationId)) {
            throw new IllegalArgumentException("Organization not found: " + organizationId);
        }

        List<Long> result = new ArrayList<>();
        collectSelfAndDescendantIds(organizationId, result);
        return result;
    }

    private Long getCurrentOrganizationId() {
        Long organizationId = CurrentUserContext.getOrganizationId();

        if (organizationId == null) {
            throw new IllegalArgumentException("Current user's organizationId cannot be null");
        }

        return organizationId;
    }

    private void collectSelfAndDescendantIds(Long organizationId, List<Long> result) {
        result.add(organizationId);

        List<Organization> children = repo.findByParentId(organizationId);

        for (Organization child : children) {
            collectSelfAndDescendantIds(child.getId(), result);
        }
    }
}