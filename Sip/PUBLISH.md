# Publishing Sip to the App Store

A step-by-step checklist. The project is fully wired — Swift sources, Info.plist,
entitlements, privacy manifest, asset catalog, 1024 px icon. You only need an
Apple Developer account and a Mac with Xcode.

---

## 0. What you need

- **Mac with Xcode 15.2 or newer** (App Store submissions require macOS).
- **Apple Developer Program** membership — $99/year, enrol at
  https://developer.apple.com/programs/enroll/
- **A free iCloud / Apple ID** (you already have one).
- **An iPhone for testing** (optional but recommended) — the Simulator does not
  have HealthKit and cannot deliver real local notifications.

---

## 1. Open the project

```bash
open Sip.xcodeproj
```

Xcode will index for a few seconds. You should see the `Sip` target with three
groups: **Models · Views · Services**.

## 2. Set your Team and bundle ID

This is the only manual edit you must do.

1. Click the blue **Sip** project icon at the top of the file navigator.
2. Select the **Sip** target → **Signing & Capabilities**.
3. **Team**: choose your Apple Developer team from the dropdown.
4. **Bundle Identifier**: change `com.example.sip` to something globally unique,
   e.g. `com.yourname.sip` or `com.yourcompany.sip`.
5. Make sure **Automatically manage signing** is checked. Xcode will create
   the signing certificate and provisioning profile for you.

The HealthKit capability is already declared in `Sip/Sip.entitlements`.
Xcode will register it against your bundle ID automatically.

## 3. Run it on the simulator

Pick **iPhone 15 Pro** in the run destination dropdown → press **⌘R**.
You should see the Today screen with the ring at 0 %, tap any quick-add
tile to log a drink. The undo toast slides up from the bottom.

> Note: HealthKit calls silently no-op in the simulator. Local notifications
> work, but on the device they only fire when the app is backgrounded.

## 4. Run it on your iPhone

1. Plug your iPhone in, trust the Mac.
2. Pick your device in the destination dropdown.
3. Press **⌘R**. The first launch will prompt:
   - "Sip would like to access Apple Health" → Allow All
   - "Sip would like to send you notifications" → Allow

## 5. Create the App Store Connect record

Go to https://appstoreconnect.apple.com → **My Apps → +**.

- **Platform**: iOS
- **Name**: Sip (or whatever — must be unique on the App Store)
- **Primary Language**: English (U.S.)
- **Bundle ID**: pick the one you set in step 2
- **SKU**: any internal identifier, e.g. `sip-001`
- **User Access**: Full Access

Fill the **App Information** section:
- **Category**: Health & Fitness (primary), Lifestyle (secondary)
- **Privacy Policy URL**: required. If you don't have one yet, generate a
  free one at https://app-privacy-policy-generator.firebaseapp.com/

Fill **App Privacy** (the nutrition label):
- Data types collected: **Health & Fitness** (linked to user via HealthKit)
- Used for: **App Functionality**
- Not used for tracking

Fill the **1.0 Prepare for Submission** page:
- **Description** (4000 char max) — see suggested copy in §9 below
- **Keywords** (100 char) — see §9
- **Support URL** — your website or a public email page
- **Marketing URL** — optional
- **Screenshots** — minimum required: 6.7" iPhone (1290 × 2796).
  Easiest path: run on the **iPhone 15 Pro Max** simulator, take screenshots
  with **⌘S**, drag the PNGs into App Store Connect.

## 6. Archive and upload

In Xcode:

1. Change the destination dropdown to **Any iOS Device (arm64)**.
2. Menu: **Product → Archive**. Build takes 1–3 min.
3. The Organizer window opens automatically.
4. Select the archive → **Distribute App** → **App Store Connect** → **Upload**.
5. Accept defaults (Include bitcode: off, Upload symbols: on, Manage signing: automatic).
6. Wait ~10–15 min — App Store Connect emails you when processing finishes.

## 7. Attach the build and submit

