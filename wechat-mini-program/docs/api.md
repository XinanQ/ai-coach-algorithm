# 后端接口文档 — 银行 AI 话术陪练小程序

> 前端已按 `config / utils/request / api / mock` 四层重构。页面只调用 `api/<域>/<方法>`，
> 数据源由 `config.js` 的 `USE_MOCK` 切换：`true` 走本地 mock，`false` 走本文档的真实接口。
> 后端就绪后，把 `USE_MOCK` 置为 `false`、配置 `BASE_URL` 即可，**页面无需改动**。

> ⚠️ **本文档已对齐当前后端实现（2026-06-25 核对）。** 后端业务接口统一前缀为 **`/api/mini`**，
> 成功码为 **`code === 200`**（不是 0）。下表「实现状态」标注每个接口是否已有真实后端：
> 后端尚未实现的，前端仍走本地 mock。

## 通用约定

| 项 | 约定 |
|---|---|
| BaseURL | `config.js` 的 `BASE_URL`（需在小程序后台配置 request 合法域名），当前 `http://localhost:8081` |
| 路径前缀 | `config.API_PREFIX = '/api'`，最终地址 = `BASE_URL + '/api' + path`。**登录**走 `/auth/login`，**小程序业务接口**走 `/mini/...`（即 `/api/mini/...`） |
| 认证 | 除登录类接口外，请求头携带 `X-Auth-Token: <token>`（**注意：不是 Authorization，也不是 Bearer**） |
| 响应信封 | `{ "code": 200, "message": "Success", "data": <payload> }`；**`code !== 200` 视为业务错误**，前端弹 `message`。`utils/request.js` 成功时直接解包返回 `data` |
| 401 | token 失效/未登录；前端自动清登录态并跳转登录页（登录接口返回 401 例外，表示工号或密码错误） |
| 分页 | 列表类可接受 query `page`(从 1 起)、`size`；响应可附 `total` |
| 时间 | `YYYY-MM-DD` 或 ISO 字符串 |

**实现状态图例：**

- ✅ **已实现** —— 后端真实接口可用。
- 🟡 **Mock** —— 后端尚未实现，前端走本地 `mock/`，接口形状为前端约定（接后端时以后端为准）。

前端封装见 [utils/request.js](../utils/request.js)（`get/post/put/del/upload`）。

---

## 实现状态总览

| 域 | 接口 | 实现状态 |
|---|---|---|
| auth | `POST /api/auth/login` | ✅ 已实现 |
| auth | `POST /api/auth/wx-login` | 🟡 Mock（后端仅 `/login`） |
| auth | `POST /api/auth/logout` | 🟡 Mock |
| auth | `GET /api/mini/profile` | ✅ 已实现 |
| auth | `GET /api/mini/account` | ✅ 已实现（前端暂未接入） |
| home | `GET /api/mini/home` | ✅ 已实现（积分/排名为占位值） |
| practice | `GET /api/mini/practice/tasks` | ✅ 已实现（演示数据） |
| practice | `GET /api/mini/practice/tasks/{taskId}` | ✅ 已实现（演示数据） |
| practice | `POST /api/mini/practice/dialog/start` | ✅ 已实现（规则生成） |
| practice | `POST /api/mini/practice/dialog/reply` | ✅ 已实现（规则生成） |
| practice | `POST /api/mini/practice/dialog/finish` | ✅ 已实现（规则生成） |
| practice | `GET /api/mini/practice/result/{taskId}` | 🟡 Mock（`finish` 已返回完整结果，冗余） |
| practice | `GET /api/mini/practice/review/{taskId}` | 🟡 Mock |
| practice | `GET /api/mini/practice/history` | 🟡 Mock |
| report | `GET /api/report/indicators`、`POST /api/report`、`GET /api/report/history`、`POST /api/upload` | 🟡 Mock（后端 `/api/admin/reports` 为管理端，小程序口径未实现） |
| ranking | `GET /api/mini/ranking` | 🟡 Mock（后端仅 `/api/admin/rankings`） |
| news | `GET /api/news`、`GET /api/news/{id}` | 🟡 Mock |
| script | `GET /api/mini/scripts[/{id}]`、`POST /api/mini/scripts` | 🟡 Mock |
| admin | `/api/mini/admin/*`（workspace / templates / tasks / analysis / employees） | 🟡 Mock |

