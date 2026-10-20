"""Test 15: Security test verifying API keys are never written to logs."""

import logging
from app.security.sanitizer import mask_secrets, SensitiveDataFilter


def test_mask_secrets_patterns():
    openai_key = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
    anthropic_key = "sk-ant-api03-abcdef1234567890abcdef1234567890"
    gemini_key = "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"

    text_with_keys = (
        f"Connecting to OpenAI with key {openai_key} and Gemini {gemini_key} and Anthropic {anthropic_key}"
    )

    masked = mask_secrets(text_with_keys)

    assert openai_key not in masked
    assert anthropic_key not in masked
    assert gemini_key not in masked
    assert "MASKED_KEY" in masked


def test_sqlite_logger_masks_keys(temp_db):
    secret_key = "sk-proj-SECRETKEY98765432101234567890"
    temp_db.append_log("test_job", "INFO", f"Configuring adapter with key: {secret_key}")

    logs = temp_db.get_logs("test_job")
    assert len(logs) == 1
    log_msg = logs[0]["message"]
    assert secret_key not in log_msg
    assert "MASKED_KEY" in log_msg
