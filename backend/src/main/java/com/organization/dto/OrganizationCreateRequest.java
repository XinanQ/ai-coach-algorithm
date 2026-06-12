package com.organization.dto;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;

public class OrganizationCreateRequest {

    private String name;
    private String code;
    private String address;
    private String phone;
    private String description;
    private OrgLevel level;

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

    public Organization toOrganization() {
        Organization organization = new Organization();
        organization.setName(name);
        organization.setCode(code);
        organization.setAddress(address);
        organization.setPhone(phone);
        organization.setDescription(description);
        organization.setLevel(level);
        return organization;
    }
}
