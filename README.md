# 金融业务绩效管理系统本地启动说明

本文档用于帮助团队成员在本地启动项目，并了解当前本地假数据的机构结构和测试账号。

项目主要包含三个部分：

```text
backend/              后端 Spring Boot 项目
web-admin/            Web 管理端前端项目
wechat-mini-program/  微信小程序端
```

目前主要启动的是：

```text
backend/    后端服务
web-admin/  Web 管理端前端
```

---

## 0. 当前假数据说明

当前假数据按照 MVP 范围设计，暂时不包含总行、省行层级。

当前机构层级为：

```text
市行 → 支行 → 网点 → 员工
```

### 0.1 机构结构

当前假数据包含 5 个机构：

```text
[1] 南京市行（CITY）
├── [2] 鼓楼支行（BRANCH）
│   └── [3] 鼓楼营业室（OUTLET）
└── [4] 玄武支行（BRANCH）
    └── [5] 珠江路网点（OUTLET）
```

对应关系如下：

| 编号 | 机构名称  | 后端 level | 说明 |
|----|-------|----------|---|
| 1  | 南京市行  | CITY     | 市行层级机构 |
| 2  | 鼓楼支行  | BRANCH   | 南京市行下属支行 |
| 3  | 鼓楼营业室 | OUTLET   | 鼓楼支行下属网点 |
| 4  | 玄武支行  | BRANCH   | 南京市行下属支行 |
| 5  | 珠江路网点 | OUTLET   | 玄武支行下属网点 |

---
### 0.2 测试账号说明

导入假数据后，可以使用以下账号登录 Web 管理端。

所有测试账号的密码均为：

```text
123456
```

| 后端 level | 前端角色 | 姓名 | 员工号      | 所属机构 | 密码 | 说明 |
|---|---|---|----------|---|---|---|
| CITY | 市行管理员 | 李家慧 | 93605894 | 南京市行 | 123456 | 用于测试市行管理员权限 |
| BRANCH | 支行管理员 | 侯烨晨 | 40307483 | 鼓楼支行 | 123456 | 用于测试支行管理员权限 |
| BRANCH | 支行负责人 | 方可儿 | 56949775 | 玄武支行 | 123456 | 用于测试支行负责人权限 |
| OUTLET | 网点管理员 | 覃曦南 | 25382232 | 鼓楼营业室 | 123456 | 用于测试网点管理员权限 |
| OUTLET | 网点负责人 | 蒋子涵 | 37865547 | 珠江路网点 | 123456 | 用于测试网点负责人权限 |
| EMPLOYEE | 普通员工 | 倪浩岚 | 11118367 | 珠江路网点 | 123456 | 用于测试柜员登录和每日上报 |
| EMPLOYEE | 普通员工 | 赵紫妍 | 30031808 | 鼓楼营业室 | 123456 | 用于测试客户经理登录和每日上报 |

说明：

```text
CITY     → city_admin
BRANCH   → branch_admin
OUTLET   → outlet_admin
EMPLOYEE → employee
```

---

## 1. 后端启动

## 1. 后端启动

后端使用 Java、Spring Boot、Maven 和 MySQL。

### 1.1 安装需要的软件

如果电脑里已经安装过对应软件，可以跳过该步骤。

#### Mac

先检查是否已经安装：

```bash
java -version
mvn -v
mysql --version
git --version
```

如果没有安装，可以先安装 Homebrew：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

然后安装后端需要的软件：

```bash
brew install openjdk
brew install maven
brew install mysql
brew install git
```

安装完成后，再检查一次：

```bash
java -version
mvn -v
mysql --version
git --version
```

#### Windows

需要安装以下软件：

```text
Java JDK 17 或以上
Maven
MySQL
Git
IntelliJ IDEA
```

安装完成后，在 PowerShell 或命令行里检查：

```bash
java -version
mvn -v
mysql --version
git --version
```

如果命令无法识别，通常是环境变量没有配置好。

---

### 1.2 创建数据库

本项目本地数据库名为：

```text
stage_one
```

进入 MySQL：

```bash
mysql -u root -p
```

创建数据库：

```sql
CREATE DATABASE IF NOT EXISTS stage_one DEFAULT CHARACTER SET utf8mb4;
```

退出 MySQL：

```sql
exit;
```

---

### 1.3 配置数据库密码

后端数据库配置文件位置：

```text
backend/src/main/resources/application.properties
```

当前项目通过环境变量读取 MySQL 密码：

```properties
spring.datasource.password=${DB_PASSWORD}
```

所以本地需要配置 `DB_PASSWORD`。

#### Mac

临时配置：

```bash
export DB_PASSWORD=你的MySQL密码
```

如果希望每次打开终端都自动生效，可以写入 `~/.zshrc`：

```bash
echo 'export DB_PASSWORD=你的MySQL密码' >> ~/.zshrc
source ~/.zshrc
```

#### Windows

PowerShell 临时配置：

```powershell
$env:DB_PASSWORD="你的MySQL密码"
```

也可以在系统环境变量里新增：

```text
变量名：DB_PASSWORD
变量值：你的MySQL密码
```

配置完成后，建议重新打开终端或 IntelliJ IDEA。

---

### 1.4 启动后端

进入后端目录：

```bash
cd backend
```

启动后端：

```bash
mvn spring-boot:run
```

后端默认运行在：

```text
http://localhost:8081
```

---

## 2. 前端启动

前端使用 Vue 3、Vite、Node.js 和 npm。

### 2.1 安装需要的软件

如果电脑里已经安装过对应软件，可以跳过该步骤。

#### Mac

先检查是否已经安装：

```bash
node -v
npm -v
```

如果没有安装：

```bash
brew install node
```

安装完成后，再检查一次：

```bash
node -v
npm -v
```

#### Windows

需要安装以下软件：

```text
Node.js
VS Code 或 WebStorm
```

安装 Node.js 后会自带 npm。

安装完成后，在 PowerShell 或命令行里检查：

```bash
node -v
npm -v
```

---

### 2.2 启动 Web 管理端

进入前端目录：

```bash
cd web-admin
```

第一次启动前需要安装依赖：

```bash
npm install
```

之后启动前端：

```bash
npm run dev
```

前端默认运行在：

```text
http://localhost:5173
```

浏览器打开：

```text
http://localhost:5173/login
```

---

## 3. 导入假数据

假数据 SQL 文件位于：

```text
database/
```

当前需要按以下顺序导入：

```bash
mysql -u root -p stage_one < database/mock_organization_data.sql
mysql -u root -p stage_one < database/mock_employee_data.sql
mysql -u root -p stage_one < database/mock_user_account_data.sql
```

导入顺序不要调换：

```text
1. mock_organization_data.sql
2. mock_employee_data.sql
3. mock_user_account_data.sql
```

原因是：

```text
员工数据依赖机构数据
登录账号数据依赖员工数据
```

---
