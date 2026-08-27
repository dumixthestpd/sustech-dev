### Reservation create wire format (corrected 2026-06-30)

**Date format is `YYYY-MM-DD HH:mm:00` (dashes), NOT `YYYY/MM/DD` (slashes).**
The SPA uses `moment.format("YYYY-MM-DD HH:mm:00")` at line ~65860 of
`chunk-a1fdd30a_1721178291757.js` (`handleSubmit` function). Using
slashes causes the server to return "请求参数错误" (code=100).

**The payload is sent as JSON body (Content-Type: application/json), NOT
as query params.** The axios call `method:"post", url:"reserve", params:t`
in the Vue component was misleading — the server's Spring Boot controller
expects a JSON body with `@RequestBody`, not `@RequestParam` query params.
Verified live 2026-06-30 by comparing:
- Query params → code=100 "请求参数错误"
- JSON body → code=1 "请在07:00后开始预约" (then code=0 on valid times)

**The complete create payload from the SPA (`handleSubmit` at offset ~65804):**

```json
{
  "sysKind": this.reserveInfo.classKind,     // int, e.g. 1
  "appAccNo": this.userInfo.accNo,           // int, e.g. 76727
  "memberKind": 1,                           // int: 1=self, 2=group
  "resvMember": [this.userInfo.accNo],       // array of int accNos
  "resvBeginTime": "YYYY-MM-DD HH:mm:00",    // string with dashes
  "resvEndTime": "YYYY-MM-DD HH:mm:00",      // string with dashes
  "testName": this.formData.title,           // string
  "resvProperty": 0,                         // int
  "resvDev": [this.reserveInfo.devId],       // array of int devIds
  "memo": this.formData.memo                 // string
}
```

**Create response** (code=0 on success):

```json
{
  "code": 0,
  "message": "新增成功",
  "data": {
    "uuid": "e51687a491884d36b75c3f2a939f547c",  // ← use for cancel
    "resvId": 183440,
    "appAccNo": 76727,
    "resvDate": 20260701,
    "resvBeginTime": 1782871200000,
    "resvEndTime": 1782874800000,
    "resvStatus": 1027,
    "classKind": 1,
    "resvProperty": 0,
    "testName": "test for cancel demo",
    "devName": null,
    "resvDevInfoList": [
      {"resvId": 183440, "devId": 10, "devName": "G302（1-3人）", "devSn": 10, ...}
    ],
    ...
  }
}
```

### Reservation cancel wire format (confirmed 2026-06-30)

**Endpoint:** `POST /ic-web/reserve/delete`
**Body:** JSON `{"uuid": "<uuid_from_create_response>"}`
**Success response:** `{"code": 0, "message": "删除成功", "data": null}`

The endpoint does NOT accept `resvId` — only `uuid`. Using
`{"resvId": 183440}` returns code=1 "请选择相应的数据". Using the
correct `uuid` from the create response returns code=0.

### My reservations (read) — param names confirmed

**Endpoint:** `GET /ic-web/borrow/reserve/own`
**Params (query string):**
- `beginDate=YYYY-MM-DD` (NOT `startDate` — that returns "请选择开始日期")
- `endDate=YYYY-MM-DD`
- `page=N`
- `pageSize=N`
- Optional: `needStatus`, `orderKey`, `orderModel`

Returns paginated list, rows in `data.rows` or `data.list` or `data`
directly depending on the response shape.
