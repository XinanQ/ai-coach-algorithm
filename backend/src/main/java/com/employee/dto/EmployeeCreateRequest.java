package com.employee.dto;

import com.employee.Employee;

public class EmployeeCreateRequest {

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

    public Employee toEmployee() {
        Employee employee = new Employee();
        employee.setName(name);
        employee.setAge(age);
        employee.setDepartment(department);
        employee.setEmail(email);
        employee.setPosition(position);
        employee.setOrganizationId(organizationId);
        employee.setLevel(level);
        employee.setIsNew(isNew);
        employee.setWorkType(workType);
        employee.setIsAdmin(isAdmin);
        employee.setIsInProject(isInProject);
        return employee;
    }
}
