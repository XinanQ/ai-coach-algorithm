# 后端接口文档 — 银行 AI 话术陪练小程序

> 前端已按 `config / utils/request / api / mock` 四层重构。页面只调用 `api/<域>/<方法>`，
> 数据源由 `config.js` 的 `USE_MOCK` 切换：`true` 走本地 mock，`false` 走本文档的真实接口。
> 后端就绪后，把 `USE_MOCK` 置为 `false`、配置 `BASE_URL` 即可，**页面无需改动**。

## 通用约定

| 项 | 约定 |
|---|---|
| BaseURL | `config.js` 的 `BASE_URL`（需在小程序后台配置 request 合法域名） |
| 路径前缀 | 所有接口位于 `/api` 下（下文 `/auth/login` 实际为 `/api/auth/login`），由 `config.API_PREFIX` 统一承载 |
| 认证 | 除登录类接口外，请求头携带 `X-Auth-Token: <token>`（**注意：不是 Authorization，也不是 Bearer**） |
| 响应信封 | `{ "code": 0, "message": "ok", "data": <payload> }`；`code !== 0` 视为业务错误，前端弹 `message` |
| 401 | token 失效/未登录；前端自动清登录态并跳转登录页 |
| 分页 | 列表类可接受 query `page`(从 1 起)、`size`；响应可附 `total` |
| 时间 | `YYYY-MM-DD` 或 ISO 字符串 |
| 角色 | `role`: `manager`(管理员) / `staff`(普通员工) |

前端封装见 [utils/request.js](../utils/request.js)（`get/post/put/del/upload`）。

---

## 1. 认证 `api.auth`

### POST /api/auth/login — 工号密码登录
- 调用页：[pages/login](../pages/login/login.js)
- Body：`{ "employeeNo": "0001", "password": "******" }`
- data：`{ "token": "xxx", "user": { "empId":"0001","name":"张三","branch":"XX网点","role":"staff" } }`
- token 位置：`res.data.data.token`（信封 `data.token`，前端 request 已统一解包到 `data`）
- 说明：`role` 为空时由前端「角色选择」页决定；接后端后建议由本接口或 `/auth/profile` 返回真实角色与权限。

### POST /auth/wx-login — 微信登录（可选）
- Body：`{ "code": "wx.login 返回的 code" }`
- data：同上 `{ token, user }`

### GET /auth/profile — 当前用户资料
- data：`{ "empId","name","branch","role" }`

### POST /auth/logout — 退出登录
- data：`null`

---

## 2. 首页 `api.home`

### GET /home/summary — 员工首页概览
- 调用页：[pages/index](../pages/index/index.js)
- data：`{ "userName":"张三","todayReported":false,"myRank":12,"myScore":86,"scoreTarget":120,"practiceTaskCount":1 }`
- 说明：`scoreTarget` 为本月积分目标，前端据 `myScore/scoreTarget` 画完成度环。

---

## 3. 业绩上报 `api.report`

### GET /report/indicators — 上报指标
- data：`[ { "id":1,"name":"存款净增额","unit":"万元" }, ... ]`

### POST /report — 提交上报
- 调用页：[pages/report](../pages/report/report.js)
- Body：`{ "indicatorId":1, "value":"8.5", "images":["https://.../a.jpg"] }`
- data：`{ "id": 123 }`
- 图片：先经 `POST /upload` 换取 url，再放入 `images`。

### GET /report/history — 本人上报历史
- data：`[ { "id":1,"date":"2026-06-14","indicator":"存款净增额","value":"8.5万元","status":"已通过","statusClass":"approved","reason":"" } ]`
- `statusClass`：`approved|rejected|pending`。

### POST /upload — 文件上传（multipart，字段 `file`）
- 配合 `wx.uploadFile`；data：`{ "url":"https://.../a.jpg" }`

---

## 4. 排行榜 `api.ranking`

### GET /ranking?period=day|week|month
- 调用页：[pages/ranking](../pages/ranking/ranking.js)
- data：`{ "myRank":12, "myScore":86, "list":[ { "rank":1,"name":"员工1","score":97 } ] }`

---

## 5. 喜报 `api.news`

### GET /news — 喜报列表
- data：`[ { "id":1,"title":"存款大单喜报","date":"2026-06-14" } ]`

### GET /news/{id} — 喜报详情
- data：`{ "id":1,"title":"...","date":"2026-06-14","recipient":"张三","content":"...","imageUrl":"" }`

---

## 6. 陪练 `api.practice`

### GET /practice/growth — 成长信息
- data：`{ "level":5,"levelName":"专业进阶","points":1260,"target":1800,"weekGain":320,"streak":7 }`

### GET /practice/tasks — 任务三分类
- 调用页：[pages/practice/list](../pages/practice/list/list.js)
- data：
```json
{
  "assigned": [ { "id":"t1","name":"风险揭示话术","scene":"理财产品风险揭示","level":"must","status":"进行中","deadline":"06/28","points":50 } ],
  "library":  [ { "id":"l1","name":"信用卡分期回访","type":"实战","points":40 } ],
  "done":     [ { "id":"t0","name":"存款推荐话术","scene":"存款推荐","status":"已完成","score":82,"date":"06/10" } ]
}
```
- `level`：`must`(必须完成，计入完成率) / `recommend`(强烈推荐，不计硬性考核)。

