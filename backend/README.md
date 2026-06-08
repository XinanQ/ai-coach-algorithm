# StageOneCode2 使用说明

**版本：** V2.2  
**日期：** 2026-06-03  
**负责人：** 李家慧、蒋子涵  
**阶段：** M1 基础闭环版（后台 API，持续开发中）

---

## 一、项目简介

Spring Boot 3.1.5 + Java 21 + MySQL 的后端服务，提供机构、员工、项目、指标库、项目挂指标、积分规则/日志、业绩上报等管理端 API（部分模块仅表结构，API 待开发）。

- 服务默认端口：**8081**
- 数据库名：**stage_one**
- 表由 JPA **自动建表**（开发环境无需手写建表 SQL）
- 代码按**业务模块**分文件夹存放：每个业务一块，里面通常有「实体类、数据库访问、业务逻辑、对外接口」四层


---

## 二、目录结构

```
StageOneCode2/
├── README.md                 # 本说明（怎么装环境、启动、测接口）
├── pom.xml                   # 项目依赖配置（Maven）
├── mvnw / mvnw.cmd           # 命令行启动用的脚本
└── src/main/
    ├── java/com/
    │   ├── bank/stageonecode/
    │   │   └── StageOneCodeApplication.java   # 程序入口，在 IDEA 里点 Run 就跑这个
    │   ├── organization/      # 机构管理：市行/支行/网点的增删改查、树形结构
    │   ├── employee/          # 员工管理：员工信息维护、Excel 批量导入导出
    │   ├── project/           # 项目管理；含 ProjectIndicator（项目挂指标、积分标准）
    │   ├── indicator/         # 指标管理：指标库（存款、理财等）、目标分解、催办
    │   │   └── dto/           # 指标接口专用的入参/出参格式（给前端 JSON 用）
    │   ├── points/            # 积分规则 points_rules、积分日志 points_logs（实体已建）
    │   ├── task/              # 系统任务记录：分解指标、催办时产生的待办记录
    │   ├── performance/       # 业绩上报 task_results：项目/指标/网点/附件等字段
    │   └── common/            # 公共组件：统一错误提示格式（如「编码已存在」）
    └── resources/
        └── application.properties   # 数据库账号密码、端口 8081 等配置
```
### 文件夹 ↔ 数据库表（对照）

| 代码文件夹 | 数据库表 | 通俗说明 |
|------------|----------|----------|
| `organization` | `organizations` | 存各级机构（市行、支行、网点） |
| `employee` | `employees` | 存员工姓名、邮箱、所属网点等 |
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
spring.datasource.password=你的MySQL密码
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
| 员工列表 | http://localhost:8081/api/admin/employees |
| 项目列表 | http://localhost:8081/api/admin/projects |
| 指标分页列表 | http://localhost:8081/api/admin/indicators?page=0&size=10 |
| 待审核上报（默认只查 PENDING） | http://localhost:8081/api/admin/reports |

> 指标列表带中文筛选参数时，浏览器可能 400，请用 Postman 或第六节 curl。

### 3. MySQL验证表（终端）

```bash
mysql -u root -p
```

```sql
USE stage_one;
SHOW TABLES;   -- 应有 9 张表（见上一节对照）
DESC indicators;  --应有indicator表具体
```

> 开发配置 `ddl-auto=create`：**每次重启会清空表数据**，属正常现象。

---

## 五、目前进度

| 模块 | 路径前缀 | 状态 | 说明 |
|------|----------|------|------|
| 指标库 | `/api/admin/indicators` | **较完整** | 增删改查、分页、启用停用 |
| 机构 | `/api/admin/organizations` | 基础可用 | 增删改查、树、按层级查 |
| 员工 | `/api/admin/employees` | 基础可用 | 增删改查、Excel 导入导出 |
| 项目 | `/api/admin/projects` | 基础可用 | 增删改查、改状态 |
| 业绩上报 | `/api/admin/reports` | 基础可用 | 提交、列表、通过/驳回；表已支持项目/指标/网点/附件字段 |
| 项目挂指标 | `project_indicators` | **表已建，API 未做** | 1.1.3.4 |
| 积分规则 / 日志 | `points_rules` / `points_logs` | **表已建，API/引擎未做** | 1.1.4 |
| 排名 | — | **未做** | 可先查 points_logs 汇总 |
| 喜报 / 低业绩 / 小程序登录 | — | **未做** | 功能需求第一阶段 Out 或后续 |

接口细节以代码为准；本文只写**怎么跑**和**最简单的测法**。

---

## 六、简单测试例子（终端复制即用）

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

### 例子 4：提交一条上报（POST，新字段可选）

先确保已有项目 id=1、指标 id=1、网点 id=4、员工 id=1（没有则先按上文创建）：

```bash
curl -X POST "http://localhost:8081/api/admin/reports/submit" \
  -H "Content-Type: application/json" \
  -d '{"projectId":1,"indicatorId":1,"organizationId":4,"submitter":"张三","submitterId":1,"reportDate":"2026-05-18","result":"85","taskId":1}'
```

`projectId`、`indicatorId`、`organizationId`、`attachmentUrl` 可不传（为 null），旧测法仍可用。

### （可选）查 MySQL 里有没有写进去

```bash
mysql -u root -p -e "USE stage_one; SELECT id,name,code,enabled FROM indicators; SELECT id,name,code,level FROM organizations;"
```

输入 MySQL 密码后会打印表里的数据。

> Mac 终端直接用上面命令即可。Windows 若 `\` 换行报错，改成一行，或用 Git Bash。

---

## 七、常见问题

| 现象 | 处理 |
|------|------|
| 数据库连不上 | 检查 `application.properties` 密码、MySQL 是否启动 |
| 8081 端口占用 | 关掉旧进程，或改 `server.port` |
| 重启后数据没了 | `ddl-auto=create` 会重建表 |
| Postman 报 400 | 看返回 JSON 的 `message` 字段 |

---

## 八、协作提醒
1. 不要把真实 MySQL 密码提交到 Git。

