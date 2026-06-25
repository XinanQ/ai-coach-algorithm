package com.dashboard.dto;

/**
 * 进行中项目进度条目（列表只含 ACTIVE 项目，故不再单列状态）。
 * completionRate 为真实完成率（已审核上报值 / 目标值），无目标值时为 null，前端展示「—」。
 * daysToDeadline 为距项目截止天数（可为负，表示已逾期）。
 */
public class DashboardProjectItem {

    private Long id;
    private String name;
    private Integer completionRate;
    private Integer daysToDeadline;

    public DashboardProjectItem() {
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

    public Integer getCompletionRate() {
        return completionRate;
    }

    public void setCompletionRate(Integer completionRate) {
        this.completionRate = completionRate;
    }

    public Integer getDaysToDeadline() {
        return daysToDeadline;
    }

    public void setDaysToDeadline(Integer daysToDeadline) {
        this.daysToDeadline = daysToDeadline;
    }
}
