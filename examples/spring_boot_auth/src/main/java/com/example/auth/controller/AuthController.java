package com.example.auth.controller;

import com.example.auth.model.User;
import com.example.auth.security.JwtUtil;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final JwtUtil jwtUtil;
    private final Map<String, User> userDatabase = new ConcurrentHashMap<>();

    public AuthController(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
        // Seed initial admin user
        userDatabase.put("admin", new User("admin", "hash_secret123", "ADMIN"));
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");
        if (username == null || password == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username and password required"));
        }
        if (userDatabase.containsKey(username)) {
            return ResponseEntity.status(409).body(Map.of("error", "Username already exists"));
        }
        User newUser = new User(username, "hash_" + password, "USER");
        userDatabase.put(username, newUser);
        return ResponseEntity.ok(Map.of("message", "User registered successfully", "username", username));
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");
        User user = userDatabase.get(username);
        if (user == null || !("hash_" + password).equals(user.getPasswordHash())) {
            return ResponseEntity.status(401).body(Map.of("error", "Invalid credentials"));
        }
        String token = jwtUtil.generateToken(username, user.getRole());
        return ResponseEntity.ok(Map.of("access_token", token, "token_type", "Bearer"));
    }

    // Task 2: Token Refresh Endpoint (Assigned to Agent B for Cross-AI continuation)
    @PostMapping("/refresh")
    public ResponseEntity<?> refreshToken(@RequestHeader(value = "Authorization", required = false) String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(401).body(Map.of("error", "Missing or invalid Bearer token"));
        }
        try {
            String token = authHeader.substring(7);
            String username = jwtUtil.extractUsername(token);
            User user = userDatabase.get(username);
            if (user == null) {
                return ResponseEntity.status(401).body(Map.of("error", "User not found"));
            }
            String newToken = jwtUtil.generateToken(username, user.getRole());
            return ResponseEntity.ok(Map.of("access_token", newToken, "token_type", "Bearer"));
        } catch (Exception e) {
            return ResponseEntity.status(401).body(Map.of("error", "Invalid or expired token"));
        }
    }
}
