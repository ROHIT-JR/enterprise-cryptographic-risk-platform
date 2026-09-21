# Demo Checklist and Contingency Plan

Companion to [`docs/demo-script.md`](demo-script.md). This file covers setup,
what to do if something goes wrong mid-demo, and recording a backup video.

## What's already built vs. what the team still has to do

This checklist and the pre-scanned fallback data are code — they ship with
the app. Three things in the original issue are **not** something an agent
can produce and are called out explicitly rather than silently skipped:

- **Recording the actual backup video.** Below is a recording script and
  the settings to use, but making the video requires a person driving a
  real browser with screen-recording software and their own voice.
- **Rehearsing the demo three times.** This is a team scheduling task.
- **Testing the recorded video plays back correctly** on the presentation
  laptop, in the actual room, on the actual projector/screen.

Everything else — the fallback data, the pre-demo checks, the contingency
switch — is implemented and tested (`tests/test_india_payments_contingency_scan.py`).

## Pre-demo setup checklist (run through this the morning of)

- [ ] `ECDAT_SEED_DEMO=true` is set on the environment the demo will run
      against, and the app has been restarted at least once since — this
      seeds SecureBank, the India Payments Platform organization/login, and
      the pre-scanned fallback project (see "Contingency plan" below)
- [ ] Confirm you can log in as `india-payments-admin` /
      `$ECDAT_DEMO_PASSWORD` (organization: `India Payments Platform`)
- [ ] Confirm `sample_enterprise/india-payments-platform.zip` exists and is
      current:
      ```bash
      cd sample_enterprise
      zip -r india-payments-platform.zip india-payments-platform
      ```
- [ ] Do one full dry-run upload + scan on the actual demo machine and
      network, not just your laptop — Wi-Fi at a venue is not your home
      Wi-Fi
- [ ] Confirm the "India Payments Platform (Pre-Scanned Fallback)" project
      is visible under Asset Explorer / Dashboard for that organization
      (this is the fallback — see below)
- [ ] Pre-generate one PDF report (executive summary or NQM compliance) and
      save it locally, in case live PDF generation is slow or the venue
      Wi-Fi is bad
- [ ] Take one full-page screenshot of every page in the flow (Dashboard,
      Upload Center mid-scan, Asset Explorer, Quantum Risk Dashboard,
      Migration Planner, PQC Benchmarks, NQM Compliance) — these become
      backup slides if the live app is unreachable at all
- [ ] Charge the laptop, disable OS notifications/updates, close Slack/email,
      set Do Not Disturb
- [ ] Confirm screen resolution matches what the projector expects before
      walking in — font sizes that look fine on a laptop can be unreadable
      from the back of a room

## Contingency plan: what to do if the live scan fails

The India Payments Platform organization is pre-seeded with **two**
projects:

1. **`India Payments Platform`** — empty until you upload
   `india-payments-platform.zip` live. This is what the 5-minute script
   walks through.
2. **`India Payments Platform (Pre-Scanned Fallback)`** — the exact same
   codebase, already scanned at application startup
   (`backend/app/seed.py::seed_india_payments_contingency_scan`). Same real
   pipeline, same real numbers — 54 assets, RSA-2048/ECDSA at 77/critical,
   the 3DES findings in IMPS/NEFT. Nothing about it is faked; it's a scan
   that already ran once so it doesn't have to run live.

**Decision rule during the demo:** if the upload hasn't finished within
~15 seconds of clicking "scan" (network hiccup, slow venue Wi-Fi), stop
narrating the wait and say: *"Let's look at a scan we already ran of the
same codebase"* — then navigate to the fallback project. The story doesn't
change, only whether the audience watches the scan happen live.

If the whole app is unreachable (server down, no network at all), fall back
to the screenshot deck from the pre-demo checklist, and use the recorded
video below if there's time to play it.

## Recording the backup video

An agent cannot record a screen video — this needs a person driving a real
browser and their own voice. Use this as the actual recording script.

**Setup**
- Recording tool: OBS Studio, QuickTime screen recording (macOS), or the
  Windows Game Bar (`Win+G`) all work; record at 1080p, 30fps minimum
- Close any app that could pop up a notification during the take
- Do a full pass of the 5-minute script from `docs/demo-script.md` once
  without recording first, so the narration timing feels natural
- Record in one take if possible — cutting between takes on a live-data UI
  (timestamps, relative dates) can visibly not match up

**Recording checklist**
- [ ] Record at 1080p or higher, 30fps minimum
- [ ] Use an external or headset microphone, not the laptop's built-in mic —
      room echo reads as unprofessional on a projector's speakers
- [ ] Follow the exact 5-minute timed script above; don't ad-lib new claims
      that aren't in the script (every number in it has been verified
      against a real scan — see the note near the top of `demo-script.md`)
- [ ] Keep total runtime under 5 minutes — trim in post if needed, but the
      live numbers/scan progress should not be sped up in a way that
      misrepresents how long the tool actually takes
- [ ] Export as MP4, H.264, under 200MB if it needs to go in an email or a
      slide deck
- [ ] Store the final file at `docs/demo-video/india-payments-demo.mp4`
      (create that directory) or upload to the team's shared drive and link
      it here once recorded — don't commit a large binary to git if it can
      be avoided; a `docs/demo-video/README.md` with the drive link is
      preferable to committing the MP4 itself
- [ ] **Play the exported file back on the actual presentation laptop**
      before the event — a video that plays fine on the machine that
      recorded it can still fail to play on a different machine (missing
      codec, wrong player)

## Rehearsal tracking

Track this manually — it's a team commitment, not something to check off
in code:

- [ ] Rehearsal 1 — date: __________ presenter: __________ time taken: ____
- [ ] Rehearsal 2 — date: __________ presenter: __________ time taken: ____
- [ ] Rehearsal 3 — date: __________ presenter: __________ time taken: ____

After each rehearsal, note anything that ran long, any question a mock
judge asked that the script didn't cover, and update `demo-script.md`
accordingly.
