package com.organization.dto;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class OrganizationResponse {

    private Long id;
    private String name;
    private String code;
    private String address;
    private String phone;
    private String description;
    private OrgLevel level;
    private Long parentId;
    private List<OrganizationResponse> children = new ArrayList<>();

    public static OrganizationResponse from(Organization organization) {
        OrganizationResponse response = new OrganizationResponse();
        response.setId(organization.getId());
        response.setName(organization.getName());
        response.setCode(organization.getCode());
        response.setAddress(organization.getAddress());
        response.setPhone(organization.getPhone());
        response.setDescription(organization.getDescription());
        response.setLevel(organization.getLevel());
        response.setParentId(organization.getParent() != null ? organization.getParent().getId() : null);
        if (organization.getChildren() != null) {
            response.setChildren(organization.getChildren().stream()
                    .map(OrganizationResponse::from)
                    .collect(Collectors.toList()));
        }
        return response;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public OrgLevel getLevel() {
        return level;
    }

    public void setLevel(OrgLevel level) {
        this.level = level;
    }

    public Long getParentId() {
        return parentId;
    }

    public void setParentId(Long parentId) {
        this.parentId = parentId;
    }

    public List<OrganizationResponse> getChildren() {
        return children;
    }

    public void setChildren(List<OrganizationResponse> children) {
        this.children = children;
    }
}
