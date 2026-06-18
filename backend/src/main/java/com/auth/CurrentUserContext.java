package com.auth;

import com.employee.Employee;

public class CurrentUserContext {

    private static final ThreadLocal<Employee> CURRENT_USER = new ThreadLocal<>();

    private CurrentUserContext() {
    }

    public static void set(Employee employee) {
        CURRENT_USER.set(employee);
    }

    public static Employee get() {
        return CURRENT_USER.get();
    }

    public static Long getEmployeeId() {
        Employee employee = get();
        return employee == null ? null : employee.getId();
    }

    public static Long getOrganizationId() {
        Employee employee = get();

        if (employee == null || employee.getOrganization() == null) {
            return null;
        }

        return employee.getOrganization().getId();
    }

    public static Boolean getIsAdmin() {
        Employee employee = get();
        return employee == null ? null : employee.getIsAdmin();
    }

    public static void clear() {
        CURRENT_USER.remove();
    }
}