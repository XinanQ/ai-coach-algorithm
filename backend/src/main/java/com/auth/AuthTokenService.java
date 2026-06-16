package com.auth;

import com.employee.Employee;
import com.employee.EmployeeRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
public class AuthTokenService {

    private static final int TOKEN_EXPIRE_HOURS = 8;

    private final AuthSessionRepository authSessionRepository;
    private final EmployeeRepository employeeRepository;

    public AuthTokenService(AuthSessionRepository authSessionRepository,
                            EmployeeRepository employeeRepository) {
        this.authSessionRepository = authSessionRepository;
        this.employeeRepository = employeeRepository;
    }

    @Transactional
    public String createToken(Long employeeId) {
        String token = UUID.randomUUID().toString().replace("-", "");
        LocalDateTime expiresAt = LocalDateTime.now().plusHours(TOKEN_EXPIRE_HOURS);

        AuthSession session = new AuthSession(token, employeeId, expiresAt);
        authSessionRepository.save(session);

        return token;
    }

    @Transactional(readOnly = true)
    public Employee getEmployeeByToken(String token) {
        if (token == null || token.isBlank()) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, 401, "Missing auth token");
        }

        AuthSession session = authSessionRepository.findByToken(token)
                .orElseThrow(() -> new AuthException(HttpStatus.UNAUTHORIZED, 401, "Invalid auth token"));

        if (session.isExpired()) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, 401, "Auth token expired");
        }

        return employeeRepository.findById(session.getEmployeeId())
                .orElseThrow(() -> new AuthException(HttpStatus.UNAUTHORIZED, 401, "Login employee not found"));
    }

    @Transactional
    public void deleteToken(String token) {
        if (token != null && !token.isBlank()) {
            authSessionRepository.deleteByToken(token);
        }
    }
}