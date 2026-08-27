# Library Booking (IC — Information Commons) at `booking.lib.sustech.edu.cn`

> **Discovered 2026-06-29.** This is the IC (Information Commons) library
> booking system, used daily by students for **research rooms (讨论间)**,
> **meeting rooms (会议室)**, **training rooms (培训室)**,
> **recording studios (录音棚)**, **3D printing**, **book scanning**, and
> **video editing / filming systems**. **Distinct from**
> `booking.sustech.edu.cn` (ehall 书院活动场地) — different host, different
> auth flow, different booking surface.

**Module location:** `src/sustech_survival/lib/booking/` (under existing
`lib/` — not a separate top-level module, per the "categorize by how
humans reach the system" iron law #6: the URL prefix is `booking.lib.*`
but students reach it via the library nav menu).

## TL;DR

- **System type:** Vue 2 SPA + axios REST API at `/ic-web/`
- **Host:** `https://booking.lib.sustech.edu.cn`
- **API base:** `https://booking.lib.sustech.edu.cn/ic-web/`
- **Auth flow:** SUSTech CAS + **intermediate `/authcenter/` redirect** —
  NOT a direct CAS ticket exchange. The flow goes through an
  `authcenter/toLoginPage` → CAS → `authcenter/doAuth/<uuid>` → JWT-token
  `auth/token` → 302 to original page. The session cookie is `ic-cookie`
  (UUID). **No JSESSIONID dance, no Playwright needed.**
- **Auth-CAS flow differs from TIS/BB/ehall-booking**: there's a
  3-redirect chain (authcenter → CAS → authcenter → token page). The
  `ic-cookie` UUID is set on the final redirect to `/ic-web/auth/token`.
- **Default scope:** `classKind=1` = research spaces (讨论间 etc).
  Other classKinds (8=seats, 16=activities, 32=exam seats) live in
  different parts of the system. This module ships `classKind=1` first.

## Auth flow (verified end-to-end 2026-06-29)

The full chain is **6 hops**:

```
1. GET /ic-web/auth/address?finalAddress=...&errPageUrl=...&manager=false&consoleType=16
   → {"code":0,"data":"https://booking.lib.sustech.edu.cn/authcenter/toLoginPage?redirectUrl=.../ic-web//auth/token?uuid=<UUID1>&extInfo=<UUID1>"}

2. GET /authcenter/toLoginPage?redirectUrl=...&uuid=<UUID1>&extInfo=<UUID1>
   → 302 Location: https://cas.sustech.edu.cn/cas/login?service=https%3A%2F%2Fbooking.lib.sustech.edu.cn%2Fauthcenter%2FdoAuth%2F<UUID2>

3. GET CAS login page
   → execution token (5.7KB JWT-encoded)

4. POST CAS login (username, password, execution, _eventId=submit, submit="")
   → 302 Location: https://booking.lib.sustech.edu.cn/authcenter/doAuth/<UUID2>?ticket=ST-...

5. GET /authcenter/doAuth/<UUID2>?ticket=...
   → 302 Location: https://booking.lib.sustech.edu.cn/ic-web//auth/token?uuid=<UUID1>&uniToken=<JWT>
   (this hop does NOT set any cookies — pure relay)

6. GET /ic-web/auth/token?uuid=<UUID1>&uniToken=<JWT>
   → 302 to /ic/home
   → SET-COOKIE: ic-cookie=<UUID3>  ← THE SESSION COOKIE
   → also keeps TGC from CAS for SSO re-auth
```

**The session cookie is `ic-cookie=<UUID>`.** It is NOT `JSESSIONID`,
NOT `TGC`. It is set on the final hop and is the only required cookie
for API calls (TGC is for SSO re-auth and not needed for daily use).

**Discovery method:** bundled JS inspection
(`js/chunk-common_1721178291757.js` contains the Vuex store with
`disCaseAddress` and `disCaseUserInfo` actions; `js/chunk-a1fdd30a_1721178291757.js`
contains the reservation form payload).

**Auth references in SPA:**
- `disCaseAddress` — vuex action → calls `auth/address` GET
- `disCaseUserInfo` — vuex action → calls `auth/userInfo` GET, returns
  full user dict (accNo, pid, trueName, deptId, classId, manager, etc.)

## API endpoint catalog (verified 2026-06-29)

