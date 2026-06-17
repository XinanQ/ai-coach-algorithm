package com.auth;

import com.auth.dto.LoginRequest;
import com.auth.dto.LoginResponse;
import com.employee.Employee;
import com.employee.EmployeeRepository;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthServiceImpl implements AuthService {

    private static final String ACTIVE_STATUS = "ACTIVE";

    private final UserAccountRepository userAccountRepository;
    private final EmployeeRepository employeeRepository;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    private final AuthTokenService authTokenService;

    public AuthServiceImpl(UserAccountRepository userAccountRepository,
                           EmployeeRepository employeeRepository,
                           AuthTokenService authTokenService) {
        this.userAccountRepository = userAccountRepository;
        this.employeeRepository = employeeRepository;
        this.authTokenService = authTokenService;
    }

    @Override
    public LoginResponse login(LoginRequest request) {
        validateLoginRequest(request);

        UserAccount account = userAccountRepository.findByEmployeeNo(request.getEmployeeNo())
                .orElseThrow(() -> new AuthException(
                        HttpStatus.UNAUTHORIZED,
                        401,
                        "Invalid employee number or password"
                ));

        if (!ACTIVE_STATUS.equals(account.getStatus())) {
            throw new AuthException(
                    HttpStatus.FORBIDDEN,
                    403,
                    "Account is disabled"
            );
        }

        boolean passwordMatches = passwordEncoder.matches(
                request.getPassword(),
                account.getPasswordHash()
        );

        if (!passwordMatches) {
            throw new AuthException(
                    HttpStatus.UNAUTHORIZED,
                    401,
                    "Invalid employee number or password"
            );
        }

        Employee employee = employeeRepository.findById(account.getEmployeeId())
                .orElseThrow(() -> new AuthException(
                        HttpStatus.FORBIDDEN,
                        403,
                        "Employee profile not found"
                ));

//        if (Boolean.FALSE.equals(employee.getIsInProject())) {
//            throw new AuthException(
//                    HttpStatus.FORBIDDEN,
//                    403,
//                    "Employee is not in project"
//            );
//        }

        String token = authTokenService.createToken(employee.getId());

        Long organizationId = employee.getOrganization() == null
                ? null
                : employee.getOrganization().getId();

        String organizationName = employee.getOrganization() == null
                ? null
                : employee.getOrganization().getName();

        return new LoginResponse(
                employee.getId(),
                account.getEmployeeNo(),
                employee.getName(),
                employee.getPosition(),
                employee.getLevel(),
                employee.getIsAdmin(),
                organizationId,
                organizationName,
                employee.getIsInProject(),
                token
        );
    }

    private void validateLoginRequest(LoginRequest request) {
        if (request == null
                || request.getEmployeeNo() == null
                || request.getEmployeeNo().isBlank()
                || request.getPassword() == null
                || request.getPassword().isBlank()) {
            throw new AuthException(
                    HttpStatus.BAD_REQUEST,
                    400,
                    "Employee number and password are required"
            );
        }
    }
}
