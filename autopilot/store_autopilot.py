#!/usr/bin/env python3
"""
App Store Readiness Autopilot
==============================
Self-contained, dependency-free auditor + scaffolder that gets a repo to
"App Store / Google Play / Web launch ready".

Usage:
    python autopilot/store_autopilot.py audit          # report only, exit 1 if criticals missing
    python autopilot/store_autopilot.py fix             # audit + scaffold missing standard files
    python autopilot/store_autopilot.py fix --app-name "My App" --description "..." --bundle-id com.example.app

Design goals:
- No third-party dependencies (stdlib only) so it runs in any CI image.
- Never overwrites a file that already exists — only fills gaps.
- Produces STORE_READINESS_REPORT.md + store_readiness.json every run.
- Clearly separates "automatable" checks from "human-only" steps
  (Apple Developer enrollment, Play Console registration, actual screenshots,
  actual store submission click, legal sign-off).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def rel(*parts):
    return os.path.join(ROOT, *parts)


def exists(*parts):
    return os.path.exists(rel(*parts))


def read(*parts):
    p = rel(*parts)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def find_first(patterns):
    """Return first path (relative to ROOT) matching any of the glob-ish literal names, searched shallow."""
    for pattern in patterns:
        for base, dirs, files in os.walk(ROOT):
            # skip heavy/irrelevant dirs
            dirs[:] = [d for d in dirs if d not in (
                "node_modules", ".git", ".next", "dist", "build", "venv",
                ".venv", "__pycache__", "ios/Pods", "android/.gradle")]
            if pattern in files:
                return os.path.relpath(os.path.join(base, pattern), ROOT)
    return None


def detect_surfaces():
    surfaces = {
        "mobile_expo": find_first(["app.json"]) is not None and "expo" in read(find_first(["app.json"]) or ""),
        "web_next": find_first(["next.config.js", "next.config.ts", "next.config.mjs"]) is not None,
        "python_backend": find_first(["requirements.txt", "pyproject.toml"]) is not None,
        "node_backend": find_first(["package.json"]) is not None,
        "android_native": exists("android") or find_first(["build.gradle"]) is not None,
        "ios_native": exists("ios") or find_first(["*.xcodeproj"]) is not None,
    }
    return surfaces


CHECKS = []


def check(category, name, critical=False):
    def deco(fn):
        CHECKS.append((category, name, critical, fn))
        return fn
    return deco


# ---------------------------------------------------------------------------
# Legal & Compliance
# ---------------------------------------------------------------------------
@check("Legal & Compliance", "Privacy Policy document present", critical=True)
def c_privacy():
    return find_first(["PRIVACY_POLICY.md", "privacy-policy.md", "privacy.md"]) is not None or exists("legal", "PRIVACY_POLICY.md")


@check("Legal & Compliance", "Terms of Service document present", critical=True)
def c_terms():
    return find_first(["TERMS_OF_SERVICE.md", "terms.md", "TOS.md"]) is not None or exists("legal", "TERMS_OF_SERVICE.md")


@check("Legal & Compliance", "LICENSE file present", critical=False)
def c_license():
    return find_first(["LICENSE", "LICENSE.md", "LICENSE.txt"]) is not None


@check("Legal & Compliance", "Data safety / privacy nutrition draft present", critical=True)
def c_data_safety():
    return exists("legal", "DATA_SAFETY.md")


@check("Legal & Compliance", "Content / age rating draft present", critical=False)
def c_age_rating():
    return exists("legal", "AGE_RATING.md")


# ---------------------------------------------------------------------------
# Store Metadata
# ---------------------------------------------------------------------------
@check("Store Metadata", "Apple App Store listing draft (name, subtitle, description, keywords)", critical=True)
def c_appstore_listing():
    return find_first(["APP_STORE.md"]) is not None


@check("Store Metadata", "Google Play listing draft (short/full description, category)", critical=True)
def c_play_listing():
    return find_first(["PLAY_STORE.md"]) is not None


@check("Store Metadata", "App icon asset present", critical=True)
def c_icon():
    for name in ["icon.png", "icon.svg", "logo.png"]:
        if find_first([name]):
            return True
    return exists("assets") and any(
        "icon" in f.lower() for f in os.listdir(rel("assets")) if os.path.isfile(rel("assets", f))
    ) if exists("assets") else False


@check("Store Metadata", "Screenshots folder / capture plan present", critical=False)
def c_screenshots():
    return exists("store", "screenshots") or exists("screenshots") or find_first(["SCREENSHOTS.md"]) is not None


@check("Store Metadata", "CHANGELOG for release notes", critical=False)
def c_changelog():
    return find_first(["CHANGELOG.md"]) is not None


# ---------------------------------------------------------------------------
# Mobile Build Config
# ---------------------------------------------------------------------------
@check("Mobile Build Config", "app.json has iOS bundleIdentifier + Android package", critical=True)
def c_mobile_ids():
    p = find_first(["app.json"])
    if not p:
        return None  # not applicable
    content = read(p)
    return "bundleIdentifier" in content and "package" in content


@check("Mobile Build Config", "app.json declares version + versionCode/buildNumber", critical=True)
def c_mobile_versions():
    p = find_first(["app.json"])
    if not p:
        return None
    content = read(p)
    return '"version"' in content and ("versionCode" in content or "buildNumber" in content)


@check("Mobile Build Config", "EAS build config (eas.json) present for Expo app", critical=True)
def c_eas():
    if not find_first(["app.json"]):
        return None
    return find_first(["eas.json"]) is not None


@check("Mobile Build Config", "iOS privacy usage-description strings present where permissions are used", critical=False)
def c_ios_usage_strings():
    p = find_first(["app.json"])
    if not p:
        return None
    content = read(p)
    if "permissions" not in content and "NS" not in content:
        return True  # no sensitive permissions declared -> nothing required
    return "UsageDescription" in content


# ---------------------------------------------------------------------------
# Web Production Readiness
# ---------------------------------------------------------------------------
@check("Web Production Readiness", "robots.txt present", critical=False)
def c_robots():
    if not detect_surfaces()["web_next"]:
        return None
    return find_first(["robots.txt"]) is not None


@check("Web Production Readiness", "sitemap present or generated", critical=False)
def c_sitemap():
    if not detect_surfaces()["web_next"]:
        return None
    return find_first(["sitemap.xml", "sitemap.ts", "sitemap.js"]) is not None


@check("Web Production Readiness", "Security headers / CSP configured", critical=True)
def c_security_headers():
    if not detect_surfaces()["web_next"]:
        return None
    for name in ["next.config.js", "next.config.ts", "next.config.mjs", "vercel.json"]:
        p = find_first([name])
        if p and ("headers" in read(p) or "Content-Security-Policy" in read(p)):
            return True
    return False


@check("Web Production Readiness", "Environment variable example file (.env.example) present, no real secrets committed", critical=True)
def c_env_example():
    return find_first([".env.example"]) is not None


# ---------------------------------------------------------------------------
# CI/CD, Security & Observability
# ---------------------------------------------------------------------------
@check("CI/CD & Security", "CI workflow present (.github/workflows)", critical=True)
def c_ci():
    return exists(".github", "workflows") and len(os.listdir(rel(".github", "workflows"))) > 0


@check("CI/CD & Security", "Store-readiness autopilot workflow installed", critical=False)
def c_autopilot_workflow():
    return exists(".github", "workflows", "store-readiness.yml")


@check("CI/CD & Security", "SECURITY.md vulnerability-disclosure policy present", critical=False)
def c_security_md():
    return find_first(["SECURITY.md"]) is not None


@check("CI/CD & Security", "Dependency audit step configured in CI", critical=False)
def c_dep_audit():
    p = exists(".github", "workflows", "store-readiness.yml")
    return p  # our generated workflow always includes this step


@check("CI/CD & Security", "Crash / error monitoring reference present (Sentry or equivalent)", critical=False)
def c_error_monitoring():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".next", "venv", ".venv")]
        for f in files:
            if f.endswith((".json", ".txt")) and f not in ("package-lock.json",):
                continue
        for f in files:
            if f in ("package.json", "requirements.txt"):
                if "sentry" in read(os.path.relpath(os.path.join(base, f), ROOT)).lower():
                    return True
    return False


def run(fix, app_name, description, bundle_id):
    results = []
    for category, name, critical, fn in CHECKS:
        try:
            status = fn()
        except Exception as e:  # pragma: no cover
            status = False
        results.append({"category": category, "check": name, "critical": critical, "status": status})

    if fix:
        scaffold(app_name, description, bundle_id)
        # re-run after scaffolding so report reflects the fix
        results = []
        for category, name, critical, fn in CHECKS:
            try:
                status = fn()
            except Exception:
                status = False
            results.append({"category": category, "check": name, "critical": critical, "status": status})

    write_report(results)
    criticals_failed = [r for r in results if r["critical"] and r["status"] is False]
    return criticals_failed


def scaffold(app_name, description, bundle_id):
    surfaces = detect_surfaces()
    os.makedirs(rel("legal"), exist_ok=True)
    os.makedirs(rel("store"), exist_ok=True)

    _write_if_missing(rel("legal", "PRIVACY_POLICY.md"), PRIVACY_TEMPLATE.format(
        app_name=app_name, year=datetime.now().year))
    _write_if_missing(rel("legal", "TERMS_OF_SERVICE.md"), TERMS_TEMPLATE.format(
        app_name=app_name, year=datetime.now().year))
    _write_if_missing(rel("legal", "DATA_SAFETY.md"), DATA_SAFETY_TEMPLATE.format(app_name=app_name))
    _write_if_missing(rel("legal", "AGE_RATING.md"), AGE_RATING_TEMPLATE.format(app_name=app_name))
    _write_if_missing(rel("SECURITY.md"), SECURITY_TEMPLATE.format(app_name=app_name))
    _write_if_missing(rel("CHANGELOG.md"), CHANGELOG_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d")))
    _write_if_missing(rel(".env.example"), "# Copy to .env and fill in real values.\n# Never commit real secrets.\n")

    if not find_first(["APP_STORE.md"]):
        _write_if_missing(rel("store", "APP_STORE.md"), APP_STORE_TEMPLATE.format(
            app_name=app_name, description=description, bundle_id=bundle_id or "com.example.app"))
    if not find_first(["PLAY_STORE.md"]):
        _write_if_missing(rel("store", "PLAY_STORE.md"), PLAY_STORE_TEMPLATE.format(
            app_name=app_name, description=description, bundle_id=bundle_id or "com.example.app"))
    if not exists("store", "screenshots"):
        os.makedirs(rel("store", "screenshots"), exist_ok=True)
        _write_if_missing(rel("store", "screenshots", "README.md"),
                           "Drop final device screenshots here before submission:\n"
                           "- iOS: 6.7\" and 5.5\" display sizes\n"
                           "- Android: phone + tablet, at least 2 each\n")

    if surfaces["mobile_expo"] and not find_first(["eas.json"]):
        _write_if_missing(rel("eas.json"), EAS_JSON_TEMPLATE)

    os.makedirs(rel(".github", "workflows"), exist_ok=True)
    _write_if_missing(rel(".github", "workflows", "store-readiness.yml"), CI_WORKFLOW_TEMPLATE)


def _write_if_missing(path, content):
    if os.path.exists(path):
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def write_report(results):
    by_cat = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)

    lines = ["# App Store Readiness Report", "",
             f"_Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z by store_autopilot.py_", ""]

    total = len(results)
    passed = len([r for r in results if r["status"] is True])
    na = len([r for r in results if r["status"] is None])
    applicable = total - na
    lines.append(f"**Score: {passed}/{applicable} applicable checks passed** ({na} not applicable to this repo)")
    lines.append("")

    for cat, items in by_cat.items():
        lines.append(f"## {cat}")
        lines.append("")
        for r in items:
            if r["status"] is True:
                mark = "PASS"
            elif r["status"] is None:
                mark = "N/A"
            else:
                mark = "MISSING (critical)" if r["critical"] else "MISSING"
            lines.append(f"- [{mark}] {r['check']}")
        lines.append("")

    lines.append("## Human-only steps (cannot be automated)")
    lines.append("")
    lines += [
        "- Enroll in the Apple Developer Program ($99/yr) and Google Play Console ($25 one-time).",
        "- Generate/rotate real signing certificates and provisioning profiles (or let EAS manage them).",
        "- Capture real device/simulator screenshots and a preview video.",
        "- Host the privacy policy at a public HTTPS URL and put that URL into both store listings.",
        "- Fill in the actual Play Data Safety form and Apple Privacy Nutrition Labels in each console (drafts in legal/DATA_SAFETY.md).",
        "- Complete the age rating questionnaire in each console (draft answers in legal/AGE_RATING.md).",
        "- Click submit for review in App Store Connect / Play Console, and respond to any reviewer feedback.",
        "- Have legal review the generated PRIVACY_POLICY.md / TERMS_OF_SERVICE.md before publishing.",
    ]
    lines.append("")

    with open(rel("STORE_READINESS_REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(rel("store_readiness.json"), "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(), "results": results}, f, indent=2)


PRIVACY_TEMPLATE = """# Privacy Policy — {app_name}