All endpoints are `GET` (or `POST` where noted) against
`https://booking.lib.sustech.edu.cn/ic-web/{path}`.

**Auth:**
- `GET  /auth/address` — `disCaseAddress`. Returns the authcenter URL.
- `GET  /auth/userInfo` — `disCaseUserInfo`. Returns the full user dict.
  `code:300` if not logged in. Used for `whoami()`.
- `GET  /auth/webapp` — `getAuthWebapp`. For 3rd-party webapp auth
  (uid+signkey URL params).
- `POST /login/user` — manual account login (uses RSA-encrypted password
  via `login/publicKey`). Not used by CAS SSO flow.
- `POST /login/signOut` — sign out.
- `GET  /login/publicKey` — RSA public key for password encryption.
- `POST /account/password` — change password.
- `POST /account/updatePss` — update password (alt endpoint).
- `GET  /account/getMembers` — get member list.
- `GET  /account/info` — account info.
- `GET  /account/update` — account update.

**Public/read (no auth needed for some):**
- `GET  /sysConfig/public` — public sys config (loginMode, captcha, etc.)
- `GET  /sysConfig` — full sys config (auth needed)
- `GET  /sysInfo` — sys info (params: probably a sysKey or id)
- `GET  /sysInfo/help` — help docs
- `GET  /codingTable/getAll` — coding tables (enums); needs unknown params
- `GET  /photomanager/banner` — homepage banner images
- `GET  /news/questions` — news/announcements
- `GET  /feedback/own` — own feedback
- `GET  /feedback/open` — open feedback
- `GET  /home/page/room/idle` — **homepage summary** (per-kind idle counts).
  Returns `[{name, idelQuantity, totalQuantity}, ...]` — 10 categories
  (video editing, video filming, 讨论间 3-7, 会议室, 培训室, 讨论间 1-3, 报告厅,
  文献扫描, 录音棚, 3D打印).
  - With `?kind=1&searchId=<labId>`: per-lab detail
- `GET  /lab/devKindLabs?classKind=1` — list of **labs (buildings/floors)**.
  Returns `[{labId, labName}, ...]`. For `classKind=1` returns 10 labs
  (琳恩一层, 涵泳二层, 一丹三层, 琳恩三层, 会议室, 培训室, 涵泳一层, 文献扫描,
  录音棚, 3D打印).
- `GET  /roomDevice/roomInfos?classKind=1&kindId=<k>&labId=<l>` — **full
  room inventory** for a (kind, lab) pair. Returns
  `[{campusId, campusName, labInfos: [{labId, labName, roomInfos: [{devId,
  devName, minResvTime, openTimes: [{openStartTime, openEndTime, openLimit}],
  resvInfos: null|...}]}]}]`.
- `GET  /devKind/labDevKinds` — kind list (params unknown)
- `GET  /devCoding/theme/details` — theme details
- `GET  /room/openTimes` — room open times (params unknown; needs classKind/kindId/labId/devId + date)
- `GET  /seatDevice/resvStatus?roomId=<id>` — `{available, used}` summary
- `GET  /seatDevice/coordinate` — seat coordinates
- `GET  /seatDevice/mcoordinate` — mobile seat coordinates
- `GET  /digitalReadingPcRoom/coordinate` — e-reading room
- `GET  /pad/GetCtrlRoomInfoS` — control room info (pad)
- `GET  /pad/picture` — pad pictures
- `GET  /psgSeat/open` — open seat info
- `GET  /psgSeat/resvInfo` — seat reservation info
- `GET  /seatRoom/open` — open seat room
- `GET  /seatRoom/openScope` — open scope
- `GET  `/device/tips` — device tips

**Reservation write (destructive):**
- `POST /reserve` — **create reservation** (verified payload below)
- `POST /reserve/delete` — **cancel reservation** (params: `params` field
  containing the resv ID)
- `POST /reserve/bulkAdd` — bulk add (group reservation)
- `POST /reserve/update` — update reservation
- `POST /reserve/entrance/save` — save entrance (entrance flow commit)
- `POST /reserve/endReserve` — end reservation early
- `POST /reserve/quickResv` — quick reservation
- `POST /seatDevice/tempLeave` — temporary leave (暂离)
- `POST `/seatOperation/tempLeave` — seat op temporary leave
- `POST /seatLockRec/unlock` — unlock seat
- `GET  /reserve/count` — reservation count (returns int)
- `GET  /reserve/operate/rec` — operate record (manager)
- `GET  /reserve/entrance` — entrance info
- `GET  /reserve/areaInfo` — area info (per-slot availability)
- `GET  /reserve/endList` — end list
- `GET  /reserve/time/expand` — time expansion
- `GET  /reserve/time/expand/duration` — time expansion duration
- `GET  /reserve/resvInfo` — reservation info (per reservation)
- `GET  /borrow/reserve/own` — **own reservations** (needs startDate+endDate+page+pageSize;
  error "请选择开始日期" if startDate missing)
