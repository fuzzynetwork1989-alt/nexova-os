# App Store Readiness Autopilot Mode

This folder was added by an automated pass to move this app toward being
**App Store (iOS), Google Play, and production-web ready**.

## What it does automatically
- Audits the repo against a store-readiness checklist (legal docs, store
  metadata, mobile build config, web production hardening, CI/CD & security).
- Scaffolds every missing standard artifact it safely can:
  - `legal/PRIVACY_POLICY.md`, `legal/TERMS_OF_SERVICE.md`
  - `legal/DATA_SAFETY.md` (Play Data Safety / Apple Privacy Nutrition draft)
  - `legal/AGE_RATING.md` (age-rating questionnaire prep)
  - `store/APP_STORE.md`, `store/PLAY_STORE.md` listing drafts
  - `store/screenshots/` capture checklist
  - `eas.json` build profiles (for Expo/React Native apps)
  - `SECURITY.md`, `CHANGELOG.md`, `.env.example`
  - `.github/workflows/store-readiness.yml` — runs the audit + a dependency
    vulnerability scan on every push/PR and uploads the report as a CI artifact
- Never overwrites a file that already exists — it only fills gaps, so nothing
  you already wrote gets clobbered.
- Regenerates `STORE_READINESS_REPORT.md` and `store_readiness.json` every run
  so you always have an up-to-date pass/fail snapshot.

## Run it yourself
```bash
python autopilot/store_autopilot.py audit                 # report only, no writes
python autopilot/store_autopilot.py fix --app-name "..." --description "..." --bundle-id com.example.app
```

## What it can NEVER automate (human-only steps)
These require a real account, a real payment, or a human judgment call — no
script can do them for you:
1. Enroll in the **Apple Developer Program** ($99/yr) and register a
   **Google Play Console** account ($25 one-time).
2. Generate/rotate signing certificates & provisioning profiles (or let
   `eas build` manage them for you).
3. Capture real device/simulator **screenshots** and an optional preview video.
4. Host the privacy policy at a public HTTPS URL and paste that URL into both
   store listings.
5. Fill in the real **Play Data Safety** form and **Apple Privacy Nutrition
   Labels** using `legal/DATA_SAFETY.md` as your source of truth.
6. Complete the **age rating questionnaire** in each console using
   `legal/AGE_RATING.md` as prep notes.
7. Have **legal review** the generated privacy policy / terms before they go live.
8. Click **submit for review** and respond to reviewer feedback.

## Recommended flow
1. `python autopilot/store_autopilot.py fix` — scaffold everything possible.
2. Fill in every `TODO` in `legal/` and `store/`.
3. Open a PR, let `store-readiness.yml` run in CI, fix anything still `MISSING (critical)`.
4. Do the human-only steps above.
5. Ship it.
