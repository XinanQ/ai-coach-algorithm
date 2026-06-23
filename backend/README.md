# StageOneCode3 使用说明
**❗❗️现在是 update，重启后数据一般会一直在 ，第六节里那些 POST 新建 的 curl 不必再跑，否则会在库里又多一批测试数据，和模拟数据混在一起**

**版本：** V4.1
**日期：** 2026-06-18 
**负责人：** 李家慧、蒋子涵  
**阶段：** 第一阶段 基础闭环版（后台 API，持续开发中）

---

## 一、项目简介

Spring Boot 3.1.5 + Java 21 + MySQL 的后端服务，提供机构、员工、登录（含 Token）、项目、指标库、项目挂指标、积分引擎/日志、**基础排名**、业绩上报等管理端 API；积分规则 API（`points_rules`）M1 暂不开发。

- 服务默认端口：**8081**
- 数据库名：**stage_one**
- 表由 JPA **自动建表/更新**（`ddl-auto=update`，重启一般保留数据）
- 代码按**业务模块**分文件夹存放：每个业务一块，里面通常有「实体类、数据库访问、业务逻辑、对外接口」四层


---

## 二、目录结构

```
StageOneCode3/
├── README.md                 # 本说明（怎么装环境、启动、测接口）
├── pom.xml                   # 项目依赖配置（Maven）
├── mvnw / mvnw.cmd           # 命令行启动用的脚本
└── src/main/
    ├── java/com/
    │   ├── bank/stageonecode/
    │   │   └── StageOneCodeApplication.java   # 程序入口，在 IDEA 里点 Run 就跑这个
    │   ├── organization/      # 机构管理：市行/支行/网点的增删改查、树形结构
    │   │   └── dto/               # 机构接口入参/出参（Create / Update / Response）
    │   ├── employee/              # 员工管理：员工信息维护、Excel 批量导入导出
    │   │   └── dto/               # 员工接口入参/出参
    │   ├── auth/                  # 登录：工号 + 密码（BCrypt）、Token 会话 auth_session
    │   │   └── dto/               # LoginRequest / LoginResponse
    │   ├── project/               # 项目管理；含项目挂指标、积分标准（ProjectIndicator）
    │   │   └── dto/               # 项目挂指标接口入参/出参
    │   ├── indicator/             # 指标管理：指标库（存款、理财等）、目标分解、催办
    │   │   └── dto/               # 指标接口入参/出参
    │   ├── points/                # 积分计算引擎、积分日志 API；
    │   ├── ranking/               # 基础排名 API（汇总 points_logs）
    │   ├── task/                  # 系统任务记录：分解指标、催办时产生的待办记录
    │   ├── performance/           # 业绩上报：员工每日填报、管理员审核通过/驳回
    │   └── common/                # 公共组件：WebConfig（Token 拦截）、统一错误提示
    └── resources/
        └── application.properties   # 数据库账号密码、端口 8081 等配置
```
### 文件夹 ↔ 数据库表（对照）

| 代码文件夹 | 数据库表 | 通俗说明 |
|------------|----------|----------|
| `organization` | `organizations` | 存各级机构（市行、支行、网点） |
| `employee` | `employees` | 存员工姓名、邮箱、所属网点等 |
| `auth` | `user_account`、`auth_session` | 登录账号；Token 会话（8 小时有效） |
| `project` | `projects` | 存一次考核/营销活动的项目信息 |
| `indicator` | `indicators` | 存业务指标定义（如「定期存款」「贷记卡」） |
| `task` | `tasks` | 存分解、催办产生的系统任务 |
| `performance` | `task_results` | 每日上报与审核；含 project_id、indicator_id、organization_id、attachment_url |
| `project`（实体 `ProjectIndicator`） | `project_indicators` | 项目挂指标、积分标准（V1 积分表） |
| `points` | `points_rules` | 积分规则配置（JSON、生效期） |
| `points` | `points_logs` | 积分变动日志；`biz_date` = 上报填写的 `reportDate`（非提交/审核时间）；`organization_id` = 员工所属机构（审核时从 `employees` 取，非上报 JSON 里的 `organizationId`）；无需单独 mock |

---

## 三、环境准备

1. **JDK 21**
2. **MySQL 8.x**（安装后保持服务运行）
3. **IntelliJ IDEA**（推荐）
4. 可选：**Apifox**（测 API）、**浏览器**（GET 接口）

### 1. 修改密码

打开`src/main/resources/application.properties`：

```properties
spring.datasource.password=${DB_PASSWORD:你的MySQL密码}
```

### 2. 创建数据库（一次即可）
终端执行：

```bash
mysql -u root -p
```

登录后执行：

```sql
CREATE DATABASE IF NOT EXISTS stage_one
EXIT;
```

