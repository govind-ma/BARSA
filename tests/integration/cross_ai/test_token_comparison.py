"""Empirical token comparison tests across full-history, manual summary, and Barsa Smart Context (Phase 12)."""

from __future__ import annotations

from barsa.integrations.evaluation import TokenBenchmarkEvaluator


def test_token_benchmark_comparison_three_conditions() -> None:
    """Benchmark token consumption between Full-History, Manual Summary, and Barsa SCE."""
    # 1. Full-History Baseline: Simulated 20-turn conversation with logs, code snippets, and debugging
    full_history = (
        """
    USER: We need to build a Spring Boot Authentication Service with JWT.
    ASSISTANT: I'll help you design and build that. First, let's create the project structure.
    Here is the pom.xml with spring-boot-starter-web and spring-boot-starter-security dependencies...
    [... 50 lines of XML pom.xml ...]
    USER: Now let's implement the User model with username, password, email, and roles.
    ASSISTANT: Here is User.java:
    package com.example.auth.model;
    public class User {
        private String id;
        private String username;
        private String password;
        private String email;
        private List<String> roles;
        // getters and setters...
    }
    USER: Can you add password hashing?
    ASSISTANT: Yes, we should use BCryptPasswordEncoder. Here is the configuration...
    USER: Now implement the JwtUtil class with HS512 key signing and claims parsing.
    ASSISTANT: Here is the code for JwtUtil.java with generateToken, validateToken, getUsernameFromToken, and isTokenExpired.
    [... 100 lines of Java code ...]
    USER: I tried running it and got an exception: io.jsonwebtoken.security.WeakKeyException: The specified key byte array is 256 bits which is insecure for HS512.
    ASSISTANT: That exception happens because HS512 requires at least a 512-bit key. Let's increase the secret key string length to 64 bytes...
    USER: That fixed it. Now what's next?
    ASSISTANT: Next is creating the AuthController with POST /api/auth/login and POST /api/auth/register.
    USER: Let's create AuthController.java.
    ASSISTANT: Here is AuthController.java:
    [... 80 lines of Java controller code ...]
    USER: The login works. What should we do next?
    ASSISTANT: The next task is to implement the JWT token refresh endpoint (/api/auth/refresh) so access tokens can be refreshed without requiring re-login.
    """
        * 3
    )  # Realistic multi-turn length (~10,000+ characters, 2,500+ tokens)

    # 2. Manual Summary Baseline: Human notes or ad-hoc summary
    manual_summary = """
    Project: Spring Boot Auth Service.
    We created pom.xml and User.java.
    We implemented JwtUtil with HS512 after fixing a WeakKeyException by using a 512-bit secret.
    We implemented AuthController.java with /api/auth/login and /api/auth/register.
    Next task: implement refresh token endpoint /api/auth/refresh.
    """

    # 3. Barsa Smart Context Engine: High-density, authoritative BMS structured representation
    barsa_context = """
    # BARSA PROJECT CONTEXT
    Project: Spring Boot JWT Authentication Service (proj-spring-auth)
    Authoritative Revision: c0ffee5120
    Status: active
    Current Task: task-login-endpoint (Completed)
    Next Task: Implement JWT token refresh endpoint (/api/auth/refresh)
    Completed Actions:
      - Implemented User model and JwtUtil with HS512
      - Implemented POST /api/auth/login with validation
    Approved Decisions:
      - dec-symmetric-hs512: Use HMAC-SHA512 for JWT Signing (512-bit symmetric secret)
    Artifacts:
      - examples/spring_boot_auth/src/main/java/com/example/auth/model/User.java (source_code)
      - examples/spring_boot_auth/src/main/java/com/example/auth/security/JwtUtil.java (source_code)
    """

    # Run Benchmark
    benchmarks = TokenBenchmarkEvaluator.run_comparison(
        full_conversation_transcript=full_history,
        manual_written_summary=manual_summary,
        barsa_rendered_context=barsa_context,
        expected_next_task="Implement JWT token refresh endpoint (/api/auth/refresh)",
    )

    assert len(benchmarks) == 3
    b_full = next(b for b in benchmarks if b.condition == "full_history_baseline")
    b_manual = next(b for b in benchmarks if b.condition == "manual_summary_baseline")
    b_barsa = next(b for b in benchmarks if b.condition == "barsa_optimized_context")

    # 1. Full History has the largest token footprint
    assert b_full.input_tokens > b_manual.input_tokens
    assert b_full.input_tokens > b_barsa.input_tokens

    # 2. Token Savings: Barsa achieves > 70% token reduction compared to Full History
    token_savings = ((b_full.input_tokens - b_barsa.input_tokens) / b_full.input_tokens) * 100.0
    assert token_savings > 70.0, f"Expected > 70% savings, got {token_savings:.1f}%"

    # 3. Information Integrity: Manual summary misses machine-readable commit and checkpoint hashes
    assert len(b_manual.missing_critical_info) > 0
    assert "exact_checkpoint_id" in b_manual.missing_critical_info

    # 4. Barsa preserves 100% of critical resumption info with zero missing fields
    assert len(b_barsa.missing_critical_info) == 0
    assert b_barsa.task_continuation_success is True


def test_token_counting_deterministic_behavior() -> None:
    """Verify TokenBenchmarkEvaluator token counting handles both short and long text deterministically."""
    short_text = "Hello world from Barsa AI memory."
    long_text = short_text * 100

    c_short = TokenBenchmarkEvaluator.count_tokens(short_text)
    c_long = TokenBenchmarkEvaluator.count_tokens(long_text)

    assert c_short > 0
    assert c_long > c_short * 80