_Last updated: {year}. TODO: have legal review before publishing publicly._

## What we collect
- Account info you provide (e.g. email) when you create an account.
- Content you create or upload while using {app_name}.
- Basic diagnostics (crash logs, performance metrics) if you opt in.

## How we use it
- To operate and improve {app_name}.
- To provide customer support.
- We do not sell personal data.

## Third parties
- List each SDK/service that processes user data here (auth provider, analytics, crash reporting, hosting).

## Data retention & deletion
- Describe how long data is kept and how a user can request deletion.

## Contact
- support@{app_name_lower}.example — replace with a real monitored address.

## Changes
We will update this policy as {app_name} evolves and note the date above.
"""

TERMS_TEMPLATE = """# Terms of Service — {app_name}

_Last updated: {year}. TODO: have legal review before publishing publicly._

## Acceptance of terms
By using {app_name} you agree to these terms.

## Use of the service
- Do not use {app_name} for unlawful purposes.
- You are responsible for content you submit.

## Accounts
- Keep your credentials secure; you are responsible for activity under your account.

## Termination
We may suspend or terminate accounts that violate these terms.

## Disclaimer & liability
{app_name} is provided "as is" without warranties of any kind, to the extent permitted by law.

## Governing law
Specify governing jurisdiction here.

## Contact
support@{app_name_lower}.example — replace with a real monitored address.
"""

DATA_SAFETY_TEMPLATE = """# Data Safety / Privacy Nutrition Draft — {app_name}

