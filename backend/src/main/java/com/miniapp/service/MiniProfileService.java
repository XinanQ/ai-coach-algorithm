//package com.miniapp.service;
//
//import com.auth.CurrentUserContext;
//import com.auth.UserAccount;
//import com.auth.UserAccountRepository;
//import com.employee.Employee;
//import com.employee.EmployeeRepository;
//import com.miniapp.dto.MiniProfileResponse;
//import com.organization.Organization;
//import org.springframework.stereotype.Service;
//
//@Service
//public class MiniProfileService {
//
//    private final EmployeeRepository employeeRepository;
//    private final UserAccountRepository userAccountRepository;
//
//    public MiniProfileService(EmployeeRepository employeeRepository,
//                              UserAccountRepository userAccountRepository) {
//        this.employeeRepository = employeeRepository;
//        this.userAccountRepository = userAccountRepository;
//    }
//
//    public MiniProfileResponse getCurrentUserProfile() {
//        Long currentEmployeeId = CurrentUserContext.getEmployeeId();
//
//        Employee employee = employeeRepository.findByIdWithOrganization(currentEmployeeId)
//                .orElseThrow(() -> new RuntimeException("Current employee not found"));
//
//        UserAccount account = userAccountRepository.findByEmployeeId(currentEmployeeId)
//                .orElse(null);
//
//        Organization organization = employee.getOrganization();
//
//        MiniProfileResponse response = new MiniProfileResponse();
//
//        response.setEmployeeId(employee.getId());
//        response.setEmployeeNo(account == null ? null : account.getEmployeeNo());
//        response.setName(employee.getName());
//        response.setEmail(employee.getEmail());
//        response.setPosition(employee.getPosition());
//        response.setDepartment(employee.getDepartment());
//        response.setLevel(employee.getLevel());
//        response.setIsAdmin(employee.getIsAdmin());
//        response.setIsInProject(employee.getIsInProject());
//
//        response.setOrganizationId(organization == null ? null : organization.getId());
//        response.setOrganizationName(organization == null ? null : organization.getName());
//        response.setOrganizationCode(organization == null ? null : organization.getCode());
//
//        response.setOrganizationLevel(
//                organization == null || organization.getLevel() == null
//                        ? null
//                        : organization.getLevel().name()
//        );
//
//        return response;
//    }
//}

package com.miniapp.service;

import com.auth.CurrentUserContext;
import com.auth.UserAccount;
import com.auth.UserAccountRepository;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import com.miniapp.dto.MiniProfileResponse;
import com.miniapp.dto.MiniProfileSummaryResponse;
import com.organization.Organization;
import org.springframework.stereotype.Service;

@Service
public class MiniProfileService {

    private final EmployeeRepository employeeRepository;
    private final UserAccountRepository userAccountRepository;

    public MiniProfileService(EmployeeRepository employeeRepository,
                              UserAccountRepository userAccountRepository) {
        this.employeeRepository = employeeRepository;
        this.userAccountRepository = userAccountRepository;
    }

    //我的页顶部卡片：只返回摘要
    public MiniProfileSummaryResponse getCurrentUserProfile() {
        Employee employee = getCurrentEmployee();
        Organization organization = employee.getOrganization();

        MiniProfileSummaryResponse response = new MiniProfileSummaryResponse();

        response.setName(employee.getName());
        response.setOrganizationName(organization == null ? null : organization.getName());
        response.setIsAdmin(employee.getIsAdmin());

        String roleName = Boolean.TRUE.equals(employee.getIsAdmin())
                ? "管理员"
                : "普通员工";
        response.setRoleName(roleName);

        return response;
    }

    //点击黑色卡片后的账号详情页：返回完整账号信息
    public MiniProfileResponse getCurrentUserAccount() {
        Employee employee = getCurrentEmployee();

        Long currentEmployeeId = employee.getId();

        UserAccount account = userAccountRepository.findByEmployeeId(currentEmployeeId)
                .orElse(null);

        Organization organization = employee.getOrganization();

        MiniProfileResponse response = new MiniProfileResponse();

        response.setEmployeeId(employee.getId());
        response.setEmployeeNo(account == null ? null : account.getEmployeeNo());
        response.setName(employee.getName());
        response.setEmail(employee.getEmail());
        response.setPosition(employee.getPosition());
        response.setDepartment(employee.getDepartment());
        response.setLevel(employee.getLevel());
        response.setIsAdmin(employee.getIsAdmin());
        response.setIsInProject(employee.getIsInProject());

        response.setOrganizationId(organization == null ? null : organization.getId());
        response.setOrganizationName(organization == null ? null : organization.getName());
        response.setOrganizationCode(organization == null ? null : organization.getCode());

        response.setOrganizationLevel(
                organization == null || organization.getLevel() == null
                        ? null
                        : organization.getLevel().name()
        );

        return response;
    }

    //根据当前登录用户拿员工
    private Employee getCurrentEmployee() {
        Long currentEmployeeId = CurrentUserContext.getEmployeeId();

        if (currentEmployeeId == null) {
            throw new RuntimeException("Current user not found. Missing or invalid token.");
        }

        return employeeRepository.findByIdWithOrganization(currentEmployeeId)
                .orElseThrow(() -> new RuntimeException("Current employee not found"));
    }
}