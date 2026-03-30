# Security scanning policy

This document describes how automated security scanning is applied in the **devsecops-pipeline-demo** repository. It defines what each tool is expected to find, when the CI pipeline fails as a result, and how engineers should triage and remediate findings. It applies to code, dependencies, container images, and runtime behavior exercised in CI.

## Scope and intent

The pipeline runs on merge requests and on pushes to protected lines of development (see `.gitlab-ci.yml`). Its purpose is to **block merges and releases** when agreed severity thresholds are exceeded, and to produce **audit-friendly evidence** (logs, reports, artifacts) for each run. This mirrors common government and regulated-industry practice: security controls are continuous, repeatable, and tied to a specific commit.

## Tools, coverage, and failure thresholds

| Control | Tool | What it evaluates | When the pipeline fails |
|--------|------|-------------------|-------------------------|
| Build integrity | Python toolchain (`pip`, `compileall`) | Dependency install succeeds; source compiles. | Any install error or compile failure. |
| SAST | Semgrep (`p/security-audit`, `p/python`) | First-party code patterns associated with vulnerabilities (e.g. injection, unsafe APIs, weak crypto usage). | **Any Semgrep finding** in the configured rulesets: the job runs with `--error` (non-zero exit on match). Severity is not filtered down to CRITICAL-only in the current pipeline; treat every reported match as merge-blocking unless handled under the false-positive process below. |
| SCA (dependencies) | Trivy (`trivy fs`) | Known CVEs in manifests and lockfiles present in the repository. | **CRITICAL or HIGH** CVEs (`TRIVY_SEVERITY=CRITICAL,HIGH`, exit code 1). MEDIUM and below do not fail this job as configured. |
| Secrets | TruffleHog (filesystem) | Credentials and similar material in the working tree. | **Verified** secret detections (`--only-verified --fail`). Unverified high-entropy strings may still warrant manual review but do not fail the job by default. |
| Container / image | Trivy (`trivy image` after `docker build`) | CVEs in the built image (OS packages and application libraries in layers). | **CRITICAL or HIGH** in the image, same severity gate as SCA. |
| DAST | OWASP ZAP baseline | Passive checks against a running instance (e.g. security headers, cookie flags, baseline policy). | Non-success exit from `zap-baseline.py` per ZAP’s baseline rules (typically “fail” class). Warnings-only behavior depends on ZAP configuration; the demo pipeline uses default strict failure semantics. |

**DAST** runs only on **merge requests targeting the default branch** (e.g. `main`), not on every branch push. Other stages run according to the workflow rules in `.gitlab-ci.yml`.

**Deploy** is gated on successful completion of the required upstream jobs; it does not run on merge-request pipelines in the demo configuration.

## Triage and remediation

1. **Confirm the finding**  
   Open the failing job log and any uploaded artifacts (e.g. ZAP JSON). Reproduce locally where practical using the same tool and major version as CI.

2. **Classify**  
   - **True positive**: Fix in code, dependency upgrades, configuration changes, or image rebuilds. Prefer eliminating the weakness over suppressing the scanner.  
   - **Accepted risk**: Rare; requires documented business justification, owner, and review date. For Trivy, use `.trivyignore` with CVE IDs and comments; for Semgrep/ZAP, use project-approved suppression mechanisms with inline justification.  
   - **False positive**: Tool or rule misfire, or environment-only noise. Document why it is false, link to vendor or rule issue if applicable, and use the contribution guidelines for suppressions.

3. **Remediate in order**  
   Address **secrets and authentication** first, then **injection and remote execution**, then **dependency and image CVEs**, then **defense-in-depth** (headers, cookies, hardening). Dependency fixes should prefer **patch upgrades** and verified lockfiles.

4. **Re-run CI**  
   Push an updated commit (or pipeline retry if your policy allows) only after the fix or approved suppression is in place. Do not merge on a red pipeline unless an emergency process explicitly overrides this policy.

## Roles and escalation

- **Change authors** are responsible for fixing or formally disputing findings on their branches.  
- **Security or platform maintainers** approve exceptions, rule-set changes, and long-lived suppressions.  
- **Severe or disputed issues** (e.g. suspected real credential leak, exploitable CVE in production path) should be escalated outside this document’s scope per your organization’s incident process.

## Contact

For security vulnerabilities in this **demo** repository, open an issue or follow your organization’s disclosure process. Do not use real production credentials or customer data in issues or reproductions.

This policy is descriptive of the current pipeline configuration. If `.gitlab-ci.yml` changes, update this document in the same change.
