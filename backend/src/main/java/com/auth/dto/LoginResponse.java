package com.auth.dto;

public class LoginResponse {

    private Long employeeId;
    private String employeeNo;
    private String name;
    private String position;
    private String level;
    private Boolean isAdmin;
    private Long organizationId;
    private Boolean isInProject;
    private String token;
    private String organizationName;
    private String organizationCode;

    public LoginResponse(Long employeeId,
                         String employeeNo,
                         String name,
                         String position,
                         String level,
                         Boolean isAdmin,
                         Long organizationId,
                         String organizationName,
                         String organizationCode,
                         Boolean isInProject,
                         String token) {
        this.employeeId = employeeId;
        this.employeeNo = employeeNo;
        this.name = name;
        this.position = position;
        this.level = level;
        this.isAdmin = isAdmin;
        this.organizationId = organizationId;
        this.organizationName = organizationName;
        this.organizationCode = organizationCode;
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

    public String getPosition() {
        return position;
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

    public String getToken() {
        return token;
    }

    public String getOrganizationName() {
        return organizationName;
    }

    public String getOrganizationCode() {
        return organizationCode;
    }
}