- `GET  /borrow/device/resvDevInfo` — borrowed device resv info
- `GET  /checkLog/checkInfo` — check-in records
- `GET  /creditRec/getOwn` — credit records
- `GET  /creditStarRec/own` — credit-star records
- `GET  /creditConversionRec` — credit conversion records
- `GET  /creditPunishRec/surPlus` — punishment surplus
- `GET  /psgLeaveRec/leave` — request leave
- `GET  /psgLeaveRec/rec` — leave records
- `GET  /psgLeaveRec/cancel` — cancel leave
- `GET  /psgLeaveRec/reserves` — leaves for reservations
- `GET  /seatLockRec/ownLockRec` — own lock records
- `POST /resvMember/operate` — member operations
- `POST /activity/custom/delete` — delete custom activity
- `GET  /activity/custom/resvInfo` — custom activity resv info
- `GET  /activity/resvInfo` — activity resv info
- `GET  /activityReview` — activity review list
- `POST /activityReview/saveOrUpdate` — activity review save

**Captcha (login page):**
- `POST /captcha/get` — get captcha (slide or click-word)
- `POST /captcha/check` — check captcha (AES-encrypted pointJson, key=`XwKsGlMcdPMEhR1B`)
  - Used by `loginMode=1` (account password) flow. The CAS flow skips this.

## `whoami()` user data shape (verified)

```json
{
  "uuid": "8c253ced4ec0490ea17f37db9c0ae5d0",
  "accNo": 76727,                 // SUSTech account number
  "pid": "<sid>",                  // SUSTech personal ID
  "logonName": "<sid>",
  "cardNo": "EED73C02",           // card number
  "cardId": "-287884286",         // card internal ID
  "idCard": "43010320061024301X", // national ID (sensitive!)
  "trueName": "<name>",
  "kind": 1,
  "ident": 257,                   // identity bitmask
  "status": 1, "localstatus": 1,
  "classId": 369, "className": "2024级本科",
  "subsidy": 0, "sex": 1,
  "handPhone": "", "email": "",
  "deptId": 2, "deptName": "南方科技大学",
  "birthday": 0, "balance": 2147483647,
  "freeTime": 0, "useQuota": null,
  "roleId": null, "roleLevel": null,
  "manager": 1,                   // bitmask
  "permsSet": [],
  "token": "29ee439de7c745fda709c50ccf08a384",
  "property": 0, "expiredDate": 0
}
```

**Sensitive fields** (treat as credentials): `idCard`, `cardNo`, `cardId`,
`handPhone`, `email`. Don't log these.

## Room data shape (verified — `roomDevice/roomInfos`)

```json
{
  "campusId": 1,
  "campusName": "涵泳讨论间(Learning Nexus Group Study Rooms)",
  "labInfos": [
    {
      "labId": 4,
      "labName": "涵泳一层(Learning Nexus 1st floor)",
      "roomInfos": [
        {
          "devId": 13,
          "devName": "C105（1-3人）",
          "minResvTime": 10,                // minutes
          "openTimes": [
            {"openStartTime": "08:00", "openEndTime": "21:59", "openLimit": 1}
          ],
          "resvInfos": null                // null when free; populated when reserved
        },
        {
          "devId": 14,
          "devName": "C106（1-3人）",
          "minResvTime": 10,
          "openTimes": [{"openStartTime": "08:00", "openEndTime": "21:59", "openLimit": 1}],
          "resvInfos": null
        }
      ]
    },
    {
      "labId": 5,
      "labName": "涵泳二层(Learning Nexus 2rd floor)",
      "roomInfos": [
        {"devId": 15, "devName": "C201（3-6人）", "minResvTime": 10, "openTimes": [...], "resvInfos": null},
        {"devId": 16, "devName": "C202（3-6人）", "minResvTime": 10, "openTimes": [...], "resvInfos": null}
      ]
    }
  ]
}
```