### 3. 导入模拟数据（可选，组员提供）

**先启动应用**（自动建表），再按顺序导入（路径按本机调整）：

```bash
mysql -u root -p stage_one < mock_organization_data.sql
mysql -u root -p stage_one < mock_employee_data.sql
mysql -u root -p stage_one < mock_user_account_data.sql
```
---

## 四、怎么确认跑通了
### 1. 启动

IDEA 打开含 `pom.xml` 的目录 → JDK 21 → 运行 `StageOneCodeApplication`  
看到 **`Started StageOneCodeApplication`** 即成功。

### 2. 浏览器验证

**服务启动后**，除 `/api/auth/login` 外，所有 `/api/**` 请求须带请求头 **`X-Auth-Token`**（先按第六节例子 0 登录拿 token）。浏览器直接打开下面链接会返回 401，请用 Postman 或 curl。

#### 基础（建议都点一遍，需 token）

| 说明 | 地址 |
|------|------|
| 机构列表 | http://localhost:8081/api/admin/organizations |
| 机构树 | http://localhost:8081/api/admin/organizations/tree |
| 员工列表（导入后约 100 条） | http://localhost:8081/api/admin/employees |
| 项目列表 | http://localhost:8081/api/admin/projects |
| 项目挂指标列表（需先有项目、指标数据） | http://localhost:8081/api/admin/projects/1/indicators |
| 指标分页列表 | http://localhost:8081/api/admin/indicators?page=0&size=10 |
| 指标分解进度（需 id） | http://localhost:8081/api/admin/indicators/1/progress |
| 上报列表（全部） | http://localhost:8081/api/admin/reports |
| 待审核上报 | http://localhost:8081/api/admin/reports?status=PENDING |
| 积分日志 | http://localhost:8081/api/admin/points-logs |
| 积分排名 | http://localhost:8081/api/admin/rankings?projectId=1&indicatorId=1&level=employee&period=MONTH&date=2026-06-10 |

> 指标列表带中文筛选参数时，浏览器可能 400，请用 Postman 或第六节 curl。  
> 项目挂指标空库直接访问可能返回 `项目不存在: 1`，请先按第六节例子 4 用 curl 建数据。

### 3. MySQL验证表（终端）

```bash
mysql -u root -p
```

```sql
USE stage_one;
SHOW TABLES;   -- 应有 11 张表（含 user_account、auth_session）
DESC indicators;
mysql -u root -p -e "USE stage_one; SELECT COUNT(*) AS orgs FROM organizations; SELECT COUNT(*) AS emps FROM employees; SELECT COUNT(*) AS accounts FROM user_account;"
```

> 开发配置 `ddl-auto=update`：**重启一般保留数据**；改回 `create` 会每次重建表并清空。

---

## 五、目前进度

| 模块 | 路径前缀 | 状态 | 说明 |
|----|----------|-----|------|
| 指标库 | `/api/admin/indicators` | 较完整 | 增删改查、分页、启用停用 |
| 指标分解/催办 | `/api/admin/indicators/{id}/decompose` 等 | 较完整 | 分解（含 targetValue、机构/员工目标）、子节点、进度查询、催办 |
| 机构 | `/api/admin/organizations` | 较完整 | 增删改查、树、按层级查；按登录机构可见；含 staffCount 统计 |
| 员工 | `/api/admin/employees` | 较完整 | 增删改查、Excel 导入导出；按登录机构可见 |
| 登录 | `/api/auth/login` | 较完整 | 工号 + 密码登录，Token 会话（8 小时） |
| 项目 | `/api/admin/projects` | 基础可用 | 增删改查、改状态；创建须带 `reportDeadline` |
| 业绩上报 | `/api/admin/reports` | 基础可用 | 提交/列表/详情/改删、审核通过驳回 |
| 项目挂指标 | `/api/admin/projects/{projectId}/indicators` | 较完整 | 增删改查、积分标准、重复挂接校验 |
| 积分计算引擎 | 审核通过触发 | 较完整 | `数量 × pointsStandard × ratio`；`points_logs.organization_id` 取员工所属机构 |
| 积分日志查询 | `/api/admin/points-logs` | 基础可用 | 按 reportId / employeeId 查询 |
| 积分规则配置 | `points_rules` | 表已建，API 未做 | 第一阶段暂不需要 |
| 排名 | `/api/admin/rankings` | 较完整 | 四层组织 + 日/周/月；`projectId` / `indicatorId` 均可选（不传=全部项目 / 整项目汇总）；同分并列；按登录机构可见；终端已测通 |
| 排名前端对接 | `web-admin` 排名页 | 未做 | 前端仍用 mock，未调后端 API |
| 喜报 / 低业绩 / 小程序登录 | — | 未做 | 第一阶段 Out 或后续 |

