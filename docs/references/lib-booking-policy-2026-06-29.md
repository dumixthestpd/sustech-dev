# Library IC Booking — User Policy (讨论间使用办法)

> **Verified on 2026-06-29.** Sourced from `GET /ic-web/sysInfo/help`
> with `params={sysType:16, sysKind:4, status:2, sysValue:""}`. The full
> policy text is the **only sysKind that returns text** (other
> sysKinds return banner images). The help page is at `/ic/userhelp`
> in the SPA; the policy corresponds to the "通用" tab (which the
> help page renders as `sysKind=4` due to the data setup).

**Service phone (per policy):** 0755-88010800
**Service hours:** Operating hours are per room `openTimes` (verified
per-room from `roomDevice/roomInfos` data; 08:00-21:59 typical,
some 08:00-23:59 for 一丹).

---

## 中文 — 南方科技大学图书馆讨论间使用办法

学校图书馆面向本校全体师生提供学习研究和学术研讨的独立讨论间，
所有讨论间采用自助式服务。为规范讨论间管理，特制定本办法。

### 1、预约及使用方式

**1.1** 读者可使用学校统一认证系统的用户名及密码通过以下三种方式预约：

1. 登录图书馆网站（http://lib.sustech.edu.cn/），点击首页下方"讨论间预约"。
2. 登录微信公众号，点击"资源"下的"讨论间预约"。
3. 通过讨论间门口PAD屏扫码预约。

**1.2** 读者可提前 **2天** 预约，每次最多可预约 **2小时**，
讨论间使用完毕后可再次预约。

**1.3** 根据房间大小不同：
- **1-3人讨论间** — 主预约人填写使用主题后即可预约（无需组员）
- **3人以上讨论间** — 主预约人填写使用主题后，**需在组成员中再添加2位及以上组员校园卡号**后方可预约

**1.4** 读者可提前 **10分钟** 到预约房间门口PAD屏上刷卡签到。
- 3人以上讨论间，**至少需3人刷卡**才算签到成功
- 否则虽然可以进入，但要记主预约人 **1次违规**
- 取消主预约人预约权限 **1周**

**1.5** 超过预约时间 **15分钟** 不到的，系统自动取消该时段预约权限，
并记主预约人 **1次违规**，取消主预约人预约权限 **1周**。

**1.6** 预约成功后如计划更改，请在预约开始时间 **10分钟之前** 登录
讨论间管理系统，点击"个人中心"取消预约。

### 2、使用要求

**2.1** 使用时需遵守国家法律及学校有关规章制度，不得从事学习、研究以外的活动。

**2.2** 爱护公物，不得移动、损坏室内设施、设备。

**2.3** 勿携带食物及饮料进入，保持室内清洁卫生。

**2.4** 按时离开，离开时带走个人随身物品，如有遗失由本人承担责任。
临时借阅的馆内图书放至讨论间外的书车上，并随手关门。

**2.5** 违反讨论间使用管理要求，停止使用讨论间 **1个月**。

本办法自公布之日起施行，解释权归图书馆。使用过程中如有问题，
请联系值班工作人员，服务咨询电话：**0755-88010800**。

---

## English — Regulation for Using Group Study Rooms of SUSTech Libraries

The group study rooms of SUSTech Libraries are available for faculty
and students of the university to study and discuss on a self-service
basis. This regulation is formulated to ensure proper use of group
study rooms.

### 1. Making a Reservation

**1.1** To reserve a group study room, applicants may use the same user
name and password as assigned by the university central authentication
system in one of the following three ways:

1. Log on to the library website (http://lib.sustech.edu.cn/), click
   on "Reserve Group Study Room" at the bottom of the homepage.
2. Scan the QR code on the iPAD outside the room.

**1.2** Reservation can be made **2 days in advance**. A room can be
reserved for **up to 2 hours** each time and can be reserved again
after use.

**1.3** For rooms for 1-3 persons, the main applicant can make a
reservation after stating the purpose of usage; for rooms for more
than three persons, the main applicant has to make a reservation
together with **two more co-applicants by providing their campus
card numbers**.

**1.4** Applicants may start using the reserved room **10 minutes
before** the reserved time slot by scanning campus card on the iPAD
outside the room. For the reserved room for more than 3 persons,
**at least three users are required to scan their campus cards**
for a qualified sign-in; otherwise although the room can be used,
the main applicant will be **blocked for making any reservation for
a week** due to violating the rules.

**1.5** If users do not show up more than **15 minutes** after the
reserved time, the reservation will be canceled automatically.
**An one-time rule violation is recorded on the main applicant who
will be blocked for making any reservation for a week.**

**1.6** Cancellation of reservation can be made **10 minutes before**
the reserved time slot. Please log on to the reservation system,
click on "Personal Information" to cancel the reservation.

### 2. User Instructions

**2.1** Group study rooms are to be used for learning and research
only. Users should comply with national laws as well as regulations
of the university.

**2.2** Take good care of public property. Do not move or damage the
furniture and equipment in the room.

**2.3** Keep the room clean. No food and drink is allowed in the room.

**2.4** Leave the room on time. Take away personal belongings. Users
shall be responsible for any loss of unattended personal belongings.
Library materials that are used temporarily without checking-out should
be placed on the book trolley outside the room. Close the door upon
leaving.

**2.5** In case of violation against rules, the application will be
**blocked for making any reservation for a week** (initial 1.4/1.5
violation) — escalating to **1 month** for misuse violations (2.5).

This regulation takes immediate effect upon its official announcement.
The library reserves the right for its implementation. For assistance,
please contact library staff on duty at: **0755-88010800**.

---

## Module implementation impact

These rules MUST be enforced in `sustech_survival.lib.booking`:

| Rule | Wire-level check | Module surface |
|---|---|---|
| 2 days advance max | `end_date - now <= 2 days` | `book()` validates `delta <= 2 days` |
| 2 hours max per booking | `end - begin <= 2h` | `book()` validates duration <= 2h |
| 1-3 person rooms: no group needed | always allow `member_kind=1` | `book()` warns if dev_name has "1-3人" and `member_kind=2` |
| 3+ person rooms: 2 co-applicants | `len(resv_member) >= 3` (incl. self) | `book()` validates count for 3+ rooms |
| 10 min cancellation deadline | `now < begin - 10min` | `cancel_reservation()` validates timing |
| 15 min no-show penalty | enforced by server | `cancel_reservation()` for "no longer needed" before the 15-min mark |
| 1-week ban on 1 violation | enforced by server | logged warning on `add_reservation` |

The server's per-room `resvRule` already encodes the room-specific
limits (minResvTime, maxResvTime, latestResvTime, earliestResvTime,
numberLimit) — the module should read these and enforce rather than
hard-coding. The global rules (2 days / 2 hours) are NOT in the
per-room data and must be enforced client-side per the policy.

The module's `dry_run=True` default (per iron law #7) gives the user
a chance to see what would be sent before committing — this is
especially important for booking where mis-booking incurs a
**1-week ban** (1.5/1.4/2.5 violations).

## See also

- `lib-booking-ic-2026-06-29.md` — full API reference
- `references/ehall-booking-venue-2026-06-15.md` — the ehall 35-venue
  module (DIFFERENT system — different policy)
- TIS cdjy module — 教学楼 classroom booking (DIFFERENT system)
