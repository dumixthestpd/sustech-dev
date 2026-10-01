---
title: E-hall language tutoring (CLE) — reservation wire and the rules it enforces
service: ehall
captured: 2026-10-01
---

# E-hall language tutoring (CLE / 语言中心语言指导)

One-to-one tutoring with 语言中心 staff, booked on e-hall: exam prep, writing
feedback, speaking practice, 出国文书 review. One reservation = **one
25-minute session**.

**Auth:** an e-hall session bootstrapped in a browser (`EhallSession`). A bare
CAS ticket answers **403** on the app's data endpoints — this is the one
e-hall app in our surface that cannot be read with TIS/CAS credentials alone.

## Wire

- The app serves **EMAP model endpoints** under `/dxggyw/sys/yyzxyy/`.
- **Booking posts the reservation model's entire control set.** The server
  rejects a subset with `#E2140600091` — do not send "just the changed fields".
- **Cancellation is a status write on the 我的预约 route**, not a DELETE.
- Field-level detail, with the captured request quoted in docstrings:
  `sustech_survival/ehall/cle/reservation/wire.py`.

## Rules the service enforces (from the published notice)

- **3 reservations per semester.** Walk-in slots do not count.
- **Book at least one day ahead**; same-day free slots are walk-ins only.
- **Cancel at least two days ahead** — inside that window the app refuses and
  points at `cle@sustech.edu.cn`.
- **Two un-cancelled no-shows stop booking for the rest of the semester.**
- **预约说明 is required** and carries the topic; written material is capped at
  500 字.
- **特别专项指导 (Thursday ≥10:00) is email-only** and cannot be booked through
  the app.

`cle policy` prints the published rules verbatim from the module's local
snapshot; the live notice and the reservation system win over the snapshot.

## Reads vs writes

Reads (no state change): `semester`, `service_types`, `teachers`,
`time_buckets`, `schedule`, `slots` (joined against live occupancy), `walkin`,
`my_reservations`, `quota`, `find_slot`, `find_reservation`.

Writes go through a **preview → apply** pair in both lanes:

```bash
sustech cle book preview   --slot <slot_id> --topic "IELTS writing feedback"
sustech cle book apply     --slot <slot_id> --topic "IELTS writing feedback" --commit --yes
sustech cle cancel preview --reservation <wid>
sustech cle cancel apply   --reservation <wid> --commit --yes
```

`apply` refuses if anything changed between preview and apply. `--slot` accepts
the first characters of a slot id printed by `cle slots`; an ambiguous prefix is
an error, not a guess. `cle mine` prints the reservation id that `cle cancel`
wants.

## Room fact

The room text comes from the **slot**, so read it rather than assuming
琳恩图书馆二楼203 — different services use different rooms.

## Status

Reads are verified against the live service. Writes remain guarded
(preview → explicit confirm → read-back), and were not fired against the live
service in the 2026-10-01 pass: a reservation consumes one of the three
per-semester slots, so it is a user-approved action, not a test fixture.