Two id patterns:
- **`devId`** — small int (1, 2, ..., 16, 17, ...) for rooms
- **`labId`** — small int (1, 4, 5, 6, 7, 8, 11, 12, 15) for labs
- **`campusId`** — small int (1, 2, ...) for campuses

## Reservation create payload (verified 2026-06-29)

Extracted from `chunk-a1fdd30a_1721178291757.js:65859`:

```js
POST /ic-web/reserve
{
  "sysKind": 1,                       // classKind
  "appAccNo": 76727,                  // user.accNo (applicant)
  "memberKind": 1,                    // 1=self, 2=group
  "resvMember": [76727],              // [accNo, ...] — list of member accNos
  "resvBeginTime": "2026/07/01 08:00:00",  // "YYYY/MM/DD HH:mm:00" format
  "resvEndTime":   "2026/07/01 09:00:00",  // "YYYY/MM/DD HH:mm:00" format
  "testName": "my meeting",           // title
  "resvProperty": 0,                  // property (0=normal, etc.)
  "resvDev": [13],                    // [devId, ...] — list of room IDs
  "memo": ""                          // notes
}
```

**Gotchas:**
- Date format is `YYYY/MM/DD HH:mm:00` (slash, not dash; with seconds).
- `resvBeginTime` and `resvEndTime` are STRINGS, not timestamps.
- `resvDev` is an ARRAY (for multi-room booking).
- `resvMember` is an ARRAY of accNos (for group booking).
- The full payload goes as **query params** (`params:`) on the POST —
  the `axios` call is `method: "post", url: "reserve", params: t` per
  the bundled JS. **Not JSON body.**

## `home/page/room/idle` summary (verified)

```json
[
  {"name": "视频编辑剪辑系统", "idelQuantity": 2, "totalQuantity": 2},
  {"name": "视频拍摄灯光系统", "idelQuantity": 1, "totalQuantity": 1},
  {"name": "讨论间  Reserve Group Study Room (3-7 persons)", "idelQuantity": 13, "totalQuantity": 13},
  {"name": "会议室", "idelQuantity": 2, "totalQuantity": 2},
  {"name": "培训室", "idelQuantity": 2, "totalQuantity": 2},
  {"name": "讨论间  Reserve Group Study Room (1-3 persons)", "idelQuantity": 7, "totalQuantity": 11},
  {"name": "报告厅", "idelQuantity": 1, "totalQuantity": 1},
  {"name": "文献扫描 Book Scanning", "idelQuantity": 1, "totalQuantity": 1},
  {"name": "录音棚 Recording Studio", "idelQuantity": 1, "totalQuantity": 1},
  {"name": "3D打印 3D Printing", "idelQuantity": 1, "totalQuantity": 1}
]
```

