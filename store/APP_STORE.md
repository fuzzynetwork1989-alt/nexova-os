# Apple App Store listing — Nexova OS

## App identity
- **Name:** Nexova OS
- **Bundle ID:** `com.synovanexus.nexova`
- **Category:** TODO (e.g. Productivity, Developer Tools)

## Subtitle (30 chars)
TODO

## Promotional text (170 chars, editable without review)
TODO

## Description
Nexova OS — The AI-Native Intelligence Layer. Next-gen multimodal agent OS with NOVA Stack, sovereign memory, agentic coding, and EU AI Act compliance. By Corey Smith / Synova Nexus Enterprise.

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
