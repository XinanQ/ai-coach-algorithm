package com.performance;

import com.employee.Employee;
import com.organization.Organization;
import com.organization.Organization.OrgLevel;
import com.organization.OrganizationRepository;
import com.organization.OrganizationService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashSet;
import java.util.Set;

@Service
@Transactional(readOnly = true)
public class ReviewScopeService {

    private final OrganizationRepository organizationRepository;
    private final OrganizationService organizationService;

    public ReviewScopeService(OrganizationRepository organizationRepository,
                              OrganizationService organizationService) {
        this.organizationRepository = organizationRepository;
        this.organizationService = organizationService;
    }

    public boolean isReviewAdmin(Employee employee) {
        if (employee == null || employee.getOrganization() == null) {
            return false;
        }
        return resolveAdminLevel(employee) != null;
    }

    private OrgLevel resolveAdminLevel(Employee employee) {
        OrgLevel level = normalizeAdminLevel(employee.getLevel());
        if (level != null) {
            return level;
        }
        if (employee.getPosition() != null) {
            return matchChineseAdminLevel(employee.getPosition());
        }
        return null;
    }

    public Set<Long> resolveReviewableOrgIds(Employee admin) {
        if (!isReviewAdmin(admin)) {
            return Set.of();
        }

        OrgLevel adminLevel = resolveAdminLevel(admin);
        if (adminLevel == null) {
            return Set.of();
        }

        // 市行/总行/省行：审核范围 = 整个市行树（与列表可见范围一致）
        if (adminLevel == OrgLevel.CITY) {
            return resolveViewableOrgIds(admin);
        }

        Long scopeRootId = findScopeRootOrgId(admin.getOrganization().getId(), adminLevel);
        if (scopeRootId == null) {
            return Set.of();
        }

        return new HashSet<>(organizationService.findSelfAndDescendantIds(scopeRootId));
    }

    public Set<Long> resolveViewableOrgIds(Employee admin) {
        if (!isReviewAdmin(admin) || admin.getOrganization() == null) {
            return Set.of();
        }

        Long cityRootId = findScopeRootOrgId(admin.getOrganization().getId(), OrgLevel.CITY);
        if (cityRootId == null) {
            return Set.of();
        }

        return new HashSet<>(organizationService.findSelfAndDescendantIds(cityRootId));
    }

    public boolean canReviewSubmitterOrg(Employee admin, Long submitterOrganizationId) {
        if (submitterOrganizationId == null) {
            return false;
        }
        return resolveReviewableOrgIds(admin).contains(submitterOrganizationId);
    }

    private Long findScopeRootOrgId(Long startOrgId, OrgLevel adminLevel) {
        Long currentId = startOrgId;
        while (currentId != null) {
            Organization org = organizationRepository.findByIdWithParent(currentId).orElse(null);
            if (org == null) {
                break;
            }
            if (org.getLevel() == adminLevel) {
                return org.getId();
            }
            Organization parent = org.getParent();
            currentId = parent != null ? parent.getId() : null;
        }
        return null;
    }

    private OrgLevel normalizeAdminLevel(String level) {
        if (level == null || level.isBlank()) {
            return null;
        }
        String normalized = level.trim().toUpperCase();
        return switch (normalized) {
            case "CITY", "HEAD", "HEADQUARTERS", "PROVINCE" -> OrgLevel.CITY;
            case "BRANCH" -> OrgLevel.BRANCH;
            case "OUTLET" -> OrgLevel.OUTLET;
            default -> matchChineseAdminLevel(level.trim());
        };
    }

    private OrgLevel matchChineseAdminLevel(String level) {
        if (level.contains("市行") || level.contains("总行") || level.contains("省行")) {
            return OrgLevel.CITY;
        }
        if (level.contains("支行")) {
            return OrgLevel.BRANCH;
        }
        if (level.contains("网点")) {
            return OrgLevel.OUTLET;
        }
        return null;
    }
}
