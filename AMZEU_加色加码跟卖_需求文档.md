# AMZEU-AI 加色加码跟卖 需求文档

> 来源：https://www.kdocs.cn/l/csWrfDljbvZM
> 整理日期：2026-03-12

---

## 整体逻辑

每个国家需要下载两类输入文件处理后生成加色加码输出表：

- **All Listings Report (Custom)** × 1 张（需求：每天早上 9 点 RPA 自动跑流程下载，覆盖前一天）
- **Category Listings Report** × 若干张（视国家而定）

### 各国输入文件张数

| 国家 | All Listings Report (Custom) | Category Listings Report |
|------|------------------------------|--------------------------|
| UK   | 1 张 | 3 张 |
| FR   | 1 张 | 2 张 |
| DE   | 1 张 | 2 张 |
| IT   | 1 张 | 2 张 |
| ES   | 1 张 | 2 张 |

---

## 补色补码模板

每个国家使用各自的输出模板：

| 国家 | 模板名称 |
|------|---------|
| UK   | UK补色补码模板 |
| FR   | FR补色模板 |
| DE   | DE补色模板 |
| IT   | IT补色模板 |
| ES   | ES上新模板 |

---

## 必填字段细节梳理

表头说明：
- **输出表**：Category Listings Report 中的字段名
- **映射表**：All Listings Report (Custom) 中对应字段名
- **调整字段**：示例值
- **特殊字段（Y）**：黄色标记，需在加色加码时调整
- **调整逻辑**：处理方式
- **映射表来源**：数据来源