> 说明：practice 五个「已实现」接口当前由后端返回**固定演示数据**（`source: "RULE_BASED"`，规则生成，非真实大模型 / 数据库），字段形状即下文，后续接 AI/DB 时形状不变。

---

## 1. 认证 `api.auth`

### ✅ POST /api/auth/login — 工号密码登录
- 调用页：[pages/login](../pages/login/login.js)（前端方法 `api.auth.login(empId, password)`）
- Body：`{ "employeeNo": "93605894", "password": "123456" }`
- data（**扁平对象**，token 与用户字段同级）：
```json
{
  "employeeId": 1,
  "employeeNo": "93605894",
  "name": "李家慧",
  "position": "市行管理员",
  "level": "CITY",
  "isAdmin": true,
  "organizationId": 1,
  "organizationName": "南京市行",
  "organizationCode": "NJ_CITY",
  "isInProject": false,
  "token": "xxxxxxxx"
}
```
- token 位置：`res.data.data.token`（信封 `data.token`，前端 request 已统一解包到 `data`）。
- 失败：工号/密码错误返回 HTTP 401 + `code !== 200`，前端提示「工号或密码错误」，**不触发**登录过期跳转。

### 🟡 POST /api/auth/wx-login — 微信登录（后端未实现）
- Body：`{ "code": "wx.login 返回的 code" }`
- data：同登录 `{ ...user, token }`

### 🟡 POST /api/auth/logout — 退出登录（后端未实现）
- data：`null`。前端当前直接本地清登录态。

### ✅ GET /api/mini/profile — 当前用户资料（精简，给「我的」页）
- 前端方法：`api.auth.getProfile()`（`silent`，失败不弹 toast）；调用页 [pages/profile](../pages/profile/profile.js)
- data：
```json
{ "name": "李家慧", "organizationName": "南京市行", "roleName": "市行管理员", "isAdmin": true }
```

### ✅ GET /api/mini/account — 当前用户账号详情（后端已就绪，前端暂未接入）
- data：
```json
{
  "employeeId": 1, "employeeNo": "93605894", "name": "李家慧",
  "email": "...", "position": "市行管理员", "department": "...",
  "level": "CITY", "isAdmin": true, "isInProject": false,
  "organizationId": 1, "organizationName": "南京市行",
  "organizationCode": "NJ_CITY", "organizationLevel": "CITY"
}
```

---

## 2. 首页 `api.home`

### ✅ GET /api/mini/home — 员工首页概览
- 前端方法：`api.home.getSummary()`；调用页 [pages/index](../pages/index/index.js)
- data：
```json
{
  "name": "张三",
  "level": "EMPLOYEE",
  "isAdmin": false,
  "organizationId": 5,
  "organizationName": "珠江路网点",
  "monthlyScore": 0,
  "scoreTarget": 0,
  "completionRate": 0,
  "rank": null,
  "rankScope": "暂无排名",
  "todayReported": false,
  "pendingPracticeTaskCount": 0
}
```
- 说明：`monthlyScore/scoreTarget/completionRate/rank/todayReported/pendingPracticeTaskCount` 当前为**后端占位值**（积分、排名、上报、陪练模块就绪后回填）。前端据 `monthlyScore/scoreTarget` 画完成度环，`rank` 为 `null` 时显示 `rankScope`。

---

## 3. 业绩上报 `api.report` 🟡（后端未实现，前端 mock）

> 后端已有管理端 `/api/admin/reports`（提交/审核/积分），但**小程序口径的 `/report/*` 未实现**，前端暂走本地 mock。

