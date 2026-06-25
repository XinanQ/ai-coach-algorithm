package com.dashboard.dto;

/**
 * 待审核上报条目（仅管理者视图）。前端「待办中心」用，点击跳转业绩审核页。
 */
public class DashboardPendingReviewItem {

    private Long id;
    private String submitter;
    private String result;
    private String reportDate;

    public DashboardPendingReviewItem() {
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getSubmitter() {
        return submitter;
    }

    public void setSubmitter(String submitter) {
        this.submitter = submitter;
    }

    public String getResult() {
        return result;
    }

    public void setResult(String result) {
        this.result = result;
    }

    public String getReportDate() {
        return reportDate;
    }

    public void setReportDate(String reportDate) {
        this.reportDate = reportDate;
    }
}