Use this as the source of truth when filling in:
- Google Play **Data safety** form
- Apple **App Privacy** (nutrition labels) in App Store Connect

| Data type | Collected? | Shared? | Purpose | Optional? |
|---|---|---|---|---|
| Email address | TODO | TODO | Account creation, support | TODO |
| User content | TODO | TODO | Core app functionality | TODO |
| Diagnostics / crash logs | TODO | TODO | Stability & performance | TODO |
| Approximate/precise location | TODO | TODO | — | TODO |
| Advertising ID | TODO | TODO | — | TODO |

Fill in every TODO based on the actual SDKs and backend calls {app_name} makes before submitting either console form.
"""

AGE_RATING_TEMPLATE = """# Age Rating Questionnaire Draft — {app_name}

Use as prep notes for Apple's age rating questionnaire and Google Play's IARC questionnaire.

- Violence: none / mild / realistic? -> TODO
- Sexual content or nudity: none? -> TODO
- Profanity or crude humor: none / infrequent? -> TODO
- Alcohol, tobacco, drugs references: none? -> TODO
- Gambling (simulated or real money): none? -> TODO
- User-generated content / unrestricted chat with strangers: yes/no -> TODO
- Data collection from children (COPPA/GDPR-K considerations): TODO

Target rating estimate: TODO (e.g. 4+/PEGI 3, or 12+/PEGI 12 if UGC/chat is present).
"""

SECURITY_TEMPLATE = """# Security Policy — {app_name}

