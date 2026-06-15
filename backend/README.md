# StageOneCode3 使用说明
**❗❗️现在是 update，重启后数据一般会一直在 ，第六节里那些 POST 新建 的 curl 不必再跑，否则会在库里又多一批测试数据，和模拟数据混在一起**

**版本：** V3.1  
**日期：** 2026-06-11  
**负责人：** 李家慧、蒋子涵  
**阶段：** M1 基础闭环版（后台 API，持续开发中）

---

## 一、项目简介

Spring Boot 3.1.5 + Java 21 + MySQL 的后端服务，提供机构、员工、登录、项目、指标库、项目挂指标、积分规则/日志、业绩上报等管理端 API（部分模块仅表结构，API 待开发）。

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
    │   ├── auth/                  # 登录：工号 + 密码（BCrypt）
    │   │   └── dto/               # LoginRequest / LoginResponse
    │   ├── project/               # 项目管理；含项目挂指标、积分标准（ProjectIndicator）
    │   │   └── dto/               # 项目挂指标接口入参/出参
    │   ├── indicator/             # 指标管理：指标库（存款、理财等）、目标分解、催办
    │   │   └── dto/               # 指标接口入参/出参
    │   ├── points/                # 积分规则 points_rules、积分日志 points_logs（实体已建）
    │   ├── task/                  # 系统任务记录：分解指标、催办时产生的待办记录
    │   ├── performance/           # 业绩上报：员工每日填报、管理员审核通过/驳回
    │   └── common/                # 公共组件：统一错误提示格式（如「编码已存在」）
    └── resources/
        └── application.properties   # 数据库账号密码、端口 8081 等配置
```
### 文件夹 ↔ 数据库表（对照）

| 代码文件夹 | 数据库表 | 通俗说明 |
|------------|----------|----------|
| `organization` | `organizations` | 存各级机构（市行、支行、网点） |
| `employee` | `employees` | 存员工姓名、邮箱、所属网点等 |
| `auth` | `user_account` | 登录账号（工号、密码哈希、关联 employee_id） |
| `project` | `projects` | 存一次考核/营销活动的项目信息 |
| `indicator` | `indicators` | 存业务指标定义（如「定期存款」「贷记卡」） |
| `task` | `tasks` | 存分解、催办产生的系统任务 |
| `performance` | `task_results` | 每日上报与审核；含 project_id、indicator_id、organization_id、attachment_url |
| `project`（实体 `ProjectIndicator`） | `project_indicators` | 项目挂指标、积分标准（V1 积分表） |
| `points` | `points_rules` | 积分规则配置（JSON、生效期） |
| `points` | `points_logs` | 积分变动日志 |

---

## 三、环境准备

1. **JDK 21**
2. **MySQL 8.x**（安装后保持服务运行）
3. **IntelliJ IDEA**（推荐）
4. 可选：**Postman / Apifox**（测 API）、**浏览器**（GET 接口）

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
cd /Users/amanda/Desktop/dev-backup/database
mysql -u root -p stage_one < mock_organization_data.sql
mysql -u root -p stage_one < mock_employee_data.sql
mysql -u root -p stage_one < mock_user_account_data.sql
```

若报 `Duplicate entry`，先清空三张表再导入：`user_account` → `employees` → `organizations`。  
测试登录密码统一为 **`123456`**（如工号 `93605894`）。

---

## 四、怎么确认跑通了
### 1. 启动

IDEA 打开含 `pom.xml` 的目录 → JDK 21 → 运行 `StageOneCodeApplication`  
看到 **`Started StageOneCodeApplication`** 即成功。

### 2. 浏览器验证

**服务启动后**，用浏览器打开下面链接。空库时多为 `[]` 或分页 `{"content":[]...}`，也算正常；有数据后会看到 JSON。

#### 基础（建议都点一遍）