Back in App Store Connect → **App Store** tab → **1.0** version → **Build** section →
click **+** and pick the build you just uploaded.

Answer **Export Compliance**:
- *Does your app use encryption?* → **No** (we only use HTTPS / Apple frameworks,
  and `ITSAppUsesNonExemptEncryption = false` is already set in Info.plist).

Click **Save** → **Add for Review** → **Submit for Review**.

## 8. Review timeline

- **Processing** (Apple): a few minutes after upload.
- **Waiting for Review**: typically <24 hours.
- **In Review**: 1–4 hours.
- **Approved** → released automatically (or held for manual release if you
  picked that option).

If rejected, you get a message in App Store Connect with the exact guideline
that was violated and a tester's screen recording. Reply in Resolution Center
or fix and resubmit.

## 9. Suggested store metadata

**Subtitle (30 char):**
> Hydration made delightful.

**Promotional text (170 char):**
> One tap to log a sip. A ring that fills as you go. Reminders that don't nag.
> Syncs to Apple Health so your water counts everywhere.

**Description:**
```
Sip is the simplest way to drink more water.

— ONE-TAP LOGGING
Three quick sizes — glass, bottle, large — plus a custom amount for
coffee, tea, or anything else. Every tap is instantly reversible.

— A RING YOU'LL ACTUALLY WATCH
A live progress ring tells you exactly where you are versus your daily
goal. Watch it fill from morning to night.

— SMART REMINDERS
Three gentle nudges — morning kickstart, midday top-up, evening
wind-down. Toggle any of them on or off in one tap.

— APPLE HEALTH
Every drink is saved to the Health app as a Water sample, so your
hydration history follows you across devices and stays in sync with
the rest of your day.

— PRIVACY FIRST
Sip stores everything locally. No accounts, no servers, no tracking.
```

**Keywords (100 char, comma-sep):**
```
water,hydration,drink,reminder,tracker,health,wellness,daily,goal,habit
```

**What's New in This Version (for v1.0):**
```
The first release of Sip — log water in one tap, watch your ring fill,
and let gentle reminders keep your streak alive.
```

## 10. Optional polish before submission

- **App Store screenshot frames** — use https://www.fastlane.tools/ or
  https://shotbot.io/ to add device frames and captions.
- **Localizations** — duplicate the strings in `Sip/Views/*.swift` and add
  language entries in App Store Connect.
- **TestFlight beta** — invite friends before going live. From App Store
  Connect → TestFlight tab → add internal/external testers.
- **Subscription / IAP** — Sip is free. If you want to monetize, add a Pro
  tier (advanced charts, custom reminders) via In-App Purchase.

---

## Files in this project

```
Sip.xcodeproj/             — Xcode project file
Sip/
  SipApp.swift             — App entry point
  Info.plist               — Bundle metadata + HealthKit usage strings
  Sip.entitlements         — HealthKit capability
  PrivacyInfo.xcprivacy    — Required privacy manifest (UserDefaults reason)
  Assets.xcassets/         — App icon (1024 px) + AccentColor
  Models/
    DrinkEntry.swift       — Codable log entry
    HydrationStore.swift   — Observable store, persistence, streak/avg math
  Views/
    RootView.swift         — TabView container
    TodayView.swift        — Ring + quick add + sections
    ProgressRing.swift     — Reusable gradient ring
    QuickAddRow.swift      — 4 add tiles with haptic feedback
    WeekChart.swift        — Swift Charts bar chart
    RemindersList.swift    — Toggle rows wired to ReminderScheduler
    TrendsView.swift       — Weekly bars + averages
    HistoryView.swift      — Grouped log list
    SettingsView.swift     — Goal stepper + privacy + about
  Services/
    HealthKitManager.swift — Writes dietaryWater samples
    ReminderScheduler.swift— UNUserNotificationCenter wrapper
scripts/
  make_icon.py             — Regenerates the 1024 px icon (Pillow)
```