**基础排名 API 已完成项：** employee / outlet / branch / city 四层；DAY / WEEK / MONTH；汇总 `points_logs.biz_date`（= 上报 `reportDate`）。

| projectId | indicatorId | 含义 |
|-----------|-------------|------|
| 传 | 传 | 某项目 + 某指标 |
| 传 | 不传 | 某项目下全部指标加总 |
| 不传 | 传 | 全部项目 + 某指标 |
| 不传 | 不传 | 全部项目 + 全部指标 |

---

## 六、简单测试例子（终端复制即用）
**❗️❗️现在是 update，重启后数据一般会一直在 ，第六节里那些 POST 新建 的 curl 不必再跑，否则会在库里又多一批测试数据，和模拟数据混在一起**

**前提：** 已 Run 启动，控制台有 `Started StageOneCodeApplication`。

基础地址：`http://localhost:8081`

> **鉴权说明：** 除 `/api/auth/login` 外，下面所有 curl 都要先登录拿 `token`，并在请求头加 `-H "X-Auth-Token: <token>"`。示例里用 `$TOKEN` 表示登录返回的 token。

### 例子 0：登录拿 token（POST，需先导入 user_account）

```bash
curl -X POST "http://localhost:8081/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"employeeNo":"93605894","password":"123456"}'
```

成功：`"code":200`，`data.token` 即后续要用的 token。可设环境变量：

```bash
TOKEN="粘贴上一步返回的 data.token"
```

### 例子 1：查指标列表（GET）

```bash
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/indicators?page=0&size=10"
```

浏览器直接打开会 401，请用 curl 或 Postman 并带 token。

### 例子 2：新建一条指标（POST）

```bash
curl -X POST "http://localhost:8081/api/admin/indicators" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"定期存款","code":"DEPOSIT","unit":"万","category":"存款","enabled":true}'
```

成功：返回 JSON，里面有 `"id":1`，HTTP 状态 **201**。

测重复编码（应报错 400）：

```bash
curl -X POST "http://localhost:8081/api/admin/indicators" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"重复测试","code":"DEPOSIT","unit":"万","enabled":true}'
```

应看到类似：`"message":"指标编码已存在: DEPOSIT"`

### 例子 3：新建市行（POST）

```bash
curl -X POST "http://localhost:8081/api/admin/organizations" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试市行","code":"TEST_CITY","level":"CITY"}'
```

成功：返回 JSON，里面有 `"id":1`，`"level":"CITY"`。

再建支行（`parentId` 改成上一步返回的市行 id，一般是 1）：

```bash
curl -X POST "http://localhost:8081/api/admin/organizations?parentId=1" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试支行","code":"TEST_BRANCH","level":"BRANCH"}'
```

`level` 常用：`CITY` 市行、`BRANCH` 支行、`OUTLET` 网点。

### 例子 4：项目挂指标全流程（1.1.3.4）

**按顺序执行**。若尚无指标，先执行例子 2。

建项目：

```bash
curl -X POST "http://localhost:8081/api/admin/projects" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试项目","startDate":"2026-06-01","endDate":"2026-12-31","reportDeadline":"2026-12-31","status":"DRAFT"}'
```

挂指标时建议带上 `ratio` 与 `pointsStandard`，例如：

```bash
curl -X POST "http://localhost:8081/api/admin/projects/1/indicators" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"indicatorId":1,"unit":"万","ratio":0.35,"pointsStandard":0.5,"pointsUnit":"分/万","targetValue":100,"sortOrder":1}'
```

查列表（应有 1 条；浏览器也可打开第四节对应地址）：

```bash
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/projects/1/indicators"
```

重复挂接（应 400，`message` 为「该项目已挂接该指标」）：

```bash
curl -X POST "http://localhost:8081/api/admin/projects/1/indicators" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"indicatorId":1,"pointsStandard":10}'
```

更新积分标准：

```bash
curl -X PUT "http://localhost:8081/api/admin/projects/1/indicators/1" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pointsStandard":15,"targetValue":200}'
```

删除挂接（成功无返回体，HTTP **204**）：

```bash
curl -X DELETE "http://localhost:8081/api/admin/projects/1/indicators/1" \
  -H "X-Auth-Token: $TOKEN"
```

### 例子 5：提交一条上报（POST，新字段可选）

先确保已有项目 id=1、指标 id=1、员工 id=1（mock 导入后张明 `organization_id=2` 鼓楼支行）。`organizationId` 可传可不传，**审核写积分时以员工表机构为准**：

```bash
curl -X POST "http://localhost:8081/api/admin/reports/submit" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"projectId":1,"indicatorId":1,"organizationId":4,"submitter":"张明","submitterId":1,"reportDate":"2026-06-10","result":"120"}'
```

