package com.auth;

import com.auth.dto.LoginRequest;
import com.auth.dto.LoginResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody LoginRequest request) {
        try {
            LoginResponse loginResponse = authService.login(request);

            Map<String, Object> body = new HashMap<>();
            body.put("code", 200);
            body.put("message", "Login successful");
            body.put("data", loginResponse);

            return ResponseEntity.ok(body);

        } catch (AuthException ex) {
            Map<String, Object> body = new HashMap<>();
            body.put("code", ex.getCode());
            body.put("message", ex.getMessage());
            body.put("data", null);

            return ResponseEntity.status(ex.getStatus()).body(body);
        }
    }
}
