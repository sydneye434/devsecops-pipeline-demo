# DevSecOps Pipeline Demo

This repository is a small Python Flask application plus a **GitLab CI/CD** pipeline that runs a full security-gated delivery path: static analysis, dependency and container scanning, secret detection, and dynamic testing before anything is treated as releasable. It exists to show how those controls chain together in one place, with realistic tooling choices and fail-fast behavior you can point auditors or new engineers at without wading through a proprietary monorepo.

The sample app is intentionally flawed in a few obvious ways (hardcoded secret, vulnerable dependency pin, SQL injection pattern) so scanners have something to find. Replace the demo weaknesses with real fixes in your own fork; keep the pipeline structure.

---

## Pipeline architecture

Stages run in order. Each row is one GitLab stage; the tool named is what implements that concern in `.gitlab-ci.yml`.

| Stage | What it does | Tool |
|--------|----------------|------|
| **build** | Create a virtualenv, install `requirements.txt`, run `compileall` so install and syntax issues fail early. | Python image + pip |
| **sast** | Scan first-party source for common bug classes (injection, unsafe patterns, etc.) without executing the app. | **Semgrep** (`p/security-audit`, `p/python`) |
| **sca** | Match manifests and lockfiles in the repo against a vulnerability database. | **Trivy** (`trivy fs`, vuln scanner) |
| **secrets** | Look for leaked or embedded credentials in the working tree. | **TruffleHog** (filesystem mode, verified findings) |
| **container-scan** | `docker build`, then scan the resulting image for OS and library CVEs. | **Docker** + **Trivy** (`trivy image`) |
| **dast** | Build the image, run the container, run **OWASP ZAP** baseline against the listening HTTP port (passive checks against a live target). | **ZAP** (`zap-baseline.py`) |
| **deploy** | Placeholder job that only runs after upstream jobs succeed; swap in your real deploy (Helm, Ansible, etc.). | Your orchestration (stub today) |

DAST is limited to **merge requests whose target branch is the project default branch** (e.g. `main`). That keeps the slow scan on the path to production without running it on every feature-branch push.

---

## What gets blocked and why

The pipeline is built around **non-zero exit codes** and **GitLab job failure**: if a gate fails, the pipeline fails, and you can require a green pipeline before merge. That mirrors how DoD and other government DevSecOps programs treat CI: each run produces **continuous compliance evidence** (logs, reports, artifacts), and releases are **audit-ready** only when the same automated gates have passed on the exact revision you ship.

Rough mapping:

- **Build** fails on dependency resolution errors or code that does not compile. No point running scanners on a broken tree.
- **Semgrep** uses `--error`: any finding the job is configured to report fails the job. Tighten or loosen with rule packs and severity flags if noise becomes a policy issue.
- **Trivy (SCA and image)** uses `TRIVY_SEVERITY=CRITICAL,HIGH` and `--exit-code 1`: CRITICAL/HIGH CVEs block. Medium and below do not, unless you change variables.
- **TruffleHog** runs with `--only-verified --fail`: only **verified** secret hits fail the job. Random demo strings may not verify; production pipelines often pair this with broader SAST secret rules or additional policies.
- **ZAP baseline** fails the job when the baseline script exits with a failure status (per ZAP’s rules and your config). Warnings vs failures can be tuned with ZAP configs and rule packs.

**Deploy** does not run on merge-request pipelines; it runs on the default branch (and tags) after merge, and only if required upstream jobs succeeded. The DAST job is listed as **optional** in `needs` so post-merge pipelines that do not include DAST (e.g. push to `main` after merge) can still deploy once the other gates pass.

---

## Setup and usage

### GitLab (intended path)

1. Create a project in GitLab and push this repository (or set up a **mirror** from GitHub if the canonical remote stays on GitHub).
2. Use a **GitLab Runner** that can run Docker jobs. The **container-scan** and **dast** jobs need **Docker-in-Docker** (`docker:dind` service) and a **privileged** executor (or an equivalent setup that provides Docker to the job).
3. Ensure the runner can pull: `python`, `semgrep`, `aquasec/trivy`, `trufflesecurity/trufflehog`, `docker`, `owasp/zap2docker-stable`, and the Trivy DB (outbound access to `ghcr.io` for the DB repositories configured in the YAML unless you mirror those internally).
4. Push a branch or open a merge request. For DAST against the default branch, open an MR **into** `main` (or whatever your **default branch** is named).

Optional: enable **merge request approvals** and **“Pipelines must succeed”** (or your org’s equivalent) so failed gates block merge.

### Local checks (developer machine)

You cannot run the full GitLab pipeline locally without reproducing Runner + DinD, but you can approximate pieces:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall -q .
python app.py   # or: gunicorn -b 0.0.0.0:8000 app:app
```

Docker build (requires Docker installed):

```bash
docker build -t devsecops-demo:local .
docker run --rm -p 8000:8000 devsecops-demo:local
```

Hit `http://localhost:8000/health` to confirm the app responds.

To dry-run individual scanners locally, install or run the same container images Semgrep, Trivy, TruffleHog, and ZAP use in `.gitlab-ci.yml` and invoke the same flags (see the `script` sections).

### GitHub-only note

This repo ships **`.gitlab-ci.yml`**, not GitHub Actions. If the repository lives on GitHub, run CI by connecting the project to GitLab (mirror or import) or by porting the stages to Actions yourself. The security stages and tools translate straightforwardly; only the orchestration YAML differs.

---

## License / safety

The bundled Flask app is for **demonstration and training** only. Do not deploy it to production or expose it to untrusted networks without removing the intentional vulnerabilities and hardening the stack.
