package com.miniapp.service;

import com.auth.CurrentUserContext;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.miniapp.dto.MiniWorkspaceSummaryResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class MiniAdminWorkspaceService {

    private final EmployeeRepository employeeRepository;

    public MiniAdminWorkspaceService(EmployeeRepository employeeRepository) {
        this.employeeRepository = employeeRepository;
    }

    public MiniWorkspaceSummaryResponse getSummary() {
        Long currentEmployeeId = CurrentUserContext.getEmployeeId();

        if (currentEmployeeId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录，无法访问管理员工作台");
        }

        Employee current = employeeRepository.findByIdWithOrganization(currentEmployeeId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "当前员工不存在"));

        if (!Boolean.TRUE.equals(current.getIsAdmin())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无管理员权限");
        }

        MiniWorkspaceSummaryResponse response = new MiniWorkspaceSummaryResponse();

        // 第一版：后端统计模块还没写，先返回占位值，保证接口和前端联调成功
        response.setTaskCompletionRate(0);
        response.setTaskCompletionRateCompareText("较上周 +0%");

        response.setAverageScore(0.0);
        response.setAverageScoreCompareText("较上周 +0");

        response.setPendingTaskCount(0);
        response.setHighRiskScriptCount(0);

        return response;
    }
}