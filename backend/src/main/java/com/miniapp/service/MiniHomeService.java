package com.miniapp.service;

import com.auth.CurrentUserContext;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.miniapp.dto.MiniHomeResponse;
import com.organization.Organization;
import org.springframework.stereotype.Service;

@Service
public class MiniHomeService {

    private final EmployeeRepository employeeRepository;

    public MiniHomeService(EmployeeRepository employeeRepository) {
        this.employeeRepository = employeeRepository;
    }

    public MiniHomeResponse getCurrentUserHome() {
        Long currentEmployeeId = CurrentUserContext.getEmployeeId();

        Employee employee = employeeRepository.findByIdWithOrganization(currentEmployeeId)
                .orElseThrow(() -> new RuntimeException("Current employee not found"));

        Organization organization = employee.getOrganization();

        MiniHomeResponse response = new MiniHomeResponse();

        response.setName(employee.getName());
        response.setLevel(employee.getLevel());
        response.setIsAdmin(employee.getIsAdmin());

        response.setOrganizationId(organization == null ? null : organization.getId());
        response.setOrganizationName(organization == null ? null : organization.getName());

        // TODO: Replace default values after points, ranking, report and practice modules are ready.
        response.setMonthlyScore(0);
        response.setScoreTarget(0);
        response.setCompletionRate(0);
        response.setRank(null);
        response.setRankScope("暂无排名");
        response.setTodayReported(false);
        response.setPendingPracticeTaskCount(0);

        return response;
    }
}