| 说明 | 地址 |
|------|------|
| 机构列表 | http://localhost:8081/api/admin/organizations |
| 机构树 | http://localhost:8081/api/admin/organizations/tree |
| 员工列表（导入后约 100 条） | http://localhost:8081/api/admin/employees |
| 项目列表 | http://localhost:8081/api/admin/projects |
| 项目挂指标列表（需先有项目、指标数据） | http://localhost:8081/api/admin/projects/1/indicators |
| 指标分页列表 | http://localhost:8081/api/admin/indicators?page=0&size=10 |
| 上报列表（全部） | http://localhost:8081/api/admin/reports |
| 待审核上报 | http://localhost:8081/api/admin/reports?status=PENDING |

> 指标列表带中文筛选参数时，浏览器可能 400，请用 Postman 或第六节 curl。  
> 项目挂指标空库直接访问可能返回 `项目不存在: 1`，请先按第六节例子 4 用 curl 建数据。

### 3. MySQL验证表（终端）

```bash
mysql -u root -p
```

```sql
USE stage_one;
SHOW TABLES;   -- 应有 10 张表（含 user_account）
DESC indicators;
```

> 开发配置 `ddl-auto=update`：**重启一般保留数据**；改回 `create` 会每次重建表并清空。

---

## 五、目前进度

| 模块 | 路径前缀 | 状态 | 说明 |
|------|----------|----|------|
| 指标库 | `/api/admin/indicators` | 较完整 | 增删改查、分页、启用停用 |
| 机构 | `/api/admin/organizations` | 较完整 | 增删改查、树、按层级查；DTO 入参/出参 |
| 员工 | `/api/admin/employees` | 较完整 | 增删改查、Excel 导入导出；DTO 入参/出参 |
| 登录 | `/api/auth/login` | 基础可用 | 工号 + 密码登录，返回员工信息 |
| 项目 | `/api/admin/projects` | 基础可用 | 增删改查、改状态 |
| 业绩上报 | `/api/admin/reports` | 基础可用 | 提交/列表/详情/改删、审核通过驳回；新字段可选 |
| 项目挂指标 | `/api/admin/projects/{projectId}/indicators` | 较完整 | 增删改查、积分标准、重复挂接校验 |
| 积分规则 / 日志 | `points_rules` / `points_logs` | 表已建，API/引擎未做 | 1.1.4 |
| 排名 | — | **未做** | 可先查 points_logs 汇总 |
| 喜报 / 低业绩 / 小程序登录 | — | 未做 | 功能需求第一阶段 Out 或后续 |

接口细节以代码为准；本文只写**怎么跑**和**最简单的测法**。

---

## 六、简单测试例子（终端复制即用）
**❗️❗️现在是 update，重启后数据一般会一直在 ，第六节里那些 POST 新建 的 curl 不必再跑，否则会在库里又多一批测试数据，和模拟数据混在一起**

**前提：** 已 Run 启动，控制台有 `Started StageOneCodeApplication`。

基础地址：`http://localhost:8081`

### 例子 1：查指标列表（GET）

```bash
curl "http://localhost:8081/api/admin/indicators?page=0&size=10"
```

浏览器也可以直接打开同一地址。

### 例子 2：新建一条指标（POST）

```bash
curl -X POST "http://localhost:8081/api/admin/indicators" \
  -H "Content-Type: application/json" \
  -d '{"name":"定期存款","code":"DEPOSIT","unit":"万","category":"存款","enabled":true}'
```

成功：返回 JSON，里面有 `"id":1`，HTTP 状态 **201**。

测重复编码（应报错 400）：

```bash
curl -X POST "http://localhost:8081/api/admin/indicators" \
  -H "Content-Type: application/json" \
  -d '{"name":"重复测试","code":"DEPOSIT","unit":"万","enabled":true}'
```

应看到类似：`"message":"指标编码已存在: DEPOSIT"`

### 例子 3：新建市行（POST）

```bash
curl -X POST "http://localhost:8081/api/admin/organizations" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试市行","code":"TEST_CITY","level":"CITY"}'
```

成功：返回 JSON，里面有 `"id":1`，`"level":"CITY"`。

