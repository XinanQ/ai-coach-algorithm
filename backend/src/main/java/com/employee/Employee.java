package com.employee;

import jakarta.persistence.*;

@Entity
@Table(name = "employees")
public class Employee {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // === 原有字段（全部保留）===
    private String name;
    private Integer age;
    private String department;
    private String email;
    private String position;
    private Long organizationId;

    // === 新增字段（根据需求文档）===
    private String level;          // 级别（总行/省行/市行/支行/网点）
    private Boolean isNew;         // 是否新员工
    private String workType;       // 内勤/外勤
    private Boolean isAdmin;       // 是否是管理员
    private Boolean isInProject;   // 是否参加项目

    // === 构造方法 ===
    public Employee() {
    }

    // === 原有 Getter/Setter ===
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

    // === 新增 Getter/Setter ===
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