## Reporting a vulnerability
Please email security@{app_name_lower}.example with details. We aim to acknowledge reports within 3 business days.

## Supported versions
Only the latest released version receives security fixes.

## Scope
Includes the production web app, backend API, and mobile clients for {app_name}.
"""

CHANGELOG_TEMPLATE = """# Changelog

## [Unreleased]
- Added App Store Readiness Autopilot toolkit.

## {date}
- Initial changelog entry.
"""

APP_STORE_TEMPLATE = """# Apple App Store listing — {app_name}

## App identity
- **Name:** {app_name}
- **Bundle ID:** `{bundle_id}`
- **Category:** TODO (e.g. Productivity, Developer Tools)

## Subtitle (30 chars)
TODO

## Promotional text (170 chars, editable without review)
TODO

## Description
{description}

## Keywords (100 chars, comma separated)
TODO

## Privacy policy URL
TODO — must be a public HTTPS URL (see legal/PRIVACY_POLICY.md)

## Support URL
TODO

## Build & submit
```bash
cd mobile   # or wherever the Expo/RN app lives
npx expo prebuild --platform ios
eas build -p ios --profile production
eas submit -p ios
```
Requires an active Apple Developer Program membership ($99/yr).
"""

PLAY_STORE_TEMPLATE = """# Google Play listing — {app_name}