### GET /practice/tasks/{id} — 任务详情
- 调用页：[pages/practice/intro](../pages/practice/intro/intro.js)
- data：`{ "scene","customerName","customerDesc","tags":[],"rounds":3,"background","goal","requirements":[],"duration":"15-20 分钟","progress":0 }`

### POST /practice/dialog/start — 开始对话
- Body：`{ "taskId":"t1" }`
- data：`{ "messages":[ { "role":"ai","content":"..." } ], "round":1 }`

### POST /practice/dialog/reply — 提交一轮回复
- 调用页：[pages/practice/chat](../pages/practice/chat/chat.js)
- Body：`{ "taskId":"t1", "text":"用户回复内容" }`
- data：`{ "message":{ "role":"ai","content":"..." }, "round":2, "liveScore":78 }`

### POST /practice/dialog/finish — 结束对话（触发评分）
- Body：`{ "taskId":"t1" }`
- data：`{ "resultId":"r1", "score":82 }`

### GET /practice/result/{taskId} — 评分报告
- 调用页：[pages/practice/result](../pages/practice/result/result.js)
- data：`{ "score":88,"delta":6,"cert":"新晋「合规揭示达人」","certDesc":"...","dimensions":[ { "label":"合规度","value":92,"level":"优秀" } ],"rewardPoints":80,"rewardExp":120,"suggestion":"..." }`

### GET /practice/review/{taskId} — 复盘（原话术/AI 优化）
- 调用页：[pages/practice/review](../pages/practice/review/review.js)
- data：`{ "original":"...", "optimized":"..." }`

### GET /practice/history — 陪练历史
- data：`[ { "id":1,"scene":"存款推荐","score":82,"date":"2026-06-14" } ]`

---

## 7. 话术库 `api.script`

### GET /scripts — 列表
- data：`[ { "id":"s1","scene":"理财产品风险揭示","title":"稳健型客户风险揭示","tags":["合规表达","风险提示"],"date":"06/12" } ]`

### GET /scripts/{id} — 详情
- data：`{ "id","scene","title","tags":[],"standard":"标准话术","mine":"我的优化话术" }`

### POST /scripts — 收藏优化话术
- Body：`{ "taskId":"t1","optimized":"...","scene":"...","title":"...","tags":[] }`
- data：`{ "id":"s9" }`

---

## 8. 管理端 `api.admin`

### GET /admin/workspace/stats?branch&position&type&period — 驾驶舱统计
- 调用页：[pages/admin/workspace](../pages/admin/workspace/workspace.js)
- data：`{ "completionRate":86,"completionDelta":9,"avgScore":82,"avgDelta":5,"pendingCount":24,"highRiskCount":7 }`

### GET /admin/workspace/ranking?branch&position&type&period — 员工排行
- data：`[ { "rank":1,"name":"李晨","dept":"客户经理","rate":95,"score":88 } ]`

### POST /admin/tasks/assign — 下发任务
- 调用页：[pages/admin/assign](../pages/admin/assign/assign.js)
- Body：`{ "name":"理财产品风险揭示话术","level":"must","target":"全部客户经理","deadline":"2026-06-28","dimensions":["合规表达","风险提示"] }`
- data：`{ "id":"task-1" }`

### GET /admin/task-templates — 任务模板库
- data：`[ { "id":"tt1","name":"理财产品风险揭示话术","scene":"风险揭示","dimensions":4 } ]`

### GET /admin/analysis — 数据分析
- 调用页：[pages/admin/analysis](../pages/admin/analysis/analysis.js)
- data：`{ "team":{ "completionRate":86,"avgScore":82,"recommendRate":76,"highRiskCount":7 },"completionTop3":[ { "name":"李晨","value":95 } ],"abilityTop3":[ { "name":"风险揭示话术","count":32 } ] }`

### GET /admin/employees — 员工列表
- data：`[ { "id":"e1","name":"李晨","dept":"客户经理","rate":95,"score":88,"progress":90 } ]`

### GET /admin/employees/{id} — 员工详情
- 调用页：[pages/admin/employee-detail](../pages/admin/employee-detail/employee-detail.js)
- data：`{ "id":"e1","name":"李晨","dept":"客户经理","rate":95,"score":88,"tasks":[ { "name":"风险揭示话术","status":"已完成","score":88 } ] }`
- `score` 为 `null` 表示进行中未出分。

---

## 接口与前端方法对照

| 域 | 前端方法 | 接口 |
|---|---|---|
| auth | `api.auth.login/wxLogin/getProfile/logout` | `/auth/*` |
| home | `api.home.getSummary` | `/home/summary` |
| report | `api.report.getIndicators/submit/getHistory` | `/report/*` |
| ranking | `api.ranking.getRanking` | `/ranking` |
| news | `api.news.getList/getDetail` | `/news` |
| practice | `api.practice.*` | `/practice/*` |
| script | `api.script.getList/getDetail/save` | `/scripts` |
| admin | `api.admin.*` | `/admin/*` |
