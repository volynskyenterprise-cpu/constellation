from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .simple_yaml import YamlError, load_yaml


class PkosSmartSyncError(RuntimeError):
    pass


CLASSIFICATIONS = {
    "production_knowledge",
    "governed_operations",
    "approved_research",
    "draft_research",
    "generated_output",
    "runtime_artifact",
    "temporary_file",
    "private_or_secret",
    "configuration",
    "tooling",
    "unknown",
}

ACTIONS = {"stage", "exclude", "review", "block"}
SECRET_PATH_PATTERNS = [
    "*secret*",
    "*credential*",
    "*token*",
    ".env",
    "*.pem",
    "*oauth*",
    "*client_secret*",
]
SECRET_CONTENT_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
]
SECRET_IDENTIFIERS = {
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "client_secret",
    "clientsecret",
    "password",
    "secret",
    "private_key",
}
PLACEHOLDER_SECRET_VALUES = {
    "",
    "none",
    "null",
    "redacted",
    "[redacted]",
    "your_api_key",
    "your-api-key",
    "change_me",
    "changeme",
    "example",
    "dummy",
    "test-token",
    "test_token",
}
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(?P<identifier>\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|private[_-]?key|secret)\b)\s*[:=]\s*(?P<value>.+)"
)
SECRET_MAPPING_VALUE_PATTERN = re.compile(
    r"(?i)(?P<quote>['\"])(?P<identifier>api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|private[_-]?key|secret)(?P=quote)\s*:\s*(?P<value>.+)"
)
SECRET_ENV_FALLBACK_PATTERN = re.compile(
    r"(?i)(?:os\.)?getenv\(\s*['\"][A-Z0-9_]*(?:API[_-]?KEY|ACCESS[_-]?TOKEN|REFRESH[_-]?TOKEN|CLIENT[_-]?SECRET|PASSWORD|SECRET|PRIVATE[_-]?KEY)['\"]\s*,\s*(?P<value>[^)]+)\)"
)
SAFE_SECRET_REFERENCE_PATTERNS = [
    ("secret-reference:attribute-read", re.compile(r"(?i)\.\s*(refresh_token|client_secret|api_key|access_token|private_key)\b")),
    ("secret-reference:config-lookup", re.compile(r"(?i)(?:get\(\s*|in\s+|[\[]\s*)['\"](?:refresh_token|client_secret|api_key|access_token|client_id|private_key)['\"]")),
    ("secret-reference:credential-file-loader", re.compile(r"Credentials\.from_authorized_user_file|InstalledAppFlow\.from_client_secrets_file")),
    ("secret-reference:parameter-or-field", re.compile(r"(?i)\b(?:def\s+\w+\([^)]*(?:refresh_token|client_secret|api_key)|(?:refresh_token|client_secret|api_key)\s*:\s*[^=])")),
]
GENERATED_SEGMENTS = {"logs", "log", "cache", "caches", "exports", "output", "outputs", "build", "dist", "__pycache__"}
RUNTIME_SEGMENTS = {"incoming", "transient", "locks", "lock", "tokens", "execution-state", "runtime"}
TEMP_EXTENSIONS = {".tmp", ".bak", ".swp", ".pyc", ".log"}
READY_CLASSIFICATIONS = {"production_knowledge", "governed_operations", "tooling"}
REVIEW_CLASSIFICATIONS = {"approved_research", "configuration", "draft_research", "unknown"}
EXCLUDED_CLASSIFICATIONS = {"generated_output", "runtime_artifact", "temporary_file", "private_or_secret"}
BROAD_OVERRIDE_WARNING_THRESHOLD = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_id(prefix: str, parts: list[str]) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _normalize_rel(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip("/")


def _split_path(path: str) -> list[str]:
    return [part.lower() for part in _normalize_rel(path).split("/") if part]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_manifest(paths: list[str]) -> str:
    return _sha256_text("\n".join(sorted(_normalize_rel(path) for path in paths)))


def _apply_override_decision(override: dict[str, Any], current_classification: str, fallback_action: str) -> tuple[str, str, str, str, str]:
    classification = str(override.get("classification", current_classification))
    if classification not in CLASSIFICATIONS:
        classification = current_classification
    action = str(override.get("action", fallback_action))
    if action not in ACTIONS:
        action = fallback_action
    pattern = str(override.get("pattern", ""))
    return classification, action, "high", f"Policy override matched `{pattern}`.", pattern


def _secret_rule_name(pattern: re.Pattern[str]) -> str:
    raw = pattern.pattern.lower()
    if "private key" in raw:
        return "private-key"
    if "api" in raw or "token" in raw or "secret" in raw:
        return "credential-field"
    if "sk-" in raw:
        return "openai-token-prefix"
    if "gh[" in raw:
        return "github-token-prefix"
    return "secret-pattern"


def _normalize_secret_identifier(value: str) -> str:
    return value.lower().replace("-", "_")


def _strip_secret_literal(value: str) -> str:
    cleaned = value.strip().rstrip(",)")
    if cleaned.startswith(("'", '"')) and cleaned.endswith(("'", '"')) and len(cleaned) >= 2:
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def is_secret_identifier(identifier: str) -> bool:
    return _normalize_secret_identifier(identifier) in SECRET_IDENTIFIERS


def is_placeholder_secret_value(value: str) -> bool:
    cleaned = _strip_secret_literal(value).lower()
    return cleaned in PLACEHOLDER_SECRET_VALUES or cleaned.startswith("your_") or cleaned.startswith("example_")


def _looks_like_real_secret_value(value: str) -> bool:
    cleaned = _strip_secret_literal(value)
    if is_placeholder_secret_value(cleaned):
        return False
    lowered = cleaned.lower()
    if lowered in {"true", "false"}:
        return False
    if cleaned.startswith(("os.", "Path(", "str(", "None", "TOKEN", "CLIENT_CONFIG")):
        return False
    if not cleaned:
        return False
    if re.search(r"\b(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{16,}|AIza[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{16})\b", cleaned):
        return True
    if value.strip().startswith(("'", '"')) and len(cleaned) >= 4:
        return True
    if len(cleaned) >= 12 and re.search(r"[A-Za-z]", cleaned) and re.search(r"\d", cleaned):
        return True
    if len(cleaned) >= 20:
        return True
    return False


def line_number_for_pattern(text: str, pattern: re.Pattern[str]) -> int:
    for index, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            return index
    return 0


@dataclass(frozen=True)
class SecretDetection:
    matched: bool
    blocked: bool
    category: str
    rule_id: str
    line_number: int
    identifier: str = ""
    value_kind: str = ""
    safe_reference: bool = False
    reason: str = ""
    redacted_evidence: str = ""

    def diagnostic_rule(self) -> str:
        suffix = f":line-{self.line_number}" if self.line_number else ""
        return f"{self.rule_id}{suffix}"


def _secret_detection_for_literal(line: str, line_number: int) -> SecretDetection | None:
    for rule_id, pattern in [
        ("secret-literal:environment-fallback", SECRET_ENV_FALLBACK_PATTERN),
        ("secret-literal:mapping-value", SECRET_MAPPING_VALUE_PATTERN),
        ("secret-literal:assignment", SECRET_ASSIGNMENT_PATTERN),
    ]:
        match = pattern.search(line)
        if not match:
            continue
        identifier = _normalize_secret_identifier(match.groupdict().get("identifier", "secret"))
        value = match.groupdict().get("value", "")
        if not is_secret_identifier(identifier) or not _looks_like_real_secret_value(value):
            return None
        return SecretDetection(
            matched=True,
            blocked=True,
            category="secret-like literal content",
            rule_id=rule_id,
            line_number=line_number,
            identifier=identifier,
            value_kind="literal",
            reason="Secret-like identifier is assigned a non-placeholder literal value.",
            redacted_evidence=f"{identifier}=<redacted>",
        )
    return None


def detect_secret_risk(text: str) -> list[SecretDetection]:
    detections: list[SecretDetection] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        literal = _secret_detection_for_literal(stripped, line_number)
        if literal:
            detections.append(literal)
            continue
        for rule_id, pattern in SAFE_SECRET_REFERENCE_PATTERNS:
            match = pattern.search(stripped)
            if match:
                identifier = _normalize_secret_identifier(match.group(1) if match.lastindex else "credential")
                detections.append(
                    SecretDetection(
                        matched=True,
                        blocked=False,
                        category="credential-field-reference",
                        rule_id=rule_id,
                        line_number=line_number,
                        identifier=identifier,
                        value_kind="reference",
                        safe_reference=True,
                        reason="Secret-like identifier appears as a reference without a literal secret value.",
                        redacted_evidence=f"{identifier}=<reference>",
                    )
                )
    for pattern in SECRET_CONTENT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        detections.append(
            SecretDetection(
                matched=True,
                blocked=True,
                category="secret-like literal content",
                rule_id=f"secret-content:{_secret_rule_name(pattern)}",
                line_number=line_number_for_pattern(text, pattern),
                value_kind="literal",
                reason="Known token prefix or private key material detected.",
                redacted_evidence="<redacted>",
            )
        )
    return detections


def major_subtree(relative_path: str) -> str:
    parts = _split_path(relative_path)
    if not parts:
        return "Other"
    if parts[0] == "03-operations" and len(parts) > 1:
        if parts[1] == "aoc":
            return "AOC"
        if parts[1] == "lodestar":
            return "Lodestar"
        return "Operations"
    if parts[0] in {"00-system", "01-system", "02-commands"}:
        return "System"
    if parts[0] in {"07-tools", "06-templates"}:
        return "Tooling"
    if parts[0] == "08-research":
        return "Research"
    if parts[0] == ".obsidian":
        return "Obsidian"
    return parts[0]


def _summary_by_subtree(changes: list["PkosFileChange"]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for change in changes:
        bucket = summary.setdefault(change.subtree, {"stage": 0, "review": 0, "exclude": 0, "block": 0})
        bucket[change.recommended_action] = bucket.get(change.recommended_action, 0) + 1
    return dict(sorted(summary.items()))


def _top_reasons(changes: list["PkosFileChange"], action: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for change in changes:
        if change.recommended_action == action:
            counts[change.reason] = counts.get(change.reason, 0) + 1
    return [{"reason": reason, "count": count} for reason, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]]


def _broad_override_warnings(changes: list["PkosFileChange"]) -> list[str]:
    counts: dict[str, int] = {}
    for change in changes:
        if change.recommended_action == "stage" and change.override_source:
            counts[change.override_source] = counts.get(change.override_source, 0) + 1
    warnings = []
    for pattern, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if count > BROAD_OVERRIDE_WARNING_THRESHOLD and _is_broad_pattern(pattern):
            warnings.append(f"Local override `{pattern}` selected {count} files. More-specific runtime exclusions should be configured.")
    return warnings


def _is_broad_pattern(pattern: str) -> bool:
    cleaned = _normalize_rel(pattern)
    return cleaned.endswith("/**") and cleaned.count("/") <= 2


def _run_git(repo: Path, args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise PkosSmartSyncError((result.stderr or result.stdout or "git command failed").strip())
    return result


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


@dataclass(frozen=True)
class PkosSyncPolicy:
    repository_path: Path
    lint_command: list[str] = field(default_factory=list)
    auto_stage_classifications: list[str] = field(default_factory=lambda: sorted(READY_CLASSIFICATIONS))
    review_classifications: list[str] = field(default_factory=lambda: sorted(REVIEW_CLASSIFICATIONS))
    excluded_classifications: list[str] = field(default_factory=lambda: sorted(EXCLUDED_CLASSIFICATIONS))
    require_confirmation: bool = True
    allow_commit: bool = True
    allow_push: bool = True
    push_requires_confirmation: bool = True
    remote: str = "origin"
    branch: str = "main"
    include_rules: list[str] = field(default_factory=list)
    exclude_rules: list[str] = field(default_factory=list)
    overrides: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def default(cls) -> "PkosSyncPolicy":
        return cls(
            repository_path=Path.home() / "OneDrive" / "Documents" / "Obsidian Vault",
            lint_command=["python", "07-tools/lint_wiki.py"],
        )

    @classmethod
    def load(cls, constellation_root: Path, config_path: Path | None = None) -> "PkosSyncPolicy":
        candidates: list[Path] = []
        if config_path:
            candidates.append(config_path if config_path.is_absolute() else constellation_root / config_path)
        candidates.extend(
            [
                constellation_root / "config" / "pkos-smart-sync.local.yaml",
                constellation_root / "config" / "pkos-smart-sync.example.yaml",
            ]
        )
        raw: dict[str, Any] | None = None
        for path in candidates:
            if path.exists():
                try:
                    raw = load_yaml(path)
                except YamlError as exc:
                    raise PkosSmartSyncError(f"Invalid Smart Sync policy: {path}: {exc}") from exc
                break
        if raw is None:
            return cls.default()
        data = raw.get("pkos_smart_sync", raw.get("\ufeffpkos_smart_sync", raw))
        if not isinstance(data, dict):
            raise PkosSmartSyncError("Smart Sync policy must be a mapping.")
        base = cls.default()
        repo_value = data.get("repository_path", str(base.repository_path))
        return cls(
            repository_path=Path(str(repo_value)),
            lint_command=_as_string_list(data.get("lint_command", base.lint_command)),
            auto_stage_classifications=_as_string_list(data.get("auto_stage_classifications", base.auto_stage_classifications)),
            review_classifications=_as_string_list(data.get("review_classifications", base.review_classifications)),
            excluded_classifications=_as_string_list(data.get("excluded_classifications", base.excluded_classifications)),
            require_confirmation=bool(data.get("require_confirmation", base.require_confirmation)),
            allow_commit=bool(data.get("allow_commit", base.allow_commit)),
            allow_push=bool(data.get("allow_push", base.allow_push)),
            push_requires_confirmation=bool(data.get("push_requires_confirmation", base.push_requires_confirmation)),
            remote=str(data.get("remote", base.remote)),
            branch=str(data.get("branch", base.branch)),
            include_rules=_as_string_list(data.get("include_rules", [])),
            exclude_rules=_as_string_list(data.get("exclude_rules", [])),
            overrides=[item for item in data.get("overrides", []) or [] if isinstance(item, dict)],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_path": str(self.repository_path),
            "lint_command": self.lint_command,
            "auto_stage_classifications": self.auto_stage_classifications,
            "review_classifications": self.review_classifications,
            "excluded_classifications": self.excluded_classifications,
            "require_confirmation": self.require_confirmation,
            "allow_commit": self.allow_commit,
            "allow_push": self.allow_push,
            "push_requires_confirmation": self.push_requires_confirmation,
            "remote": self.remote,
            "branch": self.branch,
            "include_rules": self.include_rules,
            "exclude_rules": self.exclude_rules,
            "overrides": self.overrides,
        }


@dataclass(frozen=True)
class PkosFileClassification:
    classification: str
    confidence: str
    rules: list[str]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PkosSyncDecision:
    relative_path: str
    recommended_action: str
    reason: str
    selected_for_staging: bool
    requires_manual_review: bool

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PkosFileChange:
    relative_path: str
    absolute_path: str
    git_status: str
    change_type: str
    file_extension: str
    size_bytes: int
    classification: str
    confidence: str
    classification_rules: list[str]
    recommended_action: str
    reason: str
    contains_secret_risk: bool
    contains_runtime_risk: bool
    contains_generated_content_risk: bool
    requires_manual_review: bool
    selected_for_staging: bool
    subtree: str = "Other"
    precedence: list[str] = field(default_factory=list)
    override_source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PkosSyncPreview:
    preview_id: str
    created_at: str
    repository_path: str
    branch: str
    remote: str
    remote_url_available: bool
    lint_result: dict[str, Any]
    safety_checks: dict[str, Any]
    changes: list[PkosFileChange]
    existing_staged_changes: list[str]
    proposed_commit_message: str
    ready_count: int
    review_count: int
    excluded_count: int
    blocked_count: int
    summary_by_subtree: dict[str, dict[str, int]]
    top_exclusion_reasons: list[dict[str, Any]]
    top_review_reasons: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        data["changes"] = [change.to_dict() for change in self.changes]
        return data


@dataclass(frozen=True)
class PkosSyncRun:
    run_id: str
    run_type: str
    status: str
    started_at: str
    completed_at: str
    preview_id: str | None
    staged_files: list[str]
    commit_hash: str | None
    pushed: bool
    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class PkosSyncStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.output_dir = root / "outputs" / "pkos-smart-sync"

    @property
    def latest_preview_path(self) -> Path:
        return self.output_dir / "latest-preview.json"

    @property
    def latest_run_path(self) -> Path:
        return self.output_dir / "latest-run.json"

    @property
    def approval_path(self) -> Path:
        return self.output_dir / "approval-record.json"

    def save_preview(self, preview: PkosSyncPreview) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        data = preview.to_dict()
        write_json(self.latest_preview_path, data)
        (self.output_dir / "latest-preview.md").write_text(render_preview_markdown(preview), encoding="utf-8")
        self._write_manifest("staged-manifest.json", [c for c in preview.changes if c.recommended_action == "stage"])
        self._write_manifest("review-manifest.json", [c for c in preview.changes if c.recommended_action == "review"])
        self._write_manifest("excluded-manifest.json", [c for c in preview.changes if c.recommended_action == "exclude"])
        self._write_manifest("blocked-manifest.json", [c for c in preview.changes if c.recommended_action == "block"])

    def load_preview(self) -> PkosSyncPreview:
        if not self.latest_preview_path.exists():
            raise PkosSmartSyncError("No Smart Sync preview exists. Run `pkos sync preview` first.")
        return preview_from_dict(read_json(self.latest_preview_path))

    def save_run(self, run: PkosSyncRun) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        data = run.to_dict()
        write_json(self.latest_run_path, data)
        history_path = self.output_dir / "smart-sync-history.json"
        history: list[dict[str, Any]] = []
        if history_path.exists():
            existing = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(existing, list):
                history = existing
        history.append(data)
        history.sort(key=lambda item: str(item.get("started_at", "")))
        history_path.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
        (self.output_dir / "smart-sync-report.md").write_text(render_run_markdown(run), encoding="utf-8")

    def save_approval(self, preview: PkosSyncPreview, *, commit_allowed: bool, push_allowed: bool) -> dict[str, Any]:
        approved_files = [change.relative_path for change in preview.changes if change.recommended_action == "stage"]
        record = {
            "preview_id": preview.preview_id,
            "approved_file_manifest_checksum": _hash_manifest(approved_files),
            "approved_files": sorted(approved_files),
            "approved_at": _now_iso(),
            "approved_by": "local_operator",
            "approved_categories": sorted({change.classification for change in preview.changes if change.recommended_action == "stage"}),
            "excluded_categories": sorted({change.classification for change in preview.changes if change.recommended_action != "stage"}),
            "commit_allowed": commit_allowed,
            "push_allowed": push_allowed,
        }
        write_json(self.approval_path, record)
        return record

    def load_approval(self) -> dict[str, Any]:
        if not self.approval_path.exists():
            raise PkosSmartSyncError("No Smart Sync approval record exists.")
        return read_json(self.approval_path)

    def load_history(self) -> list[dict[str, Any]]:
        path = self.output_dir / "smart-sync-history.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write_manifest(self, name: str, changes: list[PkosFileChange]) -> None:
        write_json(self.output_dir / name, {"files": [change.to_dict() for change in changes], "count": len(changes)})


class PkosSmartSyncEngine:
    def __init__(self, root: Path, policy: PkosSyncPolicy | None = None) -> None:
        self.root = root
        self.policy = policy or PkosSyncPolicy.load(root)
        self.store = PkosSyncStore(root)

    def status(self) -> dict[str, Any]:
        repo = self.policy.repository_path
        checks = self._repository_safety()
        return {
            "repository_path": str(repo),
            "repository_exists": repo.exists(),
            "is_git_repository": (repo / ".git").exists(),
            "branch": checks.get("branch", ""),
            "expected_branch": self.policy.branch,
            "remote": self.policy.remote,
            "remote_url_available": checks.get("remote_url_available", False),
            "has_conflicts": checks.get("has_conflicts", False),
            "has_preexisting_staged_changes": bool(checks.get("existing_staged_changes", [])),
            "health": "blocked" if checks.get("blocking_errors") else "ok",
            "errors": checks.get("blocking_errors", []),
            "warnings": checks.get("warnings", []),
        }

    def preview(self, *, export: bool = True) -> PkosSyncPreview:
        repo = self.policy.repository_path
        checks = self._repository_safety()
        lint = self._run_lint()
        changes = [self._classify_change(change) for change in self._git_changes()]
        changes.sort(key=lambda item: item.relative_path)
        warnings = list(checks.get("warnings", []))
        errors = list(checks.get("blocking_errors", []))
        if lint["status"] == "failed":
            errors.append("PKOS lint failed.")
        if any(change.contains_secret_risk for change in changes):
            errors.append("Secret-risk files detected.")
        warnings.extend(_broad_override_warnings(changes))
        preview = PkosSyncPreview(
            preview_id=_stable_id("pkos-preview", [str(repo), *[c.relative_path + c.git_status + c.classification + c.recommended_action for c in changes]]),
            created_at=_now_iso(),
            repository_path=str(repo),
            branch=str(checks.get("branch", "")),
            remote=self.policy.remote,
            remote_url_available=bool(checks.get("remote_url_available", False)),
            lint_result=lint,
            safety_checks=checks,
            changes=changes,
            existing_staged_changes=list(checks.get("existing_staged_changes", [])),
            proposed_commit_message=self._commit_message(changes),
            ready_count=sum(1 for item in changes if item.recommended_action == "stage"),
            review_count=sum(1 for item in changes if item.recommended_action == "review"),
            excluded_count=sum(1 for item in changes if item.recommended_action == "exclude"),
            blocked_count=sum(1 for item in changes if item.recommended_action == "block"),
            summary_by_subtree=_summary_by_subtree(changes),
            top_exclusion_reasons=_top_reasons(changes, "exclude"),
            top_review_reasons=_top_reasons(changes, "review"),
            warnings=warnings,
            errors=errors,
        )
        if export:
            self.store.save_preview(preview)
        return preview

    def stage(self, *, approved_only: bool = True) -> PkosSyncRun:
        preview = self.store.load_preview()
        self._ensure_stage_allowed(preview)
        approved = self.store.save_approval(preview, commit_allowed=True, push_allowed=self.policy.allow_push)
        approved_files = list(approved["approved_files"])
        started_at = _now_iso()
        errors: list[str] = []
        if approved_files:
            self._stage_paths(approved_files)
        staged = self._staged_paths()
        selected_staged = [path for path in staged if _normalize_rel(path) in set(approved_files)]
        run = PkosSyncRun(
            run_id=_stable_id("pkos-stage", [preview.preview_id, started_at]),
            run_type="stage",
            status="succeeded" if not errors else "failed",
            started_at=started_at,
            completed_at=_now_iso(),
            preview_id=preview.preview_id,
            staged_files=sorted(selected_staged),
            commit_hash=None,
            pushed=False,
            warnings=[],
            errors=errors,
        )
        self.store.save_run(run)
        return run

    def commit(self, *, message: str | None = None) -> PkosSyncRun:
        preview = self.store.load_preview()
        approval = self.store.load_approval()
        self._ensure_commit_allowed(preview, approval)
        staged = sorted(_normalize_rel(path) for path in self._staged_paths())
        approved = sorted(_normalize_rel(path) for path in approval.get("approved_files", []))
        if staged != approved:
            raise PkosSmartSyncError("Staged files differ from the approved Smart Sync preview.")
        started_at = _now_iso()
        if not staged:
            run = PkosSyncRun(_stable_id("pkos-commit", [preview.preview_id, started_at]), "commit", "no_changes", started_at, _now_iso(), preview.preview_id, [], None, False, ["No approved staged files to commit."], [])
            self.store.save_run(run)
            return run
        commit_message = message or preview.proposed_commit_message
        result = _run_git(self.policy.repository_path, ["commit", "-m", commit_message])
        if result.returncode != 0:
            raise PkosSmartSyncError((result.stderr or result.stdout or "git commit failed").strip())
        commit_hash = _run_git(self.policy.repository_path, ["rev-parse", "HEAD"], check=True).stdout.strip()
        run = PkosSyncRun(_stable_id("pkos-commit", [preview.preview_id, commit_hash]), "commit", "succeeded", started_at, _now_iso(), preview.preview_id, staged, commit_hash, False, [], [])
        self.store.save_run(run)
        return run

    def push(self) -> PkosSyncRun:
        latest = self._latest_run()
        if latest.get("run_type") != "commit" or latest.get("status") not in {"succeeded", "no_changes"}:
            raise PkosSmartSyncError("No Smart Sync commit is available to push.")
        checks = self._repository_safety()
        if checks.get("branch") != self.policy.branch:
            raise PkosSmartSyncError("Current branch does not match the approved Smart Sync branch.")
        started_at = _now_iso()
        if latest.get("status") == "no_changes":
            run = PkosSyncRun(_stable_id("pkos-push", [started_at, "no_changes"]), "push", "no_changes", started_at, _now_iso(), latest.get("preview_id"), [], None, False, ["No Smart Sync commit to push."], [])
            self.store.save_run(run)
            return run
        result = _run_git(self.policy.repository_path, ["push", self.policy.remote, self.policy.branch])
        if result.returncode != 0:
            raise PkosSmartSyncError((result.stderr or result.stdout or "git push failed").strip())
        run = PkosSyncRun(_stable_id("pkos-push", [str(latest.get("commit_hash")), started_at]), "push", "succeeded", started_at, _now_iso(), latest.get("preview_id"), [], str(latest.get("commit_hash")), True, [], [])
        self.store.save_run(run)
        return run

    def run(self, *, yes: bool = False, no_push: bool = False, commit_message: str | None = None) -> PkosSyncRun:
        preview = self.preview(export=True)
        if preview.blocked_count or preview.review_count:
            raise PkosSmartSyncError("Smart Sync run requires manual review before staging.")
        if not yes and self.policy.require_confirmation:
            raise PkosSmartSyncError("Smart Sync run requires explicit operator confirmation.")
        self.stage(approved_only=True)
        committed = self.commit(message=commit_message)
        if no_push or not self.policy.allow_push:
            return committed
        if not yes and self.policy.push_requires_confirmation:
            raise PkosSmartSyncError("Smart Sync push requires explicit operator confirmation.")
        return self.push()

    def show(self, run_id: str) -> dict[str, Any]:
        for run in self.store.load_history():
            if run.get("run_id") == run_id:
                return run
        raise PkosSmartSyncError(f"Smart Sync run not found: {run_id}")

    def _repository_safety(self) -> dict[str, Any]:
        repo = self.policy.repository_path
        warnings: list[str] = []
        errors: list[str] = []
        if not repo.exists():
            return {"blocking_errors": [f"Repository path does not exist: {repo}"], "warnings": [], "branch": "", "remote_url_available": False, "existing_staged_changes": []}
        if not (repo / ".git").exists():
            return {"blocking_errors": [f"Path is not a Git repository: {repo}"], "warnings": [], "branch": "", "remote_url_available": False, "existing_staged_changes": []}
        git_dir = repo / ".git"
        branch = _run_git(repo, ["branch", "--show-current"]).stdout.strip()
        if not branch:
            errors.append("Repository is in detached HEAD state.")
        elif branch != self.policy.branch:
            warnings.append(f"Current branch `{branch}` differs from configured branch `{self.policy.branch}`.")
        for marker in ["MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD"]:
            if (git_dir / marker).exists():
                errors.append(f"Repository has active {marker} state.")
        if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
            errors.append("Repository has an active rebase state.")
        status_lines = _run_git(repo, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout.splitlines()
        has_conflicts = any(_is_conflict_status(line[:2]) for line in status_lines if len(line) >= 2)
        if has_conflicts:
            errors.append("Repository has unresolved conflicts.")
        staged = [line[3:] for line in status_lines if len(line) >= 3 and line[:2] != "??" and line[0] != " "]
        if staged:
            warnings.append("Repository has pre-existing staged changes.")
        remote = _run_git(repo, ["remote", "get-url", self.policy.remote])
        remote_available = remote.returncode == 0
        if not remote_available:
            warnings.append(f"Configured remote `{self.policy.remote}` is unavailable.")
        return {
            "branch": branch,
            "expected_branch": self.policy.branch,
            "remote": self.policy.remote,
            "remote_url_available": remote_available,
            "has_conflicts": has_conflicts,
            "existing_staged_changes": sorted(staged),
            "warnings": warnings,
            "blocking_errors": errors,
        }

    def _run_lint(self) -> dict[str, Any]:
        if not self.policy.lint_command:
            return {"status": "skipped", "command": [], "returncode": 0, "summary": "No lint command configured."}
        result = subprocess.run(self.policy.lint_command, cwd=self.policy.repository_path, text=True, capture_output=True, encoding="utf-8", errors="replace")
        summary = (result.stdout or result.stderr or "").strip().splitlines()
        return {
            "status": "passed" if result.returncode == 0 else "failed",
            "command": self.policy.lint_command,
            "returncode": result.returncode,
            "summary": summary[-5:],
        }

    def _git_changes(self) -> list[dict[str, Any]]:
        lines = _run_git(self.policy.repository_path, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout.splitlines()
        changes: list[dict[str, Any]] = []
        for line in lines:
            if len(line) < 4:
                continue
            status = line[:2]
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changes.append({"status": status, "path": _normalize_rel(path)})
        return changes

    def _classify_change(self, change: dict[str, Any]) -> PkosFileChange:
        rel = change["path"]
        abs_path = self.policy.repository_path / rel
        status = change["status"]
        size = abs_path.stat().st_size if abs_path.exists() and abs_path.is_file() else 0
        secret_detections = self._secret_detections(rel, abs_path)
        blocked_secret_rules = [detection.diagnostic_rule() for detection in secret_detections if detection.blocked]
        safe_secret_rules = [detection.diagnostic_rule() for detection in secret_detections if detection.safe_reference]
        precedence = ["1 secret block", "2 conflict block", "3 explicit exclude override", "4 runtime/generated exclusion", "5 temporary/private exclusion", "6 explicit review override", "7 approved staging rule", "8 unknown review"]
        classification, confidence, rules, reason = classify_path(rel)
        rules.extend(safe_secret_rules)
        runtime_risk = classification == "runtime_artifact"
        generated_risk = classification == "generated_output"
        override_source = ""
        exclude_override = self._matching_override(rel, action="exclude")
        decision_override = self._matching_override(rel, actions={"review", "stage"})
        if blocked_secret_rules:
            classification = "private_or_secret"
            action = "block"
            confidence = "high"
            rules.extend(blocked_secret_rules)
            reason = "Secret-risk path or content detected."
        elif _is_deletion(status):
            action = "review"
            rules.append("deleted-file-review")
            reason = "Deleted files require manual review before staging."
        elif exclude_override:
            classification, action, confidence, reason, override_source = _apply_override_decision(exclude_override, classification, "exclude")
            rules.append(f"override:{override_source}")
        elif classification in {"runtime_artifact", "generated_output", "temporary_file", "private_or_secret"}:
            action = "exclude" if classification != "private_or_secret" else "block"
        elif decision_override:
            classification, action, confidence, reason, override_source = _apply_override_decision(decision_override, classification, str(decision_override.get("action", "review")))
            rules.append(f"override:{override_source}")
        elif classification in self.policy.auto_stage_classifications:
            action = "stage"
        elif classification in self.policy.review_classifications:
            action = "review"
        elif classification in self.policy.excluded_classifications:
            action = "exclude"
        else:
            action = "review"
        return PkosFileChange(
            relative_path=rel,
            absolute_path=str(abs_path),
            git_status=status,
            change_type=change_type(status),
            file_extension=abs_path.suffix.lower(),
            size_bytes=size,
            classification=classification,
            confidence=confidence,
            classification_rules=sorted(set(rules)),
            recommended_action=action,
            reason=reason,
            contains_secret_risk=bool(blocked_secret_rules),
            contains_runtime_risk=runtime_risk,
            contains_generated_content_risk=generated_risk,
            requires_manual_review=action == "review",
            selected_for_staging=action == "stage",
            subtree=major_subtree(rel),
            precedence=precedence,
            override_source=override_source,
        )

    def _secret_detections(self, rel: str, abs_path: Path) -> list[SecretDetection]:
        lower = rel.lower()
        detections = [
            SecretDetection(
                matched=True,
                blocked=True,
                category="secret-path risk",
                rule_id=f"secret-path:{pattern}",
                line_number=0,
                value_kind="path",
                reason="Path matches a configured secret-risk pattern.",
                redacted_evidence="<path>",
            )
            for pattern in SECRET_PATH_PATTERNS
            if fnmatch.fnmatch(lower, pattern)
        ]
        if abs_path.exists() and abs_path.is_file() and abs_path.stat().st_size <= 1_000_000:
            try:
                text = abs_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
            detections.extend(detect_secret_risk(text))
        return detections

    def _matching_override(self, rel: str, *, action: str | None = None, actions: set[str] | None = None) -> dict[str, Any] | None:
        normalized = _normalize_rel(rel)
        matches: list[dict[str, Any]] = []
        for override in self.policy.overrides:
            pattern = str(override.get("pattern", ""))
            override_action = str(override.get("action", ""))
            if action is not None and override_action != action:
                continue
            if actions is not None and override_action not in actions:
                continue
            if pattern and fnmatch.fnmatch(normalized, _normalize_rel(pattern)):
                matches.append(override)
        if not matches:
            return None
        return sorted(matches, key=lambda item: (int(item.get("priority", 0) or 0), len(str(item.get("pattern", "")))), reverse=True)[0]

    def _commit_message(self, changes: list[PkosFileChange]) -> str:
        date = datetime.now().strftime("%Y-%m-%d")
        staged = [change for change in changes if change.recommended_action == "stage"]
        if not staged:
            return f"PKOS Smart Sync - {date}"
        categories = sorted({change.classification for change in staged})
        lines = [f"PKOS Smart Sync - {date}", ""]
        for category in categories:
            count = sum(1 for change in staged if change.classification == category)
            lines.append(f"* {category}: {count}")
        return "\n".join(lines)

    def _ensure_stage_allowed(self, preview: PkosSyncPreview) -> None:
        checks = self._repository_safety()
        if checks.get("blocking_errors"):
            raise PkosSmartSyncError("; ".join(checks["blocking_errors"]))
        if preview.lint_result.get("status") == "failed":
            raise PkosSmartSyncError("PKOS lint failed; staging refused.")
        if preview.existing_staged_changes:
            raise PkosSmartSyncError("Pre-existing staged changes require explicit operator review.")

    def _ensure_commit_allowed(self, preview: PkosSyncPreview, approval: dict[str, Any]) -> None:
        if not approval.get("commit_allowed"):
            raise PkosSmartSyncError("Approval record does not allow commit.")
        approved_files = [str(path) for path in approval.get("approved_files", [])]
        expected = _hash_manifest(approved_files)
        if approval.get("approved_file_manifest_checksum") != expected:
            raise PkosSmartSyncError("Approval record checksum is invalid.")

    def _stage_paths(self, paths: list[str]) -> None:
        existing: list[str] = []
        deleted: list[str] = []
        for rel in paths:
            if (self.policy.repository_path / rel).exists():
                existing.append(rel)
            else:
                deleted.append(rel)
        if existing:
            _run_git(self.policy.repository_path, ["add", "--", *existing], check=True)
        if deleted:
            _run_git(self.policy.repository_path, ["rm", "--cached", "--", *deleted], check=True)

    def _staged_paths(self) -> list[str]:
        lines = _run_git(self.policy.repository_path, ["diff", "--cached", "--name-only"]).stdout.splitlines()
        return [_normalize_rel(line) for line in lines if line.strip()]

    def _latest_run(self) -> dict[str, Any]:
        if not self.store.latest_run_path.exists():
            raise PkosSmartSyncError("No Smart Sync run exists.")
        return read_json(self.store.latest_run_path)


def classify_path(relative_path: str) -> tuple[str, str, list[str], str]:
    rel = _normalize_rel(relative_path)
    lower = rel.lower()
    parts = _split_path(rel)
    suffix = Path(rel).suffix.lower()
    name = parts[-1] if parts else ""
    if parts[:1] == [".obsidian"]:
        return "configuration", "high", ["obsidian-configuration"], "Obsidian configuration requires review."
    if len(parts) == 1 and re.match(r"^\d{4}-\d{2}-\d{2}\.md$", name):
        return "unknown", "medium", ["root-daily-note"], "Root daily notes require review."
    if suffix in TEMP_EXTENSIONS or any(part in {"tmp", "temp"} for part in parts):
        return "temporary_file", "high", ["temporary-file"], "Temporary files are excluded."
    if name.endswith(".lock"):
        return "runtime_artifact", "high", ["lock-file"], "Lock files are runtime artifacts."
    if any(part in GENERATED_SEGMENTS for part in parts):
        return "generated_output", "medium", ["generated-segment"], "Generated output is excluded by default."
    if any(part in RUNTIME_SEGMENTS for part in parts):
        return "runtime_artifact", "high", ["runtime-segment"], "Runtime artifacts are excluded."
    if parts[:5] == ["03-operations", "aoc", "07-automation", "intake", "approved"]:
        return "governed_operations", "medium", ["aoc-approved-intake"], "Approved AOC intake is governed operations."
    if _contains_sequence(parts, ["intake", "incoming"]) or _contains_sequence(parts, ["intake", "review"]):
        return "runtime_artifact", "high", ["intake-runtime-path"], "Intake incoming/review files are transient runtime artifacts."
    if _contains_sequence(parts, ["automation", "tmp"]) or _contains_sequence(parts, ["automation", "temp"]) or _contains_sequence(parts, ["automation", "cache"]) or _contains_sequence(parts, ["automation", "locks"]):
        return "runtime_artifact", "high", ["automation-runtime-path"], "Automation temp/cache/lock files are runtime artifacts."
    if name.endswith("-run.json"):
        return "runtime_artifact", "medium", ["operational-run-json"], "Operational run JSON is a runtime artifact."
    if name.startswith("latest-") and name.endswith("-scan.md"):
        return "runtime_artifact", "medium", ["transient-scan-status"], "Latest scan outputs are transient unless explicitly approved."
    if "draft" in lower or "experimental" in lower or "working" in lower or "proposed" in lower or "review-required" in lower:
        return "draft_research", "medium", ["draft-marker"], "Draft or review-required material needs review."
    if name == "morning executive brief.md":
        return "unknown", "medium", ["generated-morning-brief-review"], "Generated Morning Executive Brief requires review unless designated durable."
    if parts[:1] == ["00-system"] or parts[:1] == ["01-system"] or parts[:1] == ["02-commands"] or "governance" in parts or "registry" in lower or "procedure" in lower:
        return "production_knowledge", "high", ["production-knowledge-path"], "Governed system knowledge can be staged."
    if _is_aoc_stage_path(parts, name):
        return "governed_operations", "medium", ["governed-operations-path"], "Operational knowledge can be staged when safe."
    if _is_aoc_review_path(parts, name):
        return "unknown", "medium", ["aoc-review-path"], "AOC review/status material requires operator review."
    if parts[:3] == ["03-operations", "lodestar", "eoc"]:
        return "governed_operations", "medium", ["lodestar-eoc-path"], "Lodestar EOC records are governed operations."
    if parts[:4] == ["03-operations", "lodestar", "growth", "content-intelligence"]:
        return "unknown", "medium", ["lodestar-content-intelligence-review"], "Lodestar content-intelligence material requires review unless final/approved."
    if parts[:1] == ["06-templates"] or (parts[:1] == ["07-tools"] and suffix in {".ps1", ".py", ".md", ".json"}):
        return "tooling", "medium", ["tooling-path"], "Governed tooling can be staged when safe."
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "configuration", "low", ["configuration-extension"], "Configuration requires review unless overridden."
    if parts[:1] == ["08-research"]:
        return "draft_research", "medium", ["research-path"], "Research defaults to draft unless approved."
    return "unknown", "low", ["no-governed-rule"], "No governed staging rule matched."


def _contains_sequence(parts: list[str], sequence: list[str]) -> bool:
    size = len(sequence)
    return any(parts[index : index + size] == sequence for index in range(0, max(len(parts) - size + 1, 0)))


def _is_aoc_stage_path(parts: list[str], name: str) -> bool:
    if parts[:3] in (
        ["03-operations", "aoc", "00-system"],
        ["03-operations", "aoc", "01-dashboard"],
        ["03-operations", "aoc", "02-assignments"],
        ["03-operations", "aoc", "08-analytics"],
    ):
        return True
    if parts[:4] == ["03-operations", "aoc", "05-knowledge", "packs"]:
        return True
    if parts[:5] == ["03-operations", "aoc", "07-automation", "intake", "approved"]:
        return True
    return name in {
        "opportunity-index.md",
        "latest-opportunity-review.md",
        "appraisal-operations-context.md",
        "aoc-automation-notes.md",
        "latest-automation-status.md",
        "scheduler-config.example.json",
        "gmail-intake-config.example.json",
    }


def _is_aoc_review_path(parts: list[str], name: str) -> bool:
    if parts[:5] == ["03-operations", "aoc", "07-automation", "opportunities", "review"]:
        return True
    if "reconciliation" in name or "review" in name or name.startswith("latest-"):
        return parts[:3] == ["03-operations", "aoc", "07-automation"]
    return parts[:2] == ["03-operations", "aoc"]


def change_type(status: str) -> str:
    if status == "??":
        return "untracked"
    if "D" in status:
        return "deleted"
    if "R" in status:
        return "renamed"
    if "A" in status:
        return "added"
    if "M" in status:
        return "modified"
    return "changed"


def _is_deletion(status: str) -> bool:
    return "D" in status


def _is_conflict_status(status: str) -> bool:
    return status in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}


def preview_from_dict(data: dict[str, Any]) -> PkosSyncPreview:
    changes = [PkosFileChange(**item) for item in data.get("changes", [])]
    return PkosSyncPreview(
        preview_id=str(data.get("preview_id", "")),
        created_at=str(data.get("created_at", "")),
        repository_path=str(data.get("repository_path", "")),
        branch=str(data.get("branch", "")),
        remote=str(data.get("remote", "")),
        remote_url_available=bool(data.get("remote_url_available", False)),
        lint_result=dict(data.get("lint_result", {})),
        safety_checks=dict(data.get("safety_checks", {})),
        changes=changes,
        existing_staged_changes=[str(item) for item in data.get("existing_staged_changes", [])],
        proposed_commit_message=str(data.get("proposed_commit_message", "")),
        ready_count=int(data.get("ready_count", 0)),
        review_count=int(data.get("review_count", 0)),
        excluded_count=int(data.get("excluded_count", 0)),
        blocked_count=int(data.get("blocked_count", 0)),
        summary_by_subtree=dict(data.get("summary_by_subtree", {})),
        top_exclusion_reasons=list(data.get("top_exclusion_reasons", [])),
        top_review_reasons=list(data.get("top_review_reasons", [])),
        warnings=[str(item) for item in data.get("warnings", [])],
        errors=[str(item) for item in data.get("errors", [])],
    )


def render_preview_markdown(preview: PkosSyncPreview) -> str:
    def section(title: str, changes: list[PkosFileChange]) -> list[str]:
        lines = [f"## {title}", ""]
        if not changes:
            return lines + ["None.", ""]
        for change in changes:
            lines.append(f"- `{change.relative_path}` - {change.classification} / {change.recommended_action} ({change.reason})")
        return lines + [""]

    lines = [
        "# PKOS Smart Sync Preview",
        "",
        "## Executive Summary",
        "",
        f"- Production knowledge: {sum(1 for c in preview.changes if c.classification == 'production_knowledge')}",
        f"- Governed operations: {sum(1 for c in preview.changes if c.classification == 'governed_operations')}",
        f"- Approved research: {sum(1 for c in preview.changes if c.classification == 'approved_research')}",
        f"- Needs review: {preview.review_count}",
        f"- Excluded generated/runtime: {sum(1 for c in preview.changes if c.classification in {'generated_output', 'runtime_artifact'})}",
        f"- Blocked secret-risk files: {preview.blocked_count}",
        f"- Ready to stage: {preview.ready_count}",
        "",
        "## Summary By Major Subtree",
        "",
    ]
    if preview.summary_by_subtree:
        for subtree, counts in preview.summary_by_subtree.items():
            if isinstance(counts, dict):
                lines.append(f"- {subtree}: stage `{counts.get('stage', 0)}`, review `{counts.get('review', 0)}`, exclude `{counts.get('exclude', 0)}`, block `{counts.get('block', 0)}`")
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Top Review Reasons",
            "",
        ]
    )
    lines.extend([f"- {item.get('reason')}: `{item.get('count')}`" for item in preview.top_review_reasons] or ["None."])
    lines.extend(["", "## Top Exclusion Reasons", ""])
    lines.extend([f"- {item.get('reason')}: `{item.get('count')}`" for item in preview.top_exclusion_reasons] or ["None."])
    lines.extend(
        [
            "",
        "## Repository Status",
        "",
        f"- Repository: `{preview.repository_path}`",
        f"- Branch: `{preview.branch}`",
        f"- Remote: `{preview.remote}`",
        f"- Remote available: `{preview.remote_url_available}`",
        "",
        "## Lint Result",
        "",
        f"- Status: `{preview.lint_result.get('status', 'unknown')}`",
        "",
        ]
    )
    lines.extend(section("Files Recommended for Staging", [c for c in preview.changes if c.recommended_action == "stage"]))
    lines.extend(section("Files Requiring Review", [c for c in preview.changes if c.recommended_action == "review"]))
    lines.extend(section("Files Excluded", [c for c in preview.changes if c.recommended_action == "exclude"]))
    lines.extend(section("Blocked Files", [c for c in preview.changes if c.recommended_action == "block"]))
    lines.extend(["## Existing Staged Changes", ""])
    lines.extend([f"- `{path}`" for path in preview.existing_staged_changes] or ["None."])
    lines.extend(
        [
            "",
            "## Proposed Commit Message",
            "",
            "```text",
            preview.proposed_commit_message,
            "```",
            "",
            "## Proposed Push Target",
            "",
            f"- `{preview.remote}` / `{preview.branch}`",
            "",
            "## Safety Checks",
            "",
        ]
    )
    for warning in preview.warnings:
        lines.append(f"- Warning: {warning}")
    for error in preview.errors:
        lines.append(f"- Error: {error}")
    if not preview.warnings and not preview.errors:
        lines.append("- No safety warnings or errors.")
    lines.extend(["", "## Provenance", "", f"- Preview ID: `{preview.preview_id}`", f"- Created at: `{preview.created_at}`", ""])
    return "\n".join(lines)


def render_run_markdown(run: PkosSyncRun) -> str:
    lines = [
        "# PKOS Smart Sync Report",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Type: `{run.run_type}`",
        f"- Status: `{run.status}`",
        f"- Preview ID: `{run.preview_id or 'none'}`",
        f"- Commit hash: `{run.commit_hash or 'none'}`",
        f"- Pushed: `{run.pushed}`",
        "",
        "## Staged Files",
        "",
    ]
    lines.extend([f"- `{path}`" for path in run.staged_files] or ["None."])
    if run.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend([f"- {warning}" for warning in run.warnings])
    if run.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend([f"- {error}" for error in run.errors])
    lines.append("")
    return "\n".join(lines)
