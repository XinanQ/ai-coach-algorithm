package com.organization.dto;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import java.util.Map;

public class OrganizationResponse {

    private Long id;
    private String name;
    private String code;
    private String address;
    private String phone;
    private String description;
    private OrgLevel level;
    private Long parentId;
    private Long staffCount;
    private Long totalStaffCount;
    private Long adminCount;
    private List<OrganizationResponse> children = new ArrayList<>();

    public static OrganizationResponse from(Organization organization) {
        return from(organization, Map.of(), Map.of());
    }

    public static OrganizationResponse from(
            Organization organization,
            Map<Long, Long> staffCountMap,
            Map<Long, Long> adminCountMap
    ) {
        OrganizationResponse response = new OrganizationResponse();
        response.setId(organization.getId());
        response.setName(organization.getName());
        response.setCode(organization.getCode());
        response.setAddress(organization.getAddress());
        response.setPhone(organization.getPhone());
        response.setDescription(organization.getDescription());
        response.setLevel(organization.getLevel());
        response.setParentId(organization.getParent() != null ? organization.getParent().getId() : null);

        Long directStaffCount = staffCountMap.getOrDefault(organization.getId(), 0L);
        response.setStaffCount(directStaffCount);
        Long directAdminCount = adminCountMap.getOrDefault(organization.getId(), 0L);
        response.setAdminCount(directAdminCount);

        long totalStaffCount = directStaffCount;

        if (organization.getChildren() != null) {
            List<OrganizationResponse> childResponses = organization.getChildren().stream()
                    .map(child -> OrganizationResponse.from(child, staffCountMap, adminCountMap))
                    .collect(Collectors.toList());

            response.setChildren(childResponses);

            totalStaffCount += childResponses.stream()
                    .mapToLong(child -> child.getTotalStaffCount() == null ? 0L : child.getTotalStaffCount())
                    .sum();
        }

        response.setTotalStaffCount(totalStaffCount);
        return response;
    }

    public Long getId() { return id; }

    public void setId(Long id) { this.id = id; }

    public String getName() { return name; }

    public void setName(String name) { this.name = name; }

    public String getCode() { return code; }

    public void setCode(String code) { this.code = code; }

    public String getAddress() { return address; }

    public void setAddress(String address) { this.address = address; }

    public String getPhone() { return phone; }

    public void setPhone(String phone) { this.phone = phone; }

    public String getDescription() { return description; }

    public void setDescription(String description) { this.description = description; }

    public OrgLevel getLevel() { return level; }

    public void setLevel(OrgLevel level) { this.level = level; }

    public Long getParentId() { return parentId; }

    public void setParentId(Long parentId) { this.parentId = parentId; }

    public List<OrganizationResponse> getChildren() { return children; }

    public void setChildren(List<OrganizationResponse> children) { this.children = children;}

    public Long getStaffCount() { return staffCount; }

    public void setStaffCount(Long staffCount) { this.staffCount = staffCount; }

    public Long getTotalStaffCount() { return totalStaffCount; }

    public void setTotalStaffCount(Long totalStaffCount) { this.totalStaffCount = totalStaffCount; }

    public Long getAdminCount() { return adminCount; }

    public void setAdminCount(Long adminCount) { this.adminCount = adminCount; }
}
