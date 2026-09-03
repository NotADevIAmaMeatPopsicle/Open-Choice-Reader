from app.services.login_throttle import LoginAttemptLimiter


def test_login_attempt_limiter_blocks_and_expires_failures() -> None:
    limiter = LoginAttemptLimiter(max_attempts=2, window_seconds=60)

    limiter.record_failure("client:alice", now=10)
    assert limiter.retry_after("client:alice", now=20) is None

    limiter.record_failure("client:alice", now=20)
    assert limiter.retry_after("client:alice", now=30) == 40
    assert limiter.retry_after("client:alice", now=71) is None


def test_login_attempt_limiter_can_be_cleared_after_success() -> None:
    limiter = LoginAttemptLimiter(max_attempts=1, window_seconds=60)
    limiter.record_failure("client:alice", now=10)
    limiter.clear("client:alice")
    assert limiter.retry_after("client:alice", now=11) is None
