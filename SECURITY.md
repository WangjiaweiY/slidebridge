# Security Policy

SlideBridge Core is a research and algorithm debugging toolkit. It is not
clinical software and must not be used for clinical diagnosis.

## Reporting A Security Issue

If GitHub Security Advisories are available for this repository, please report
security issues there. If advisories are not available, open a minimal public
issue that describes the affected component without including sensitive data.

## Do Not Include Sensitive Materials

Please do not include:

- patient data or patient-identifiable metadata
- proprietary data or private documentation
- proprietary SDKs, runtime libraries, headers, or vendor binaries
- credentials, tokens, keys, or local machine secrets

Synthetic data and generated demo images are preferred for reproductions.

## Scope

Security reports should focus on the public Python package, CLI, local viewer,
file parsing behavior, and generated outputs. Reports involving private readers
or private packages should be handled by the owner of those packages.
