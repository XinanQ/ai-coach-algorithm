package com.project;

import jakarta.persistence.*;

/**
 * 项目参与机构范围：限定哪些机构（含其下级）可以看到/参与该项目。
 * 为空表示不限制（所有机构可见，兼容历史数据）。
 */
@Entity
@Table(
        name = "project_visible_orgs",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_project_visible_org",
                columnNames = {"project_id", "organization_id"}
        )
)
public class ProjectVisibleOrg {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "organization_id", nullable = false)
    private Long organizationId;

    public ProjectVisibleOrg() {
    }

    public ProjectVisibleOrg(Long projectId, Long organizationId) {
        this.projectId = projectId;
        this.organizationId = organizationId;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getProjectId() {
        return projectId;
    }

    public void setProjectId(Long projectId) {
        this.projectId = projectId;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public void setOrganizationId(Long organizationId) {
        this.organizationId = organizationId;
    }
}