| 输出表字段 | 映射表字段 | 示例值 | 需调整(Y) | 调整逻辑 | 映射表来源 |
|-----------|-----------|--------|-----------|---------|-----------|
| Product Type | Product Type | dress | — | 保留（映射） | Template |
| Seller SKU | SKU | ES80026SG04-UK1 | Y | 颜色/尺码变更 | Template |
| Brand Name | Brand Name | Ever-Pretty | — | 保留（映射） | Template |
| Product Name | Item Name | Ever-Pretty Women's Maxi Bridesmaid Dress ... Sage Green 8UK | Y | 颜色/尺码变更 | Template |
| Outer Material Type | — | Synthetic | — | 保留（映射） | Template |
| Colour Map | Colour Map | Green | Y | 更换 | 颜色映射关系 |
| Colour | Colour | Sage Green | Y | 更换 | 颜色映射关系 |
| Size | — | 8 | Y | 更换 | 尺码映射关系 |
| Occasion description | Lifestyle | Evening | — | 保留（映射） | Template |
| Style Name | Style | A-Line | — | 保留（映射） | Template |
| Neck Style | Neck Style | V-Neck | — | 保留（映射） | Template |
| Department | Department Name | Women | — | 保留（映射） | Template |
| Supply Type | — | Fashion | — | 固定 | — |
| Size Map | — | 8 | Y | 更换 | 尺码映射关系 |
| Item Length | Item Length Description | Maxi | — | 保留（映射） | Template |
| Adult Flag | — | No | — | 固定 | — |
| Country/Region Of Origin | — | China | — | 固定 | — |
| fabric_type | Fabric Type | Chiffon | — | 保留（映射） | Template |
| standard_price | Your Price GBP (Sell on Amazon, UK) | 62.99 | — | 固定 | — |
| quantity | — | 2 | — | 固定 | — |
| target_gender | Target Gender | Female | — | 固定 | — |
| age_range_description | Age Range Description | Adult | — | 固定 | — |
| apparel_size_system | Apparel Size System | UK | — | 固定 | — |
| apparel_size_class | Apparel Size Class | Numeric | — | 固定 | — |
| apparel_size | Apparel Size Value | 8 | Y | 更换 | 尺码映射关系 |
| Apparel Size Body Type | Apparel Size Body Type | Regular | — | 固定 | — |
| Apparel Size Height Type | Apparel Size Height Type | Regular | — | 固定 | — |
| main_image_url | — | https://eppic.s3.amazonaws.com/ES80026SG-L.jpg | Y | 图片链接替换：尾缀 1–5；尺码图: EG02088-S-UK | — |
| Other Image Url1 | — | https://eppic.s3.amazonaws.com/ES80026SG-L.jpg | Y | 同上 | — |
| Other Image Url2 | — | https://eppic.s3.amazonaws.com/ES80026SG-L5.jpg | Y | 同上 | — |
| Other Image Url3 | — | https://eppic.s3.amazonaws.com/ES80026SG-L3.jpg | Y | 同上 | — |
| Other Image Url4 | — | https://eppic.s3.amazonaws.com/ES80026SG-L4.jpg | Y | 同上 | — |
| Other Image Url5 | — | https://eppic.s3.amazonaws.com/ES80026-S-UK.jpg | Y | 同上 | — |
| Parentage | — | Child | — | 固定 | — |
| Parent SKU | Parent SKU | ES80026-UK1 | — | 保留 | Template |
| Relationship Type | — | Variation | — | 固定 | — |
| Variation Theme | — | SizeName-ColorName | — | 固定 | — |
| Update Delete | — | Update | — | 固定 | — |
| Product Description | Product Description | — | — | 保留（映射） | Template |
| Recommended Browse Nodes | Recommended Browse Nodes | 13623308031 | — | "Fashion > Women > Clothing > Dresses > Evening Cocktail" → 13623308031；"Fashion > Women > Clothing > Dresses > Cocktail" → 13623305031 | Template |
| Product Care Instructions | Care Instructions | Dress Care: Hand wash in cold water. | — | 保留（映射） | Template |
| Model Name | Model Name | ES80026SG04-UK1 | Y | 颜色/尺码变更 | Template |
| Model Number | Model Number | ES80026SG04-UK1 | Y | 颜色/尺码变更 | Template |
| Manufacturer Part Number | Model Number | ES80026SG04-UK1 | Y | 颜色/尺码变更 | Template |
| Search Terms | generic_keyword[marketplace_id=A1F83G8C2ARO7P][language_tag=en_GB]#1.value | [关键词] | Y | 删除与所补颜色不相关的部分，更换成前所补颜色 | Template |
| bullet_point1 | bullet_point[marketplace_id=A1F83G8C2ARO7P][language_tag=en_GB]#1.value | — | — | 保留（映射） | Template |
| bullet_point2 | bullet_point[marketplace_id=...#2.value | — | — | 保留（映射） | Template |
| bullet_point3 | bullet_point[marketplace_id=...#3.value | — | — | 保留（映射） | Template |
| bullet_point4 | bullet_point[marketplace_id=...#4.value | — | — | 保留（映射） | Template |
| bullet_point5 | bullet_point[marketplace_id=...#5.value | — | — | 保留（映射） | Template |
| Sleeve Type | Sleeve Type | sleeveless | — | 保留（映射） | Template |
| Package Length | Item Package Length | 13 | — | 保留（映射） | Template |
| Package Height | Item Package Height | 1 | — | 保留（映射） | Template |
| Package Height (Weight) | Item Package Weight | 470.00 | — | 保留（映射） | Template |
| Package Weight Unit Of Measure | Item Package Weight Unit | GR | — | 保留（映射） | Template |
| Package Dimensions Unit Of Measure | Package Height Unit | IN | — | 保留（映射） | Template |
| Is this product a battery or does it utilise batteries? | — | No | — | 固定 | Template |
| Batteries are Included | — | No | — | 固定 | Template |
| Condition Type | — | New | — | 固定 | Template |
| Currency | — | GBP | — | 固定（按国家） | Template |
| List Price with Tax for Display | — | 72.99 | Y | = Your Price GBP (standard_price) + 10 | — |

---

## 尺码逻辑

**Size Map = SKU 中的尺码数字 + 4**

例：SKU 中尺码为 `04` → Size Map = `8`

---

## 颜色管理

每个国家有各自的颜色和尺码规范表：

| 国家 | 规范表 |
|------|--------|
| UK   | UK-Color和Size规范表 |
| FR   | FR-Color和Size规范表 |
| DE   | DE Color和Size的规范表 |
| IT   | IT Color和Size规范表 |
| ES   | ES Color和Size的规范表 |

---

## SKU 格式规则

支持两种产品代码位数：

- **7 位产品代码**：`EG02230` + `LV` + `14` + `-UK1`（产品 + 颜色 + 尺码 + 后缀）
- **8 位产品代码**：`EE0164A` + `BD` + `14` + `-UK1`

后缀示例：`-UK1`、`-DE`、`-CO` 等（按国家/站点区分）

---

## 跟卖

（待补充）

---

## 历史承接文档梳理（参考 US 版实现）

1. **颜色代码映射管理**
   - 维护颜色代码到颜色名称的映射（如 `LV` → Lavender，`BK` → Black）
   - 支持颜色映射的增删改查、批量更新、搜索功能
   - 通过 `colorMapping.json` 集中管理所有颜色定义

2. **Excel 自动化处理**

3. **SKU 解析规则**
   - 支持 7 位和 8 位两种产品代码格式
   - 解析：产品代码 + 颜色码 + 尺码 + 后缀

4. **多模板支持**
   - 多国家模板
   - 不同模板有不同的列位置配置和图片命名规则

5. **智能数据填充**
   自动填充以下字段：
   - SKU、Style Number、MPN（保持一致）
   - Parent SKU（产品代码 + 后缀）
   - 颜色名称和 Color Map 分类
   - 尺码信息（Size、Size Value、Size Map）
   - 产品图片 URL（主图、附图、色卡图）
   - Product Name（自动替换颜色和尺码）
   - Key Features、Generic Keyword（从原始数据复制）

6. **多后缀支持**
   - 自动识别原始数据中的所有后缀（如 `-UK1`、`-DE`、`-CO` 等）
   - 为每个后缀生成独立的 Sheet
   - 保持后缀相关的产品描述一致性

---

## 与 US BU2Ama 的主要差异

| 维度 | US (BU2Ama) | EU (本项目) |
|------|------------|------------|
| 站点/店铺 | EP / DM / PZ | UK / FR / DE / IT / ES |
| 模板 | 3个 US 模板 (.xlsm) | 5个 EU 国家模板 |
| 输入文件 | All Listings Report | All Listings Report (Custom) + Category Listings Report（多张） |
| SKU 后缀 | -USA / -PL / -DA | -UK1 / -DE / -IT / -ES 等 |
| 图片命名 | -L1 / -PL1 | -L / -L5 / -L3 / -L4 / -S-UK |
| 尺码逻辑 | US sizing | UK sizing（SKU 尺码 + 4） |
| 货币 | USD | GBP（UK）/ EUR（FR/DE/IT/ES） |
| Variation Theme | Size/Color | SizeName-ColorName |
| marketplace_id | ATVPDKIKX0DER | A1F83G8C2ARO7P（UK）等 |
