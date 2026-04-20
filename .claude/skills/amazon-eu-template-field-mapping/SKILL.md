---
name: amazon-eu-template-field-mapping
description: |
  Fix for Amazon EU (DE/FR/IT/ES) xlsm flat-file template output being empty even
  when the indexer correctly reads category data. Use when: (1) DE/FR/IT/ES output
  xlsx has empty columns despite category data being indexed, (2) _build_output_row
  returns 40+ non-None values but template columns stay blank, (3) _resolve_template_col_idx
  returns None for keys like "Seller SKU", "Colour", "Product Name", "Update Delete".
  Root cause: English display-name keys don't match DE/FR/IT/ES machine-header keys.
  Also covers Docker TEMPLATES_DIR path fix (PROJECT_ROOT resolves to / in Docker).
author: Claude Code
version: 1.0.0
date: 2026-03-18
---

# Amazon EU Flat-File Template Field Mapping

## Problem

DE/FR/IT/ES output xlsx files have all columns blank. The processor generates
`processed_count > 0` and `_build_output_row` returns a row with 40+ non-None values,
but `_write_workbook` writes nothing to the template columns.

## Root Cause

Two independent bugs:

### Bug 1: Key Name Mismatch

`_build_output_row` uses English display names as dict keys:
```python
"Seller SKU": sku, "Brand Name": ..., "Colour": ..., "Product Name": ..., "Update Delete": "Update"
```

But DE/FR/IT/ES templates (xlsm) have **machine headers in row 3** with snake_case names:
- `item_sku`, `brand_name`, `color_name`, `item_name`, `update_delete`

`_resolve_template_col_idx` only does casefold normalization, so:
- `"seller sku"` ≠ `"item_sku"` → None
- `"colour"` ≠ `"color_name"` → None
- `"product name"` ≠ `"item_name"` → None

### Bug 2: TEMPLATES_DIR Wrong in Docker

```python
PROJECT_ROOT = BASE_DIR.parent   # /app → parent = /
TEMPLATES_DIR = PROJECT_ROOT / "templates"  # = /templates (doesn't exist!)
```

Templates are at `/app/templates/` inside the container.

## Amazon EU Template Structure

All DE/FR/IT/ES xlsm templates (DE补色模板.xlsm, FR补色模板.xlsm, etc.) follow:

| Row | Content |
|-----|---------|
| 1 | Amazon settings metadata (`attributeRow=3&dataRow=4&labelRow=2&...`) |
| 2 | Local-language display headers (German: "Verkäufer-SKU", "Marke", "Update / Löschen") |
| 3 | Machine headers (`item_sku`, `brand_name`, `update_delete`, `feed_product_type`) |
| 4 | Example data row |
| 5+ | Empty (data rows written here) |

The key machine headers and their display-name equivalents:

| Display Name (English) | Machine Header |
|------------------------|----------------|
| Seller SKU | item_sku |
| Product Type | feed_product_type |
| Brand Name | brand_name |
| Update Delete | update_delete |
| Product Name | item_name |
| Colour | color_name |
| Colour Map | color_map |
| Size | size_name |
| Size Map | size_map |
| Department | department_name |
| Item Length | item_length_description |
| Occasion description | lifestyle |
| Model Number | model |
| Parentage | parent_child |
| Country/Region Of Origin | country_of_origin |
| List Price with Tax for Display | list_price_with_tax |
| Product Care Instructions | care_instructions |
| Package Dimensions Unit Of Measure | package_height_unit_of_measure |

Many others match after underscore→space normalization: "Brand Name"↔"brand_name",
"Update Delete"↔"update_delete", "Other Image Url1"↔"other_image_url1".

## Solution

### Fix 1: DISPLAY_TO_MACHINE mapping + fuzzy normalization

**In `add_color_size_processor.py`:**

```python
# Add near ASIN_ALIASES
DISPLAY_TO_MACHINE: dict[str, str] = {
    "Seller SKU": "item_sku",
    "Product Type": "feed_product_type",
    "Colour": "color_name",
    "Colour Map": "color_map",
    "Size": "size_name",
    "Product Name": "item_name",
    "Department": "department_name",
    "Item Length": "item_length_description",
    "Occasion description": "lifestyle",
    "Package Dimensions Unit Of Measure": "package_height_unit_of_measure",
    "Model Number": "model",
    "Parentage": "parent_child",
    "Country/Region Of Origin": "country_of_origin",
    "List Price with Tax for Display": "list_price_with_tax",
    "Product Care Instructions": "care_instructions",
}

# At END of _build_output_row, before return:
for display_key, machine_key in DISPLAY_TO_MACHINE.items():
    if display_key in row and machine_key not in row:
        row[machine_key] = row[display_key]
```

**Add fuzzy normalization to `_resolve_template_col_idx`** (5th fallback):
```python
def _normalize_key_fuzzy(self, value: Any) -> str:
    return re.sub(r"[_\-/]+", " ", self._normalize_key(value)).strip()

# In _resolve_template_col_idx, after existing 4 lookups:
fuzzy_key = self._normalize_key_fuzzy(key)
for col_name, col_idx in display_map.items():
    if self._normalize_key_fuzzy(col_name) == fuzzy_key:
        return col_idx
for col_name, col_idx in machine_map.items():
    if self._normalize_key_fuzzy(col_name) == fuzzy_key:
        return col_idx
return None
```

### Fix 2: TEMPLATES_DIR path detection

**In `config.py`:**
```python
_templates_candidates = [PROJECT_ROOT / "templates", BASE_DIR / "templates"]
TEMPLATES_DIR = next((p for p in _templates_candidates if p.exists()), _templates_candidates[0])
```

Local dev: `PROJECT_ROOT/templates` exists → used.
Docker: `PROJECT_ROOT/templates` = `/templates` (missing), falls back to `BASE_DIR/templates` = `/app/templates` ✓

### Fix 3: Case-insensitive template sheet lookup

DE/FR/IT/ES xlsm files have lowercase `template` sheet. Always use case-insensitive lookup:
```python
_sheet_name = next((s for s in workbook.sheetnames if s.lower() == "template"), None)
```

## Verification

```python
docker exec <container> python3 -c "
import sys; sys.path.insert(0, '/app')
from app.config import TEMPLATES_DIR
print('TEMPLATES_DIR:', TEMPLATES_DIR)
print('exists:', TEMPLATES_DIR.exists())
"
# Should show: TEMPLATES_DIR: /app/templates  exists: True

# Run end-to-end test and check output has filled columns:
# processed_count > 0, output template sheet has item_sku, brand_name, color_name, etc.
```

## Notes

- UK template (`AMZEU_UK_AddColor_Template.xlsx`) uses English display names in row 2,
  so the English key names work for UK. DE/FR/IT/ES need the machine-name aliases.
- The DE category **listing input** files (used for indexing) have a DIFFERENT structure:
  5 header rows with machine headers at row 5. The OUTPUT template has 3 header rows.
- `other_image_url1`..`other_image_url8` in DE template vs `"Other Image Url1"` in row dict —
  fixed by the fuzzy normalization (space/underscore equivalence).
- xlsm templates must be opened with `keep_vba=True` to preserve macros.
- Sheet names in DE/FR/IT/ES templates: `['Dropdown Lists', 'AttributePTDMAP', 'template', 'Conditions List']`