再建支行（`parentId` 改成上一步返回的市行 id，一般是 1）：

```bash
curl -X POST "http://localhost:8081/api/admin/organizations?parentId=1" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试支行","code":"TEST_BRANCH","level":"BRANCH"}'
```

`level` 常用：`CITY` 市行、`BRANCH` 支行、`OUTLET` 网点。

### 例子 4：项目挂指标全流程（1.1.3.4）

**按顺序执行**。若尚无指标，先执行例子 2。

建项目：

```bash
curl -X POST "http://localhost:8081/api/admin/projects" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试项目","startDate":"2026-06-01","endDate":"2026-12-31","reportDeadline":"2026-12-31","status":"DRAFT"}'
```

挂指标（`indicatorId` 用例子 2 返回的 id，一般为 1）：

```bash
curl -X POST "http://localhost:8081/api/admin/projects/1/indicators" \
  -H "Content-Type: application/json" \
  -d '{"indicatorId":1,"unit":"万","pointsStandard":10,"pointsUnit":"分/万","targetValue":100,"sortOrder":1}'
```

查列表（应有 1 条；浏览器也可打开第四节对应地址）：

```bash
curl "http://localhost:8081/api/admin/projects/1/indicators"
```

重复挂接（应 400，`message` 为「该项目已挂接该指标」）：

```bash
curl -X POST "http://localhost:8081/api/admin/projects/1/indicators" \
  -H "Content-Type: application/json" \
  -d '{"indicatorId":1,"pointsStandard":10}'
```

更新积分标准：

```bash
curl -X PUT "http://localhost:8081/api/admin/projects/1/indicators/1" \
  -H "Content-Type: application/json" \
  -d '{"pointsStandard":15,"targetValue":200}'
```

删除挂接（成功无返回体，HTTP **204**）：

```bash
curl -X DELETE "http://localhost:8081/api/admin/projects/1/indicators/1"
```

### 例子 5：提交一条上报（POST，新字段可选）

先确保已有项目 id=1、指标 id=1、网点 id=4、员工 id=1（没有则先按上文创建）：

```bash
curl -X POST "http://localhost:8081/api/admin/reports/submit" \
  -H "Content-Type: application/json" \
  -d '{"projectId":1,"indicatorId":1,"organizationId":4,"submitter":"张三","submitterId":1,"reportDate":"2026-06-10","result":"85"}'
```

`projectId`、`indicatorId`、`organizationId`、`attachmentUrl`、`taskId` 均可不传。提交后状态为 `PENDING`。

审核通过（`id` 换成上一步返回的上报 id；query 用英文，中文需 `--data-urlencode`）：

```bash
curl -X POST "http://localhost:8081/api/admin/reports/1/approve?reviewer=admin&comment=ok"
```

### 例子 6：登录（POST，需先导入 user_account）

```bash
curl -X POST "http://localhost:8081/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"employeeNo":"93605894","password":"123456"}'
```

成功：`"code":200`，`data` 含员工姓名等。`isInProject=false` 的账号会 403。

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
| 数据库连不上 | 检查 `application.properties` 密码、MySQL 是否启动 |
| 8081 端口占用 | 关掉旧进程，或改 `server.port` |
| 重启后数据没了 | 检查是否改回 `ddl-auto=create`；`update` 下一般会保留 |
| 导入 SQL 报 Duplicate entry | 表里已有数据，先 TRUNCATE 再导入（见第三节） |
| 审核接口 HTML 400 | URL 参数勿直接写中文，用 `reviewer=admin` 或 `--data-urlencode` |
| Postman 报 400 | 看返回 JSON 的 `message` 字段 |
| `项目不存在: 1` | 库中尚无该项目，先 POST 建项目（见例子 4） |
| 指标列表是 `{"content":[]...}` 而其他是 `[]` | 仅指标库用了分页 `Page`，属正常 |

---

## 八、协作提醒
1. 不要把真实 MySQL 密码提交到 Git。