### 🟡 GET /api/report/indicators — 上报指标
- data：`[ { "id":1,"name":"存款净增额","unit":"万元" }, ... ]`

### 🟡 POST /api/report — 提交上报
- 调用页：[pages/report](../pages/report/report.js)
- Body：`{ "indicatorId":1, "value":"8.5", "images":["https://.../a.jpg"] }`
- data：`{ "id": 123 }`；图片先经 `POST /upload` 换取 url 再放入 `images`。

### 🟡 GET /api/report/history — 本人上报历史
- data：`[ { "id":1,"date":"2026-06-14","indicator":"存款净增额","value":"8.5万元","status":"已通过","statusClass":"approved","reason":"" } ]`
- `statusClass`：`approved|rejected|pending`。

### 🟡 POST /api/upload — 文件上传（multipart，字段 `file`）
- 配合 `wx.uploadFile`；data：`{ "url":"https://.../a.jpg" }`

---

## 4. 排行榜 `api.ranking` 🟡（后端未实现，前端 mock）

> 后端已有管理端 `/api/admin/rankings`（四层组织 + 日/周/月），但**小程序 `/mini/ranking` 未实现**。

### 🟡 GET /api/mini/ranking?period=day|week|month
- 前端方法：`api.ranking.getRanking(period)`；调用页 [pages/ranking](../pages/ranking/ranking.js)
- data：`{ "myRank":12, "myScore":86, "list":[ { "rank":1,"name":"员工1","score":97 } ] }`

---

## 5. 喜报 `api.news` 🟡（后端未实现，前端 mock）

### 🟡 GET /api/news — 喜报列表
- data：`[ { "id":1,"title":"存款大单喜报","date":"2026-06-14" } ]`

### 🟡 GET /api/news/{id} — 喜报详情
- data：`{ "id":1,"title":"...","date":"2026-06-14","recipient":"张三","content":"...","imageUrl":"" }`

---

## 6. 陪练 `api.practice`

> ✅ 任务列表/详情 + 对话流（start/reply/finish）已由后端实现，当前返回固定演示数据（`source:"RULE_BASED"`）。
> 对话流以 **`sessionId` 串联**：`start` 返回 `sessionId`，后续 `reply`/`finish` 用它定位会话。固定 **3 轮**。

### ✅ GET /api/mini/practice/tasks?tab=assigned|self|done — 任务列表（含成长信息）
- 前端方法：`api.practice.getTasks(tab)`；调用页 [pages/practice/list](../pages/practice/list/list.js)
- `tab`：`assigned`(指派给我，默认) / `self`(自主练习) / `done`(已完成)。每切 tab 单独拉取。
- data（成长信息并入返回体，`list` 仅含当前 tab）：
```json
{
  "levelName": "Lv5 专业进阶",
  "points": 1260,
  "target": 1800,
  "streakDays": 7,
  "weekGain": 320,
  "list": [
    {
      "taskId": "t1",
      "title": "风险揭示话术",
      "scene": "理财产品风险揭示",
      "level": "must",
      "levelText": "必须完成",
      "status": "IN_PROGRESS",
      "statusText": "进行中",
      "deadline": "2026-06-28",
      "rewardPoints": 50
    }
  ]
}
```
- `level`：`must`(必须完成，计入完成率) / `recommend`(强烈推荐，不计硬性考核)。
- `status`：`IN_PROGRESS` / `PENDING` / `DONE`；中文展示用 `statusText`。

### ✅ GET /api/mini/practice/tasks/{taskId} — 任务详情
- 前端方法：`api.practice.getTaskDetail(taskId)`；调用页 [pages/practice/intro](../pages/practice/intro/intro.js)
- data：
```json
{
  "taskId": "t1", "title": "风险揭示话术", "scene": "理财产品风险揭示",
  "rounds": 3, "customerName": "王女士", "customerDesc": "35岁，企业白领，有一笔闲置资金",
  "tags": ["流动性担忧","利率敏感","风险厌恶"],
  "background": "...", "goal": "...",
  "requirements": ["完成 3 轮对话","综合得分 ≥ 80 分"],
  "duration": "15-20 分钟", "progress": 0, "scriptId": "s1"
}
```

