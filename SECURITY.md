# Security Policy

## Supported Versions

Security fixes target the latest released minor version. During pre-1.0
development, users should upgrade to the newest release before reporting an
issue unless the issue blocks upgrading.

## Reporting a Vulnerability

Report vulnerabilities privately to the maintainer before public disclosure.
Include:

- affected version or commit;
- command, input file, or API path used;
- expected and observed behavior;
- whether the issue exposes secrets, executes code, corrupts certificates, or
  silently promotes claim status.

Do not include live credentials, private keys, API tokens, or unpublished
research artifacts in reports. Use redacted examples or synthetic fixtures.

## Input and Artifact Safety

The package treats TeX, JSON, YAML, and Zenodo metadata as untrusted input.
Extractors parse text and metadata; they do not execute TeX, run shell commands,
or treat registry entries as mathematical evidence. A registry claim is only a
projection of an accepted checker/extractor judgment.

Canonical Zenodo validation checks DOI metadata and checksums. It does not
download or vendor paper PDFs or TeX sources into the repository.

## Secret Handling

The repository must not contain:

- `.env` files or credentials;
- private keys or certificates;
- user-local paths, home directories, or machine-specific downloads;
- generated caches, virtual environments, or build artifacts.

CI includes static checks for accidental local paths and common secret markers.

## Agent Integration Threat Model

AI agents using this package should treat all external observations and generated
frontier records as untrusted until checked. Agent-facing JSON outputs separate
declared status from derived status, preserve residual/proof obligations, and
avoid status promotion without explicit certificate obligations.

The package does not certify unobserved physical facts, unconditional ASI claims,
or arbitrary external simulator output. Those cases must remain explicit proof
obligations or diagnostic records.
