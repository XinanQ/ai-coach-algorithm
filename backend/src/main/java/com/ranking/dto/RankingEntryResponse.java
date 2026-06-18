package com.ranking.dto;

import java.math.BigDecimal;

/**
 * 单条排名记录，字段名与前端 Rankings.vue 对齐（points、organization、name、rank）。
 */
public class RankingEntryResponse {

    private int rank;
    private Long id;
    private String name;
    private String organization;
    private Long organizationId;
    private BigDecimal points;

    public int getRank() {
        return rank;
    }

    public void setRank(int rank) {
        this.rank = rank;
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

    public String getOrganization() {
        return organization;
    }

    public void setOrganization(String organization) {
        this.organization = organization;
    }

    public Long getOrganizationId() {
        return organizationId;
    }

    public void setOrganizationId(Long organizationId) {
        this.organizationId = organizationId;
    }

    public BigDecimal getPoints() {
        return points;
    }

    public void setPoints(BigDecimal points) {
        this.points = points;
    }
}
