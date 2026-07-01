package com.employee;

import com.organization.Organization;
import com.organization.Organization.OrgLevel;

/**
 * 员工 level 表示管理身份（审核范围、登录角色等），与自由填写的「职务」无关。
 * 规则：非管理员固定为 EMPLOYEE；管理员与其所属机构的 OrgLevel 对齐。
 */
public final class EmployeeLevelResolver {

    private EmployeeLevelResolver() {
    }

    public static String inferLevel(Boolean isAdmin, Organization organization) {
        if (!Boolean.TRUE.equals(isAdmin)) {
            return "EMPLOYEE";
        }
        if (organization == null || organization.getLevel() == null) {
            return "EMPLOYEE";
        }
        return switch (organization.getLevel()) {
            case HEADQUARTERS, PROVINCE, CITY -> "CITY";
            case BRANCH -> "BRANCH";
            case OUTLET -> "OUTLET";
        };
    }

    public static void applyInferredLevel(Employee employee) {
        if (employee == null) {
            return;
        }
        employee.setLevel(inferLevel(employee.getIsAdmin(), employee.getOrganization()));
    }
}
