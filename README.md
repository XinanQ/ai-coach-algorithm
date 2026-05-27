# financial-performance-team
# 金融绩效管理系统

本仓库用于统一管理金融绩效管理系统项目的后端、Web 后台、小程序、数据库脚本和技术文档。

## 技术栈

- 后端：Spring Boot
- Web 后台：Vue + Element Plus
- 微信小程序：待确认
- 数据库：MySQL

## 目录结构

- `backend/`：后端服务
- `web-admin/`：后台管理系统
- `wechat-mini-program/`：微信小程序端
- `database/`：数据库初始化脚本、迁移脚本、测试数据

## 分支管理规则

本项目用 `main`、`dev` 和 `feature/*` 三类分支。

- `main`：稳定分支，用于保存已确认可运行的版本，不直接在该分支上开发。
- `dev`：开发集成分支，用于合并各成员完成的功能并进行联调。
- `feature/*`：功能开发分支，每个新功能从 `dev` 创建，完成后合并回 `dev`。

分支命名示例：

```bash
feature/frontend-login-page
feature/backend-user-module
feature/miniprogram-report-page
