package com.auth;

import com.auth.dto.LoginRequest;
import com.auth.dto.LoginResponse;

public interface AuthService {

    LoginResponse login(LoginRequest request);
}
