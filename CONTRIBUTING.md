# Contributing

Thanks for helping improve this demo repository. The goal is to keep the pipeline realistic and easy to follow, not to grow a full application framework.

## Before you open a change

- **Read `SECURITY.md`** so you know how scans behave and what is merge-blocking.
- Keep changes **focused**: one logical change per merge request (or pull request, if you use GitHub with a mirror).
- Do not commit real secrets, production URLs, or customer data. Use obvious placeholders.

## Pipeline requirement

**All merge requests must pass the full security-gated CI pipeline before maintainers will review for merge.** In GitLab, that means the latest pipeline for your MR is green, including every job that applies to that MR (build, SAST, SCA, secrets, container scan, and DAST when your MR targets the default branch).

If CI is red, fix the underlying issue or work through the false-positive process below. Asking for review on a failing pipeline should be the exception (for example, when you need help interpreting a scanner message).

## Local sanity checks

Before pushing, at minimum:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m compileall -q .
```

If you change the container image, build it locally when you can:

```bash
docker build -t devsecops-demo:local .
```

## False positives in security scans

Scanners err. When you believe a finding is wrong or not actionable:

1. **Reproduce** with the same tool and similar flags as in `.gitlab-ci.yml`.  
2. **Document** in the MR description: tool name, rule or CVE ID, why you think it is a false positive, and what you propose (code change, suppression, rule tweak).  
3. **Prefer fixes over silence** when a small refactor removes the pattern without weakening behavior.  
4. **Suppressions** must be minimal and justified:
   - **Trivy**: `.trivyignore` entries with the CVE ID and a short comment; get maintainer agreement for anything long-lived.  
   - **Semgrep**: use the project’s agreed inline or config-level suppressions, never blanket `nosemgrep` without cause.  
   - **ZAP**: adjust baseline config or rule packs in-repo when the team agrees the finding is not applicable to this demo.  
   - **TruffleHog**: if verification misfires, coordinate with maintainers; do not commit strings that resemble real secrets to “prove” a point.

Maintainers may ask you to open an upstream issue (Semgrep, Trivy, etc.) and link it when the fault is clearly in the tool.

## What we are not looking for

- Drive-by dependency major upgrades unrelated to security or CI.  
- Changes that disable or bypass security jobs without a documented policy update in `SECURITY.md` and the pipeline YAML.  
- Marketing-style README edits unless they correct technical accuracy.

## Questions

Open an issue for pipeline behavior, policy wording, or demo scope. For tool-specific bugs, check the vendor’s issue tracker first.