### ✅ POST /api/mini/practice/dialog/start — 开始对话
- 前端方法：`api.practice.startDialog(taskId)`
- Body：`{ "taskId":"t1" }`
- data：
```json
{
  "sessionId": "s-xxxx",
  "taskId": "t1",
  "round": 1,
  "totalRounds": 3,
  "liveScore": 70,
  "messages": [ { "role": "ai", "content": "您好，我最近想了解一下存款产品……" } ],
  "source": "RULE_BASED"
}
```

### ✅ POST /api/mini/practice/dialog/reply — 提交一轮回复
- 前端方法：`api.practice.replyDialog(sessionId, text)`；调用页 [pages/practice/chat](../pages/practice/chat/chat.js)
- Body：`{ "sessionId":"s-xxxx", "text":"用户回复内容" }`
- data：
```json
{
  "round": 2,
  "totalRounds": 3,
  "liveScore": 78,
  "message": { "role": "ai", "content": "如果资金需要随时支取，您会怎么建议呢？" },
  "finished": false,
  "source": "RULE_BASED"
}
```
- 最后一轮回复后 `finished:true`、`message:null`，前端据此引导进入「结束/评分」。

### ✅ POST /api/mini/practice/dialog/finish — 结束对话（触发评分）
- 前端方法：`api.practice.finishDialog(sessionId)`
- Body：`{ "sessionId":"s-xxxx" }`
- data（**直接返回完整评分报告**）：
```json
{
  "resultId": "r-xxxx",
  "taskId": "t1",
  "score": 82,
  "scoreDelta": 6,
  "certificationTitle": "新晋「合规揭示达人」",
  "certificationDesc": "合规表达达标，完成专项认证",
  "dimensionScores": [
    { "name": "合规度", "score": 92, "level": "优秀" },
    { "name": "共情力", "score": 84, "level": "良好" }
  ],
  "rewardPoints": 80,
  "rewardExp": 120,
  "weakTags": ["流动性解释不足","风险提示不足"],
  "suggestion": "……",
  "source": "RULE_BASED"
}
```

### 🟡 GET /api/mini/practice/result/{taskId} — 评分报告（后端未单独实现）
- 调用页：[pages/practice/result](../pages/practice/result/result.js)
- 说明：`finish` 已返回同等信息，本接口为冗余的前端 mock；结果页可直接复用 `finish` 返回。data 形状同 `finish`。

### 🟡 GET /api/mini/practice/review/{taskId} — 复盘（原话术/AI 优化，后端未实现）
- 调用页：[pages/practice/review](../pages/practice/review/review.js)
- data：`{ "original":"...", "optimized":"..." }`

### 🟡 GET /api/mini/practice/history — 陪练历史（后端未实现）
- data：`[ { "id":1,"scene":"存款推荐","score":82,"date":"2026-06-14" } ]`

---

## 7. 话术库 `api.script` 🟡（后端未实现，前端 mock）

### 🟡 GET /api/mini/scripts — 列表
- data：`[ { "scriptId":"s1","scene":"理财产品风险揭示","title":"稳健型客户风险揭示","tags":["合规表达","风险提示"],"date":"06/12" } ]`

### 🟡 GET /api/mini/scripts/{id} — 详情
- data：`{ "scriptId","scene","title","tags":[],"standard":"标准话术","sourceTaskId":"t1" }`
- `sourceTaskId` 存在时展示「我的优化话术」块，缺省自动隐藏。

### 🟡 POST /api/mini/scripts — 收藏优化话术
- Body：`{ "taskId":"t1","optimized":"...","scene":"...","title":"...","tags":[] }`
- data：`{ "scriptId":"s9" }`

