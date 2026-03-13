# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow

- **Claude**: 负责代码 review、架构决策、任务规划，以及与 Codex 讨论方案后敲定最终实现路径
- **Codex**: 负责代码实现与执行
- **方案讨论**: Claude 提出方案后需通过 Codex skill 与 Codex 交流确认，再敲定最终方案
- **并行开发**: 对于独立任务，Claude 可同时开启多个 Codex session 并行执行，使用 `parallel-codex-sessions` 或 `subagent-driven-development` skill

## ⚠️ 严禁修改参考项目

**绝对不能修改 `/Users/melodylu/PycharmProjects/BU2Ama/` 下的任何文件。**

BU2Ama 是正在生产使用的美国站加色加码项目，本项目（Bu2_ama_ep）是欧洲站的全新实现。

允许的操作：
- ✅ **只读参考** BU2Ama 的代码结构、逻辑思路、设计模式
- ✅ 在本项目中借鉴并重新实现类似功能

禁止的操作：
- ❌ 修改 BU2Ama 的任何源文件
- ❌ 在 BU2Ama 目录下新建文件
- ❌ 将本项目的改动提交到 BU2Ama

## Project Overview

**AMZEU-AI 加色加码跟卖** — 欧洲亚马逊多站点加色加码系统。

支持国家：UK / FR / DE / IT / ES

核心功能：
- 读取 All Listings Report (Custom) + Category Listings Report，生成各国补色补码模板
- 支持 7 位和 8 位产品代码的 SKU 解析（产品码 + 颜色码 + 尺码 + 国家后缀）
- 每国独立的 Color/Size 规范表、模板、货币、marketplace_id
- 尺码逻辑：Size Map = SKU 尺码 + 4（以 UK 为基准）
- 跟卖功能（二期）

需求详细说明见：[AMZEU_加色加码跟卖_需求文档.md](./AMZEU_加色加码跟卖_需求文档.md)

## Architecture（目录结构规划）

```text
backend/
  app/
    api/                # 路由层
    core/
      parsers/          # SKU 解析（支持 7/8 位）
      indexers/         # All Listings + Category Listings 索引
      processors/       # 加色加码处理器、跟卖处理器
      profiles/         # 每国配置（UK/FR/DE/IT/ES）
    models/             # Pydantic 模型
    services/           # template_service, mapping_service
    config.py           # 国家注册表
    main.py             # FastAPI 入口
frontend/
  src/
    components/
    services/
    store/
    types/
data/                   # colorMapping.json 等
templates/              # 各国 Excel 模板
backend/results/        # 处理结果输出
backend/uploads/        # 上传的源文件
```

## Technology Stack

### Backend
- Python 3.11+
- FastAPI
- openpyxl
- Pydantic
- Uvicorn

### Frontend
- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Query
- Zustand
- Axios

## Key Design Decisions

1. **配置驱动多国家**：用 `CountryProfile` 枚举 + 配置注册表管理5个国家的差异，避免 `if country == ...` 散落各处
2. **输入模型差异**：EU 每国需要 1 张 All Listings Report + 2-3 张 Category Listings Report（与 US 单文件不同）
3. **SKU 解析**：按后缀先切，再从尾部切 2 位颜色 + 2 位尺码，剩余为产品码（7 或 8 位）
4. **先做 UK 打通**，验证端到端流程后再扩展其他4个国家
5. **跟卖为二期**，需求文档中该部分仍为空白，暂不实现
