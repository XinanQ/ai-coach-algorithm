package com.organization;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;
import com.organization.OrganizationRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

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
        return all.stream().filter(o -> o.getParent() == null).collect(Collectors.toList());
    }

    @Override
    public Optional<Organization> findById(Long id) {
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
}