---

## 8. 管理端 `api.admin` 🟡（后端未实现，前端 mock）

### 🟡 GET /api/mini/admin/workspace?period — 驾驶舱（stats + ranking 合并单接口）
- 前端方法：`api.admin.getWorkspace(filters)`；调用页 [pages/admin/workspace](../pages/admin/workspace/workspace.js)
- 筛选当前仅透传 `period`（week/month/quarter）；`branchId/position/type` 待后端定取值口径。
- data：
```json
{
  "completionRate":86,"completionDelta":9,"avgScore":82,"avgDelta":5,
  "pendingCount":24,"highRiskCount":7,
  "ranking":[ { "rank":1,"name":"李晨","position":"客户经理","completionRate":95,"score":88 } ]
}
```

### 🟡 GET /api/mini/admin/practice/templates — 任务模板库
- data：`[ { "id":"tt1","name":"理财产品风险揭示话术","scene":"风险揭示","dimensions":4 } ]`

### 🟡 GET /api/mini/admin/practice/templates/{templateId} — 模板详情（任务库→下发预填）
- data：`{ "id":"tt1","name":"...","dimensions":["合规表达","风险提示"] }`

### 🟡 POST /api/mini/admin/practice/tasks — 下发任务
- 调用页：[pages/admin/assign](../pages/admin/assign/assign.js)
- Body：`{ "templateId":"tt1","level":"must","targetPosition":"全部客户经理","deadline":"2026-06-28","dimensions":["合规表达","风险提示"] }`
- data：`{ "id":"task-1" }`

### 🟡 GET /api/mini/admin/analysis?period — 数据分析
- 调用页：[pages/admin/analysis](../pages/admin/analysis/analysis.js)
- data：`{ "team":{ "completionRate":86,"avgScore":82,"recommendRate":76,"highRiskCount":7 },"completionTop3":[ { "name":"李晨","value":95 } ],"abilityTop3":[ { "name":"风险揭示话术","count":32 } ] }`

### 🟡 GET /api/mini/admin/employees — 员工列表
- data：`[ { "id":"e1","name":"李晨","position":"客户经理","completionRate":95,"score":88,"progress":90 } ]`

### 🟡 GET /api/mini/admin/employees/{id} — 员工详情
- 调用页：[pages/admin/employee-detail](../pages/admin/employee-detail/employee-detail.js)
- data：`{ "id":"e1","name":"李晨","position":"客户经理","completionRate":95,"score":88,"tasks":[ { "name":"风险揭示话术","status":"已完成","score":88 } ] }`
- `score` 为 `null` 表示进行中未出分。

---

## 接口与前端方法对照

| 域 | 前端方法 | 接口 | 状态 |
|---|---|---|---|
| auth | `api.auth.login` | `POST /api/auth/login` | ✅ |
| auth | `api.auth.wxLogin` | `POST /api/auth/wx-login` | 🟡 |
| auth | `api.auth.getProfile` | `GET /api/mini/profile` | ✅ |
| auth | `api.auth.logout` | `POST /api/auth/logout` | 🟡 |
| home | `api.home.getSummary` | `GET /api/mini/home` | ✅ |
| report | `api.report.getIndicators/submit/getHistory` | `/api/report/*` | 🟡 |
| ranking | `api.ranking.getRanking` | `GET /api/mini/ranking` | 🟡 |
| news | `api.news.getList/getDetail` | `/api/news` | 🟡 |
| practice | `api.practice.getTasks/getTaskDetail/startDialog/replyDialog/finishDialog` | `/api/mini/practice/*` | ✅ |
| practice | `api.practice.getResult/getReview/getHistory` | `/api/mini/practice/result|review|history` | 🟡 |
| script | `api.script.getList/getDetail/save` | `/api/mini/scripts` | 🟡 |
| admin | `api.admin.*` | `/api/mini/admin/*` | 🟡 |