10 categories. English name is in parens (e.g., "Reserve Group Study
Room (3-7 persons)"). `idelQuantity` = free count; `totalQuantity` = total.
Some kinds (1-3 person 讨论间) currently have 7 free / 11 total = 4 in use.

## Routing rules

| User asks about… | Route to |
|---|---|
| Library 讨论间 (group study rooms) | `sustech/lib/booking` (this module) |
| Library 会议室, 培训室, 报告厅, 录音棚, 3D打印, 文献扫描 | `sustech/lib/booking` (this module) |
| Library seats (座位) — quick seat, common seat | `sustech/lib/booking` (future, classKind=8) |
| Library grad-exam seats (考研座位) | `sustech/lib/booking` (future, classKind=32) |
| Library activities (活动) | `sustech/lib/booking` (future, classKind=16) |
| 书院活动场地 (35 venues on ehall booking) | `sustech/booking` (different module — `booking.sustech.edu.cn`) |
| 教学楼 classrooms (一教324 etc.) | `sustech/classroom` (TIS cdjy) |

## Gotchas discovered

1. **Auth flow is 3 redirects, not 1.** Going direct from
   `cas.sustech.edu.cn/cas/login?service=https://booking.lib.sustech.edu.cn/ic/home`
   returns an empty "error page" — the booking app's service URL MUST be
   `https://booking.lib.sustech.edu.cn/authcenter/doAuth/<uuid>`, not
   `/ic/home`. **Always start with `/ic-web/auth/address`** to get the
   proper authcenter URL.

2. **`ic-cookie` is the only session cookie needed.** TGC persists from
   CAS for SSO re-auth, but API calls only need `ic-cookie`. Don't
   try to manually set both.

3. **TGC has a long lifespan and can replay CAS.** Same sensitivity
   warning as elsewhere — don't log it.

4. **No "JSESSIONID" dance.** Unlike the ehall MAIN host
   (`ehall.sustech.edu.cn` — see `references/ehall-auth-2026-06-01.md`),
   the booking sub-app does NOT require a JSESSIONID. The `ic-cookie`
   is the whole session. **Don't import the ehall MAIN authorizer here.**

5. **Some endpoints have surprising required params.** e.g.,
   `/borrow/reserve/own` requires `startDate` (not `beginDate` or
   `fromDate`); `/reserve/areaInfo` requires `resvDate` (date string,
   not timestamp). When probing, read the Chinese error message:
   - "请选择开始日期" = needs `startDate`
   - "预约日期不能为空" = needs `resvDate`
   - "请求参数缺失" = generic; trial-and-error param shape

6. **Cancellation goes through `POST /reserve/delete` with the
   reservation ID in `params` (not in body and not in URL path).**
   Format: `params: { resvId: <id> }` (assumed — not yet verified).

7. **Date string format is `YYYY/MM/DD HH:mm:00`** (slash + 0-padded
   seconds). NOT ISO, NOT Unix timestamp. The form input is a `Date`
   object; the JS calls `moment(d).format("YYYY/MM/DD HH:mm:00")`
   before sending.

8. **API uses `params:` (query string) even for POST.** `axios` with
   `params: t` on a POST puts the payload in the URL query string,
   not the body. This is a 2024-era Java/Spring MVC convention that
   the SPA faithfully reproduces.

9. **Captcha key on the login page is `XwKsGlMcdPMEhR1B`** (AES-ECB,
   PKCS7). Only needed for `loginMode=1` (account password login) —
   the CAS SSO flow we use skips this entirely.

10. **`manager: 1` in whoami is a permission bit, not a role flag.**
    User with `manager: 1` is NOT necessarily a system administrator
    (it's part of the `ident`/`manager` bitmask used for feature
    toggles in the UI). Don't gate features on it.

## Module structure (target)

```
src/sustech_survival/lib/booking/
├── __init__.py          # Public API exports
├── auth.py              # LibBookingAuth (CAS + authcenter + token handshake)
├── client.py            # LibBookingClient (one class, all methods)
├── schema.py            # Dataclasses: Room, Lab, Campus, Reservation, ...
├── __main__.py          # CLI: whoami, rooms, my-reservations, reserve, cancel
└── tests/
    ├── test_schema.py       # offline parsing tests
    └── test_client.py       # mock-API tests (no live calls in CI)
```

Umbrella subskill at `~/.hermes/skills/sustech/lib/booking/SKILL.md` and
catalog entry above. The existing `sustech/lib/SKILL.md` umbrella gets
a "see also" pointer.

## Future work (not blocking initial ship)

- **classKind=8 (seats)** — quickSeat, commonSeat, seatPredetermine flows
- **classKind=16 (activities)** — activity posting/review
- **classKind=32 (grad-exam seats)** — exam seat predetermine
- **`/reserve/areaInfo` full per-slot availability** (for the "what slots
  are free in this room on this date" view)
- **`/room/openTimes`** for room-specific hours (right now only gets the
  generic `openTimes` from `roomInfos` data; per-day rules unknown)
- **Group reservation (memberKind=2)** — multi-user resv with the
  `resvMember` array populated
- **Captcha solver for `loginMode=1`** — needed if the user wants to
  use the local account password flow instead of CAS

## See also

- `sustech/booking` SKILL.md — the 35-room 书院活动 booking
  (different host, different module)
- `sustech/classroom` SKILL.md — 教学楼 classroom booking (TIS cdjy)
- `sustech-dev/SKILL.md` — endpoint catalog (catalog entry for IC)
- `references/ehall-auth-2026-06-01.md` — ehall MAIN host auth (DIFFERENT
  from this — JSESSIONID dance; this is the authcenter flow)
- `references/ehall-booking-venue-2026-06-15.md` — the ehall 35-venue
  booking module (DIFFERENT system — same Python module name pattern
  but separate host + auth)
