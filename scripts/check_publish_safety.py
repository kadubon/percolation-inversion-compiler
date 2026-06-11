"""Fail when publishable files contain local paths or obvious secret markers."""

from __future__ import annotations

import re
import subprocess  # nosec B404
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".git",
    "uv.lock",
}
PUBLISH_SUFFIXES = {
    ".cff",
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PATTERNS = [
    re.compile(r"C:\\Users\\", re.IGNORECASE),
    re.compile(r"/home/[^/\s]+"),
    re.compile(r"Desktop\\Downloads", re.IGNORECASE),
    re.compile(
        r"(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{8,}",
        re.IGNORECASE,
    ),
    re.compile(r"bearer\s+[A-Za-z0-9_./+=-]{16,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?" + r"PRIVATE" + r" KEY-----"),
]

REQUIRED_PROJECT_URLS = {
    "Homepage",
    "Repository",
    "Documentation",
    "Issues",
    "Changelog",
    "DOI",
    "Works",
}
REQUIRED_KEYWORDS = {
    "ai-agents",
    "agent-runtime",
    "evidence-routing",
    "verifier-routing",
    "residual-ledger",
    "sybil-resistance",
    "abstraction-liquidity",
    "ecpt",
    "sqot",
    "alt",
}
PYPI_PUBLISH_ACTION_SHA = "6733eb7d741f0b11ec6a39b58540dab7590f9b7d"
FORBIDDEN_PATH_PARTS = {
    ".venv",
    "cache",
    "data/raw",
    "data/private",
    "dist",
    "download",
    "downloads",
    "node_modules",
    "private",
    "secrets",
    "site-packages",
    "temp",
    "tmp",
    "vendor",
    "vendors",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".arrow",
    ".bin",
    ".bz2",
    ".ckpt",
    ".feather",
    ".gz",
    ".joblib",
    ".npy",
    ".npz",
    ".onnx",
    ".parquet",
    ".pkl",
    ".pickle",
    ".pt",
    ".pth",
    ".rar",
    ".safetensors",
    ".tar",
    ".tgz",
    ".whl",
    ".xz",
    ".zip",
}
FORBIDDEN_KEY_SUFFIXES = {".asc", ".cer", ".crt", ".key", ".p12", ".pem", ".pfx"}
PRIVATE_KEY_NAME = re.compile(r"(^|[/\\])(id_rsa|id_ed25519|.*private.*key)", re.IGNORECASE)


def publishable_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "check_publish_safety.py":
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in PUBLISH_SUFFIXES:
            files.append(path)
    return files


def candidate_repository_files() -> list[Path]:
    # Fixed command, no shell, no user input.
    result = subprocess.run(  # nosec
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return publishable_files()
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def _is_allowed_tex(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    parts = relative.parts
    return len(parts) >= 2 and (
        (parts[0] == "docs" and path.suffix == ".tex")
        or (parts[:2] == ("tests", "fixtures") and path.suffix == ".tex")
    )


def check_repository_paths() -> list[str]:
    failures: list[str] = []
    for path in candidate_repository_files():
        if not path.exists() or not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        relative_text = relative.as_posix()
        parts = set(relative.parts)
        suffixes = {suffix.lower() for suffix in path.suffixes}
        relative_lower = relative_text.lower()
        forbidden_parts = {
            marker
            for marker in FORBIDDEN_PATH_PARTS
            if marker in parts
            or relative_lower == marker
            or relative_lower.startswith(f"{marker}/")
            or f"/{marker}/" in relative_lower
        }
        if forbidden_parts:
            failures.append(f"{relative_text} uses forbidden publish path part")
        if suffixes & FORBIDDEN_SUFFIXES:
            failures.append(f"{relative_text} uses forbidden archive/model/data suffix")
        if suffixes & FORBIDDEN_KEY_SUFFIXES or PRIVATE_KEY_NAME.search(relative_text):
            failures.append(f"{relative_text} looks like credential or private key material")
        if path.suffix.lower() == ".pdf":
            failures.append(f"{relative_text} vendors a PDF file")
        if path.suffix.lower() == ".tex" and not _is_allowed_tex(path):
            failures.append(f"{relative_text} vendors TeX outside allowed docs/tests fixture paths")
    return failures


def check_pyproject_metadata() -> list[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data.get("project", {})
    failures: list[str] = []
    urls = project.get("urls", {})
    missing_urls = sorted(REQUIRED_PROJECT_URLS - set(urls))
    failures.extend(f"pyproject.toml missing project URL: {name}" for name in missing_urls)
    if urls.get("Repository") != "https://github.com/kadubon/percolation-inversion-compiler":
        failures.append("pyproject.toml Repository URL must point to the public GitHub repo")
    if urls.get("DOI") != "https://doi.org/10.5281/zenodo.20569166":
        failures.append("pyproject.toml DOI URL must point to the repository concept DOI")
    keywords = set(project.get("keywords", []))
    missing_keywords = sorted(REQUIRED_KEYWORDS - keywords)
    failures.extend(
        f"pyproject.toml missing PyPI keyword: {keyword}" for keyword in missing_keywords
    )
    dev_dependencies = set(project.get("optional-dependencies", {}).get("dev", []))
    if not any(item.startswith("twine>=") for item in dev_dependencies):
        failures.append("pyproject.toml dev dependencies must include twine for metadata checks")
    return failures


def check_pypi_workflow() -> list[str]:
    workflow = ROOT / ".github" / "workflows" / "pypi-publish.yml"
    if not workflow.exists():
        return ["missing .github/workflows/pypi-publish.yml"]
    text = workflow.read_text(encoding="utf-8")
    failures: list[str] = []
    forbidden = ["PYPI_API_TOKEN", "pypi_token", "password:", "username:"]
    for marker in forbidden:
        if marker.lower() in text.lower():
            failures.append(f"PyPI workflow must not use token/password field: {marker}")
    data = yaml.safe_load(text)
    jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
    publish = jobs.get("publish", {}) if isinstance(jobs, dict) else {}
    if publish.get("environment") != "pypi":
        failures.append("PyPI workflow publish job must use the pypi environment")
    permissions = publish.get("permissions", {})
    if permissions.get("id-token") != "write":
        failures.append("PyPI workflow must grant id-token: write for trusted publishing")
    steps = publish.get("steps", [])
    uses_values = [step.get("uses", "") for step in steps if isinstance(step, dict)]
    expected_action = f"pypa/gh-action-pypi-publish@{PYPI_PUBLISH_ACTION_SHA}"
    if expected_action not in uses_values:
        failures.append("PyPI workflow must use the SHA-pinned PyPI publish action")
    if not any(
        "twine check" in str(step.get("run", "")) for step in steps if isinstance(step, dict)
    ):
        failures.append("PyPI workflow must run twine check before publishing")
    return failures


def main() -> int:
    failures: list[str] = []
    if (ROOT / "llms.txt").exists():
        failures.append("llms.txt must not be committed for this repository")
    failures.extend(check_repository_paths())
    for path in publishable_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PATTERNS:
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)} matched {pattern.pattern}")
    failures.extend(check_pyproject_metadata())
    failures.extend(check_pypi_workflow())
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
