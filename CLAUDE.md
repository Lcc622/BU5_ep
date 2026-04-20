# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Workflow

- **Claude**: 负责代码 review、架构决策、任务规划，以及与 Codex 讨论方案后敲定最终实现路径
- **Codex**: 负责代码实现与执行
- **方案讨论**: Claude 提出方案后需通过 Codex skill 与 Codex 交流确认，再敲定最终方案
- **并行开发**: 对于独立任务，Claude 可同时开启多个 Codex session 并行执行，使用 `parallel-codex-sessions` 或 `subagent-driven-development` skill

## 严禁修改参考项目

**绝对不能修改 `/Users/melodylu/PycharmProjects/BU2Ama/` 下的任何文件。**

BU2Ama 是生产环境美国站项目，本项目（Bu5_ama_ep）是欧洲站独立实现。可只读参考 BU2Ama 的设计模式，但禁止修改、新建、提交任何改动到 BU2Ama。

## Project Overview

**AMZEU-AI 加色加码跟卖** — 欧洲亚马逊多站点加色加码系统，支持 UK / FR / DE / IT / ES。

核心功能：
- 读取 All Listings Report + Category Listings Report，生成各国补色补码模板
- 支持 7/8 位产品代码的 SKU 解析（产品码 + 颜色码 + 尺码 + 国家后缀）
- 每国独立的模板、货币、marketplace_id、尺码偏移
- 跟卖功能（二期）

需求详细说明见：[AMZEU_加色加码跟卖_需求文档.md](./AMZEU_加色加码跟卖_需求文档.md)

## Commands

### Backend
```bash
# Run dev server (auto-reload)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests (需要先安装 pytest)
PYTHONPATH=backend python -m pytest backend/tests/ -x -q

# Run single test file
PYTHONPATH=backend python -m pytest backend/tests/test_add_color_size_processor.py -x -q

# Run single test method
PYTHONPATH=backend python -m pytest backend/tests/test_add_color_size_processor.py::TestAddColorSizeProcessor::test_method_name -x -q
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Dev server at localhost:5180, proxies /api → localhost:8002
npm run build
```

### Docker (full stack)
```bash
docker-compose up   # Backend: 8002, Frontend: 5180
```

## Architecture — Processing Pipeline

```
All Listings (TSV) + Category Listings (XLSM)
        ↓
  ListingIndexer.build_index()
        ↓
  Index {by_sku, by_prefix} — each record has all_listings_data + category_data
        ↓
  AddColorSizeProcessor._process_core() / FollowSellProcessor.process()
        ↓
  rows_by_suffix: {suffix → [parent_row, child_row, child_row, ...]}
        ↓
  _write_workbook() → copies country template, fills via column mapping
        ↓
  backend/results/{country}-{product}-补色.xlsx
```

### Key Pipeline Components

**ListingIndexer** (`core/indexers/listing_indexer.py`):
- `_find_category_sheet()` — 选择 XLSM 中的数据 sheet。EU 各国 sheet 名不同：FR=`Modèle`, DE=`Vorlage`, IT=`Modello`, ES=`Plantilla`, UK=`Template`。通过 `_TEMPLATE_SHEET_NAMES` 优先匹配这些名字
- Machine header row 通常包含 `contribution_sku#1.value`，以此定位表头行
- `_simplified_machine_header_key()` 将 `product_type#1.value` 简化为 `product_type` 作为额外 key

**AddColorSizeProcessor** (`core/processors/add_color_size_processor.py`):
- 每个 prefix (产品码) 生成 1 个 parent row + N 个 child rows (颜色 × 尺码)
- Parent row: 只有基本字段 + ASIN (`external_product_id`)
- Child row: 完整字段，但 **不写 ASIN**（Amazon 自动生成子 ASIN）
- `DISPLAY_TO_MACHINE` dict 将显示名 (`"Product Type"`) 映射到机器名 (`"feed_product_type"`)，确保 row 同时有两种 key
- `COPY_FIELD_ALIASES` 定义 category_data 字段的所有可能别名（含 marketplace_id 限定格式）

**Template Writing** (`_write_workbook` + `_resolve_template_col_idx`):
- 复制国家模板 XLSM，读取 display header row (row 2) + machine header row (row 3)
- 写入时对每个 row key 依次尝试：精确匹配 → 大小写规范化 → fuzzy 匹配（`_` `-` `/` 替换为空格）
- 保留模板样式（颜色、字体、边框）

**FollowSellProcessor** (`core/processors/follow_sell_processor.py`):
- 通过 `新老款映射信息(1).xlsx` 将新产品码映射到老产品码
- 在老 SKU 数据基础上生成新 SKU 行，价格 = 老价格 + 0.1
- DE/IT/ES 需要从 FR All Listings 查找 ASIN

## Country Configuration

`config.py` 中 `COUNTRY_PROFILES` 字典管理各国差异：
- `size_offset`: UK=4, FR/DE/IT/ES=32 (SKU size + offset = 模板尺码)
- `template_file`: 各国独立的 XLSM 模板文件（在 `templates/` 目录）
- `language_tag`: 影响颜色名本地化 (`en_GB`, `fr_FR`, `de_DE`, `it_IT`, `es_ES`)
- UK suffix 过滤只保留 `-UK*`，EU 国家优先无后缀行

处理器中的国家差异通过专用方法封装：
- `_build_country_static_fields()` — 各国固定字段值
- `_update_delete_value()` — FR=`Actualisation`, DE=`Aktualisierung`, IT=`Aggiorna`
- `_condition_type_value()` — FR=`Neuf`, DE=`Neu`

## 测试规范

- **禁止使用 mock 数据**：测试必须使用真实的 SKU、真实的文件结构和真实的字段值
- SKU 格式须符合实际业务规则（如 `ES01955BD04`、`EG02088BK04-UK1`）
- 需要文件的测试，使用 `backend/uploads/` 下的真实文件或 `backend/tests/fixtures/` 的真实格式数据
- **每次改动必须用真实 SKU 端到端验证**：修改处理器、索引器或模板后，必须用 `backend/uploads/` 中的真实文件构建 index，调用处理器生成输出，检查关键字段值正确后才算修复完成

## Key Paths

- `templates/` — 各国 XLSM 模板（FR补色模板.xlsm 等）
- `backend/uploads/` — 上传的源文件（All Listings + Category Reports）
- `backend/results/` — 处理结果输出
- `backend/app/data/colorMapping.json` — 颜色码映射表（BK→Black/Noir/Schwarz 等）
