# App Store Readiness Report

_Generated 2026-08-20T09:43:48+00:00Z by store_autopilot.py_

**Score: 13/16 applicable checks passed** (7 not applicable to this repo)

## Legal & Compliance

- [PASS] Privacy Policy document present
- [PASS] Terms of Service document present
- [MISSING] LICENSE file present
- [PASS] Data safety / privacy nutrition draft present
- [PASS] Content / age rating draft present

## Store Metadata

- [PASS] Apple App Store listing draft (name, subtitle, description, keywords)
- [PASS] Google Play listing draft (short/full description, category)
- [MISSING (critical)] App icon asset present
- [PASS] Screenshots folder / capture plan present
- [PASS] CHANGELOG for release notes

## Mobile Build Config

- [N/A] app.json has iOS bundleIdentifier + Android package
- [N/A] app.json declares version + versionCode/buildNumber
- [N/A] EAS build config (eas.json) present for Expo app
- [N/A] iOS privacy usage-description strings present where permissions are used

## Web Production Readiness

- [N/A] robots.txt present
- [N/A] sitemap present or generated
- [N/A] Security headers / CSP configured
- [PASS] Environment variable example file (.env.example) present, no real secrets committed

## CI/CD & Security

- [PASS] CI workflow present (.github/workflows)
- [PASS] Store-readiness autopilot workflow installed
- [PASS] SECURITY.md vulnerability-disclosure policy present
- [PASS] Dependency audit step configured in CI
- [MISSING] Crash / error monitoring reference present (Sentry or equivalent)

## Human-only steps (cannot be automated)

- Enroll in the Apple Developer Program ($99/yr) and Google Play Console ($25 one-time).
- Generate/rotate real signing certificates and provisioning profiles (or let EAS manage them).
- Capture real device/simulator screenshots and a preview video.
- Host the privacy policy at a public HTTPS URL and put that URL into both store listings.
- Fill in the actual Play Data Safety form and Apple Privacy Nutrition Labels in each console (drafts in legal/DATA_SAFETY.md).
- Complete the age rating questionnaire in each console (draft answers in legal/AGE_RATING.md).
- Click submit for review in App Store Connect / Play Console, and respond to any reviewer feedback.
- Have legal review the generated PRIVACY_POLICY.md / TERMS_OF_SERVICE.md before publishing.