`projectId`、`indicatorId`、`organizationId`、`attachmentUrl`、`taskId` 均可不传；**若要审核后算分**，须传 `projectId`、`indicatorId`、`submitterId`。提交后状态为 `PENDING`。

审核通过（`id` 换成上一步返回的上报 id；query 用英文，中文需 `--data-urlencode`）：

```bash
curl -X POST "http://localhost:8081/api/admin/reports/1/approve?reviewer=admin&comment=ok" \
  -H "X-Auth-Token: $TOKEN"
```

审核通过后自动算分，`points_logs.biz_date` 与上报的 `reportDate` 相同。查积分日志（`reportId` 换成上报 id）：

```bash
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/points-logs?reportId=1"
```

若项目挂接时 `ratio=0.35`、`pointsStandard=0.5`，上报 `result=120`，则 `pointsDelta` 应为 **21**（120 × 0.5 × 0.35）。

### 例子 6：查积分排名（GET，需先有 points_logs）

先完成例子 5 审核通过，确保 `points_logs` 有数据。**每次请求 `level` 只能填一个值**（如 `outlet`，不要填 `employee,outlet`）。

```bash
# 全部项目 + 全部指标（projectId、indicatorId 都不传）
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?level=employee"

# 某项目整项目排名（不传 indicatorId）
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?projectId=1&level=employee"

# 全部项目 + 某指标
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?indicatorId=1&level=employee"

# 某项目 + 某指标
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?projectId=1&indicatorId=1&level=employee"

# 网点 / 支行 / 市行（各请求一次，level 单独传）
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?projectId=1&indicatorId=1&level=outlet"
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?projectId=1&indicatorId=1&level=branch"
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?projectId=1&indicatorId=1&level=city"

# 日榜（按 reportDate 写入的 biz_date，非审核当天）
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8081/api/admin/rankings?projectId=1&indicatorId=1&level=employee&period=DAY&date=2026-06-10"
```

**参数：** `projectId`、`indicatorId` 均可选（不传表示全部项目 / 整项目各指标加总，响应里未传的字段为 `null`）；`level` = `employee` | `outlet` | `branch` | `city`（每次一个）；`period` = `DAY` | `WEEK` | `MONTH`；`date` 可选，默认今天。

**汇总规则（M1）：**

| level | 汇总方式 |
|-------|----------|
| employee | 按 `employee_id` 加总 |
| outlet / branch / city | 按 `points_logs.organization_id` **向上**找对应层级机构后加总 |
| 并列 | 同分同名次，下一名顺延（1, 1, 2） |

**注意：** 员工挂在**支行**（如 mock 张明 org=2）时，积分进支行/市行榜，**不进网点榜**（网点在支行下方，向上找不到 OUTLET）。网点员工（如王晨 org=3 鼓楼营业室）才计入 outlet 榜。

### （可选）查 MySQL 里有没有写进去

```bash
mysql -u root -p -e "USE stage_one; SELECT id,name,code,enabled FROM indicators; SELECT id,name FROM projects; SELECT project_id,indicator_id,points_standard FROM project_indicators;"
```

输入 MySQL 密码后会打印表里的数据。

> Mac 终端直接用上面命令即可。Windows 若 `\` 换行报错，改成一行，或用 Git Bash。

---

## 七、常见问题

| 现象 | 处理 |
|------|------|
| 401 Missing auth token | 先执行例子 0 登录，其它请求加 `-H "X-Auth-Token: $TOKEN"` |
| 数据库连不上 | 检查 `application.properties` 密码、MySQL 是否启动 |
| 8081 端口占用 | 关掉旧进程，或改 `server.port` |
| 重启后数据没了 | 检查是否改回 `ddl-auto=create`；`update` 下一般会保留 |
| 导入 SQL 报 Duplicate entry | 表里已有数据，先 TRUNCATE 再导入（见第三节） |
| 审核接口 HTML 400 | URL 参数勿直接写中文，用 `reviewer=admin` 或 `--data-urlencode` |
| Postman 报 400 | 看返回 JSON 的 `message` 字段 |
| `项目不存在: 1` | 库中尚无该项目，先 POST 建项目（见例子 4） |
| 排名报 `No enum constant ... RankingLevel.EMPLOYEE,OUTLET` | `level` 一次只能传一个，如 `level=outlet` |
| 网点榜 `items` 为空或比员工榜少 | 正常：支行层级员工的积分不计入 outlet；见例子 6 |
| 指标列表是 `{"content":[]...}` 而其他是 `[]` | 仅指标库用了分页 `Page`，属正常 |

---

## 八、协作提醒
1. 不要把真实 MySQL 密码提交到 Git。