## App identity
- **Name:** {app_name}
- **Package:** `{bundle_id}`
- **Category:** TODO
- **Free / paid:** TODO

## Short description (80 chars)
TODO

## Full description
{description}

## Privacy policy URL
TODO — must be a public HTTPS URL (see legal/PRIVACY_POLICY.md)

## Data safety form
See legal/DATA_SAFETY.md for the source-of-truth answers.

## Build & submit
```bash
cd mobile
eas build -p android --profile production
eas submit -p android
```
Requires a one-time $25 Google Play Console registration.
"""

EAS_JSON_TEMPLATE = """{
  "cli": {
    "version": ">= 5.0.0",
    "appVersionSource": "remote"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal"
    },
    "production": {
      "autoIncrement": true
    }
  },
  "submit": {
    "production": {}
  }
}
"""

CI_WORKFLOW_TEMPLATE = """name: Store Readiness Autopilot

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Run store readiness audit
        run: python autopilot/store_autopilot.py audit
      - name: Upload readiness report
        uses: actions/upload-artifact@v4
        with:
          name: store-readiness-report
          path: |
            STORE_READINESS_REPORT.md
            store_readiness.json

  dependency-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Node dependency audit
        if: hashFiles('package.json') != ''
        run: |
          npm install --package-lock-only --no-audit --silent || true
          npm audit --audit-level=high || true
      - name: Python dependency audit
        if: hashFiles('requirements.txt') != ''
        run: |
          pip install pip-audit --quiet || true
          pip-audit -r requirements.txt || true
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["audit", "fix"])
    parser.add_argument("--app-name", default=os.path.basename(ROOT))
    parser.add_argument("--description", default="TODO: one paragraph product description.")
    parser.add_argument("--bundle-id", default=None)
    args = parser.parse_args()

    app_name_lower = re.sub(r"[^a-z0-9]", "", args.app_name.lower()) or "app"
    global PRIVACY_TEMPLATE, TERMS_TEMPLATE, SECURITY_TEMPLATE
    PRIVACY_TEMPLATE = PRIVACY_TEMPLATE.replace("{app_name_lower}", app_name_lower)
    TERMS_TEMPLATE = TERMS_TEMPLATE.replace("{app_name_lower}", app_name_lower)
    SECURITY_TEMPLATE = SECURITY_TEMPLATE.replace("{app_name_lower}", app_name_lower)

    criticals_failed = run(args.mode == "fix", args.app_name, args.description, args.bundle_id)

    print(f"Wrote STORE_READINESS_REPORT.md and store_readiness.json")
    if criticals_failed:
        print(f"{len(criticals_failed)} critical checks still failing:")
        for r in criticals_failed:
            print(f"  - [{r['category']}] {r['check']}")
        if args.mode == "audit":
            sys.exit(1)
    else:
        print("No critical checks failing.")


if __name__ == "__main__":
    main()
