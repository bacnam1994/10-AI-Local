"""Sanitization and Security Utilities."""

import re
import logging
from pathlib import Path

# Common API Key Patterns
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{15,}", re.IGNORECASE),          # OpenAI
    re.compile(r"AIzaSy[a-zA-Z0-9_-]{20,}", re.IGNORECASE),        # Google Gemini
    re.compile(r"sk-ant-[a-zA-Z0-9_-]{15,}", re.IGNORECASE),      # Anthropic
    re.compile(r"(api[_-]?key|secret|password|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{12,})['\"]?", re.IGNORECASE),
]

UNSAFE_FILENAME_CHARS = re.compile(r'[\\/*?:"<>|]')


def mask_secrets(text: str, additional_secrets: list[str] | None = None) -> str:
    """Mask any sensitive API keys or credentials in a given text."""
    if not text:
        return text

    sanitized = text

    # Mask known additional secrets first
    if additional_secrets:
        for secret in additional_secrets:
            if secret and len(secret) >= 6:
                masked = secret[:3] + "..." + secret[-3:]
                sanitized = sanitized.replace(secret, f"***MASKED_SECRET[{masked}]***")

    # Mask pattern matches
    for pattern in SECRET_PATTERNS:
        def _replace_match(match: re.Match) -> str:
            val = match.group(0)
            if len(val) > 8:
                return val[:4] + "***[MASKED_KEY]***" + val[-4:]
            return "***[MASKED_KEY]***"

        sanitized = pattern.sub(_replace_match, sanitized)

    return sanitized


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts API keys and sensitive tokens before writing to logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_secrets(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(mask_secrets(str(v)) if isinstance(v, str) else v for v in record.args)
        return True


def sanitize_filename(filename: str, default: str = "document") -> str:
    """Clean a string to be safely used as a Windows filename."""
    if not filename:
        return default
    
    # Replace unsafe characters with underscore
    clean = UNSAFE_FILENAME_CHARS.sub("_", filename)
    clean = clean.strip(". ")
    clean = re.sub(r"\s+", " ", clean)
    
    if not clean:
        return default
    return clean[:120]


def validate_path_traversal(target_path: Path, allowed_root: Path) -> Path:
    """Ensure target_path resolves strictly inside allowed_root.
    Raises PermissionError if path traversal is attempted.
    """
    resolved_target = target_path.resolve()
    resolved_root = allowed_root.resolve()

    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        raise PermissionError(
            f"Security Violation: Target path '{resolved_target}' is outside allowed directory '{resolved_root}'"
        )

    return resolved_target


def resolve_safe_output_path(base_dir: Path, filename: str, allow_overwrite: bool = False) -> Path:
    """Resolve a safe output path.
    If allow_overwrite is False and the file exists, append an incremental version suffix (_v1, _v2, etc.).
    """
    safe_name = sanitize_filename(filename)
    dest_path = base_dir / safe_name
    
    # Ensure no path traversal
    dest_path = validate_path_traversal(dest_path, base_dir)

    if allow_overwrite or not dest_path.exists():
        return dest_path

    # Handle duplicate without overwriting
    stem = dest_path.stem
    suffix = dest_path.suffix
    counter = 1
    
    while dest_path.exists():
        dest_path = base_dir / f"{stem}_v{counter}{suffix}"
        counter += 1

    return dest_path
