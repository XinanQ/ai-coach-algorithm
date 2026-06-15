package com.employee.dto;

import com.employee.Employee;

public class EmployeeResponse {

    private Long id;
    private String name;
    private Integer age;
    private String department;
    private String email;
    private String position;
    private Long organizationId;
    private String level;
    private Boolean isNew;
    private String workType;
    private Boolean isAdmin;
    private Boolean isInProject;

    public static EmployeeResponse from(Employee employee) {
        EmployeeResponse response = new EmployeeResponse();
        response.setId(employee.getId());
        response.setName(employee.getName());
        response.setAge(employee.getAge());
        response.setDepartment(employee.getDepartment());
        response.setEmail(employee.getEmail());
        response.setPosition(employee.getPosition());
        response.setOrganizationId(employee.getOrganizationId());
        response.setLevel(employee.getLevel());
        response.setIsNew(employee.getIsNew());
        response.setWorkType(employee.getWorkType());
        response.setIsAdmin(employee.getIsAdmin());
        response.setIsInProject(employee.getIsInProject());
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

    public Integer getAge() {
        return age;
    }

    public void setAge(Integer age) {
        this.age = age;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getPosition() {
        return position;
    }

    public void setPosition(String position) {
        this.position = position;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public void setOrganizationId(Long organizationId) {
        this.organizationId = organizationId;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public Boolean getIsNew() {
        return isNew;
    }

    public void setIsNew(Boolean isNew) {
        this.isNew = isNew;
    }

    public String getWorkType() {
        return workType;
    }

    public void setWorkType(String workType) {
        this.workType = workType;
    }

    public Boolean getIsAdmin() {
        return isAdmin;
    }

    public void setIsAdmin(Boolean isAdmin) {
        this.isAdmin = isAdmin;
    }

    public Boolean getIsInProject() {
        return isInProject;
    }

    public void setIsInProject(Boolean isInProject) {
        this.isInProject = isInProject;
    }
}
