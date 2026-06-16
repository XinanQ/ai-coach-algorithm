package com.auth.dto;

public class LoginResponse {

    private Long employeeId;
    private String employeeNo;
    private String name;
    private String level;
    private Boolean isAdmin;
    private Long organizationId;
    private Boolean isInProject;
    private String token;

    public LoginResponse(Long employeeId,
                         String employeeNo,
                         String name,
                         String level,
                         Boolean isAdmin,
                         Long organizationId,
                         Boolean isInProject,
                         String token) {
        this.employeeId = employeeId;
        this.employeeNo = employeeNo;
        this.name = name;
        this.level = level;
        this.isAdmin = isAdmin;
        this.organizationId = organizationId;
        this.isInProject = isInProject;
        this.token = token;
    }

    public Long getEmployeeId() {
        return employeeId;
    }

    public String getEmployeeNo() {
        return employeeNo;
    }

    public String getName() {
        return name;
    }

    public String getLevel() {
        return level;
    }

    public Boolean getIsAdmin() {
        return isAdmin;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public Boolean getIsInProject() {
        return isInProject;
    }

    public String getToken() { return token;
    }
}
