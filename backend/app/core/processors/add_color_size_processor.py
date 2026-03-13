"""UK add-color/add-size workbook processor."""

from __future__ import annotations

from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
import re
import shutil
import types as _types
from pathlib import Path
from typing import Any, Iterable, Mapping

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from app.config import COUNTRY_PROFILES, RESULTS_DIR, TEMPLATES_DIR, UPLOADS_DIR, Country, CountryProfile
from app.core.color_mapper import color_mapper
from app.core.parsers.sku import SKUInfo
from app.models.excel import ProcessRequest


STATIC_FIELDS: dict[str, Any] = {
    "Parentage": "Child",
    "Relationship Type": "Variation",
    "Variation Theme": "SizeName-ColorName",
    "Update Delete": "Update",
    "Adult Flag": "No",
    "Country/Region Of Origin": "China",
    "quantity": 2,
    "target_gender": "Female",
    "age_range_description": "Adult",
    "apparel_size_class": "Numeric",
    "apparel_body_type": "Regular",
    "apparel_height_type": "Regular",
    "lifecycle_supply_type": "Fashion",
    "Condition Type": "New",
    "batteries_required": "No",
    "are_batteries_included": "No",
}

COPY_FIELD_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    ("Product Type", ("product type", "product_type", "product_type#1.value")),
    (
        "Brand Name",
        (
            "brand name",
            "brand",
            "brand[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Outer Material Type",
        (
            "outer material type",
            "material",
            "material[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Occasion description",
        (
            "occasion description",
            "lifestyle",
            "lifestyle[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Style Name",
        (
            "style name",
            "style",
            "style[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Neck Style",
        (
            "neck style",
            "neck[marketplace_id=a1f83g8c2aro7p]#1.neck_style[language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Department",
        (
            "department",
            "department name",
            "department[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Item Length",
        (
            "item length",
            "item length description",
            "item_length_description[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "fabric_type",
        (
            "fabric_type",
            "fabric type",
            "fabric_type[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Product Description",
        (
            "product description",
            "product_description",
            "product_description[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Product Care Instructions",
        (
            "product care instructions",
            "care instructions",
            "care_instructions[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Sleeve Type",
        (
            "sleeve type",
            "sleeve_type",
            "sleeve[marketplace_id=a1f83g8c2aro7p]#1.type[language_tag=en_gb]#1.value",
        ),
    ),
    (
        "Package Length",
        (
            "package length",
            "item package length",
            "item_package_dimensions[marketplace_id=a1f83g8c2aro7p]#1.length.value",
        ),
    ),
    (
        "Package Width",
        (
            "package width",
            "package-width",
            "package_width",
            "item_package_dimensions[marketplace_id=a1f83g8c2aro7p]#1.width.value",
        ),
    ),
    (
        "Package Length Unit Of Measure",
        (
            "package length unit of measure",
            "package length unit",
            "item_package_dimensions[marketplace_id=a1f83g8c2aro7p]#1.length.unit",
        ),
    ),
    (
        "Package Height",
        (
            "package height",
            "item package height",
            "item_package_dimensions[marketplace_id=a1f83g8c2aro7p]#1.height.value",
        ),
    ),
    (
        "Package Dimensions Unit Of Measure",
        (
            "package dimensions unit of measure",
            "package height unit",
            "item_package_dimensions[marketplace_id=a1f83g8c2aro7p]#1.height.unit",
        ),
    ),
    (
        "Package Weight",
        (
            "package weight",
            "item package weight",
            "item_package_weight[marketplace_id=a1f83g8c2aro7p]#1.value",
        ),
    ),
    (
        "Package Weight Unit Of Measure",
        (
            "package weight unit of measure",
            "item package weight unit",
            "item_package_weight[marketplace_id=a1f83g8c2aro7p]#1.unit",
        ),
    ),
    (
        "Recommended Browse Nodes",
        (
            "recommended browse nodes",
            "recommended_browse_nodes[marketplace_id=a1f83g8c2aro7p]#1.value",
        ),
    ),
]

GENERIC_KEYWORD_ALIASES = (
    "generic_keywords",
    "generic keyword",
    "generic keywords",
    "generic_keyword",
    "generic_keyword[marketplace_id=a1f83g8c2aro7p][language_tag=en_gb]#1.value",
)
ITEM_NAME_ALIASES = ("item name", "product name")
COLOUR_ALIASES = ("colour", "color")
PRICE_ALIASES = (
    "your price gbp (sell on amazon, uk)",
    "your price eur (sell on amazon",
    "your price gbp",
    "your price eur",
    "your price",
    "price",
    "standard price",
    "sale price gbp",
    "sale price eur",
    "list price with tax",
    "list price with tax for display",
    "purchasable_offer[marketplace_id=a1f83g8c2aro7p][audience=all]#1.our_price#1.schedule#1.value_with_tax",
)
ASIN_ALIASES = ("asin", "asin1", "asin 1")

COLOUR_MAP_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Black", ("black",)),
    ("White", ("white", "ivory")),
    ("Blue", ("blue", "navy", "azure", "cobalt", "teal")),
    ("Green", ("green", "sage", "olive", "mint")),
    ("Red", ("red", "burgundy", "wine", "maroon")),
    ("Pink", ("pink", "rose", "blush")),
    ("Purple", ("purple", "lilac", "lavender", "violet")),
    ("Yellow", ("yellow", "mustard")),
    ("Orange", ("orange", "coral", "apricot")),
    ("Brown", ("brown", "coffee", "chocolate")),
    ("Beige", ("beige", "nude", "champagne", "cream", "khaki", "taupe", "camel")),
    ("Grey", ("grey", "gray", "silver")),
    ("Gold", ("gold",)),
]

DEFAULT_TEMPLATE_FILL = PatternFill(fill_type="solid", fgColor="FCE4D6")


@dataclass(slots=True)
class ProcessResult:
    output_file: str
    processed_count: int
    skipped_count: int
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _NormalizedRecord:
    sku: str
    parsed_sku: SKUInfo | None
    all_listings_data: dict[str, Any]
    category_data: dict[str, Any]
    price: float | None
    asin: str | None


class AddColorSizeProcessor:
    """Generate add-color/add-size workbooks from listing index data."""

    def process(
        self,
        index_or_request: Any,
        country: str | Country | None = None,
        selected_prefixes: Iterable[str] | None = None,
        target_colors: Iterable[str] | None = None,
        start_size: str | int | None = None,
        end_size: str | int | None = None,
        size_step: int = 1,
        output_filename: str | None = None,
        progress_callback: Any | None = None,
    ) -> ProcessResult:
        if isinstance(index_or_request, ProcessRequest):
            request = index_or_request
            return self._process_from_request(
                request=request,
                output_filename=output_filename,
                progress_callback=progress_callback,
            )

        if country is None:
            raise ValueError("country is required when processing an explicit index")
        if selected_prefixes is None or target_colors is None:
            raise ValueError("selected_prefixes and target_colors are required")
        if start_size is None or end_size is None:
            raise ValueError("start_size and end_size are required")

        return self._process_core(
            index=index_or_request,
            country=country,
            selected_prefixes=selected_prefixes,
            target_colors=target_colors,
            start_size=start_size,
            end_size=end_size,
            size_step=size_step,
            output_filename=output_filename,
            progress_callback=progress_callback,
        )

    def _process_from_request(
        self,
        *,
        request: ProcessRequest,
        output_filename: str | None,
        progress_callback: Any | None,
    ) -> ProcessResult:
        index = self._build_index_from_request(request)
        return self._process_core(
            index=index,
            country=request.country,
            selected_prefixes=request.selected_prefixes,
            target_colors=request.target_colors,
            start_size=request.start_size,
            end_size=request.end_size,
            size_step=request.size_step,
            output_filename=output_filename,
            progress_callback=progress_callback,
            mode=request.mode,
        )

    def _process_core(
        self,
        *,
        index: Any,
        country: str | Country,
        selected_prefixes: Iterable[str],
        target_colors: Iterable[str],
        start_size: str | int,
        end_size: str | int,
        size_step: int,
        output_filename: str | None,
        progress_callback: Any | None,
        mode: str = "add-color",
    ) -> ProcessResult:
        resolved_country = country if isinstance(country, Country) else Country(str(country).strip().upper())
        profile = COUNTRY_PROFILES[resolved_country]
        normalized_prefixes = self._dedupe_upper(selected_prefixes)
        normalized_colors = self._dedupe_upper(target_colors)
        size_codes = self._build_size_codes(start_size=start_size, end_size=end_size, size_step=size_step)
        headers = self._build_headers(profile)
        rows_by_suffix: dict[str, list[dict[str, Any]]] = defaultdict(list)
        errors: list[str] = []
        processed_count = 0
        skipped_count = 0
        total_operations = max(1, len(normalized_prefixes) * len(normalized_colors) * len(size_codes))

        if progress_callback is not None:
            progress_callback(20)

        for prefix_index, prefix in enumerate(normalized_prefixes, start=1):
            records = self._get_records_for_prefix(index, prefix)
            if not records:
                errors.append(f"No source records found for prefix {prefix}")
                continue

            suffixes = self._collect_suffixes(records)
            # Only keep suffixes matching the current country (e.g. -UK, -UK1, -UK2 for UK)
            country_upper = profile.country.upper()
            suffixes = [s for s in suffixes if s.lstrip("-").upper().startswith(country_upper)]
            if not suffixes:
                errors.append(f"No parsed suffixes found for prefix {prefix}")
                continue

            for suffix in suffixes:
                source_record = self._pick_source_record(records, suffix)
                if source_record is None or source_record.parsed_sku is None:
                    errors.append(f"No usable source record found for {prefix}{suffix}")
                    skipped_count += len(normalized_colors) * len(size_codes)
                    continue

                for color_code in normalized_colors:
                    for size_code in size_codes:
                        row = self._build_output_row(
                            source_record=source_record,
                            new_color_code=color_code,
                            new_size_code=size_code,
                            profile=profile,
                        )
                        rows_by_suffix[suffix].append(row)
                        processed_count += 1

            if progress_callback is not None:
                progress = 20 + int((prefix_index / len(normalized_prefixes)) * 70)
                progress_callback(min(progress, 95))

        _req_ns = _types.SimpleNamespace(
            country=resolved_country,
            selected_prefixes=normalized_prefixes,
            target_colors=normalized_colors,
            mode=mode,
        )
        output_name = self._resolve_output_filename(output_filename, _req_ns)
        output_path = RESULTS_DIR / output_name
        self._write_workbook(
            output_path=output_path,
            headers=headers,
            rows_by_suffix=rows_by_suffix,
            template_path=TEMPLATES_DIR / profile.template_file,
        )

        if progress_callback is not None:
            if processed_count == 0 and skipped_count == 0:
                skipped_count = total_operations
            progress_callback(100)

        return ProcessResult(
            output_file=output_name,
            processed_count=processed_count,
            skipped_count=skipped_count,
        )

    def _build_index_from_request(self, request: ProcessRequest) -> Any:
        all_listings_path = UPLOADS_DIR / Path(request.all_listings_file).name
        category_paths = [UPLOADS_DIR / Path(filename).name for filename in request.category_files]

        from app.core import indexers as indexer_module

        index_cls = getattr(indexer_module, "ListingIndex", None) or getattr(indexer_module, "ListingIndexer", None)
        if index_cls is None:
            raise RuntimeError("No listing index implementation is available")

        indexer = index_cls()
        build_index = getattr(indexer, "build_index", None)
        if callable(build_index):
            return build_index(all_listings_path, category_paths)
        return indexer

    def _build_output_row(
        self,
        *,
        source_record: _NormalizedRecord,
        new_color_code: str,
        new_size_code: str,
        profile: CountryProfile,
    ) -> dict[str, Any]:
        if source_record.parsed_sku is None:
            raise ValueError("source_record.parsed_sku is required")

        source_info = source_record.parsed_sku
        product_code = source_info.product_code
        sku = f"{product_code}{new_color_code}{new_size_code}{source_info.suffix}"
        parent_sku = f"{product_code}{source_info.suffix}"
        size_value = int(new_size_code)
        size_map = size_value + profile.size_offset
        old_size_map = int(source_info.size_code) + profile.size_offset
        source_data = self._merge_source_data(source_record)
        lang = profile.language_tag.split("_")[0]  # "en_GB" → "en", "fr_FR" → "fr"
        new_colour = self._get_colour_name(new_color_code, lang=lang)
        old_colour = self._get_source_colour_name(source_record, lang=lang)
        standard_price = source_record.price or 0.0
        list_price_with_tax = standard_price + 10
        generic_keyword_header = self._generic_keyword_header(profile)
        product_name = self._build_product_name(
            source_data=source_data,
            old_colour=old_colour,
            new_colour=new_colour,
            old_size_map=old_size_map,
            new_size_map=size_map,
            country_code=profile.country,
        )

        row: dict[str, Any] = {
            **STATIC_FIELDS,
            "Seller SKU": sku,
            "Model Name": sku,
            "Model Number": sku,
            "part_number": sku,
            "Parent SKU": parent_sku,
            "Colour Map": self._infer_colour_map(new_colour),
            "Colour": new_colour,
            "Size": size_map,
            "Size Map": size_map,
            "apparel_size": size_map,
            "Product Name": product_name,
            "Currency": profile.currency,
            "standard_price": standard_price,
            "List Price with Tax for Display": list_price_with_tax,
            "main_image_url": self._build_image_url(product_code, new_color_code, profile.image_suffix_main),
            "apparel_size_system": profile.country,
        }

        for output_key, aliases in COPY_FIELD_ALIASES:
            row[output_key] = self._first_value(source_record.category_data, aliases)

        for index, suffix in enumerate(profile.image_suffixes_other, start=1):
            row[f"Other Image Url{index}"] = self._build_image_url(product_code, new_color_code, suffix)

        row[generic_keyword_header] = self._first_value(source_data, GENERIC_KEYWORD_ALIASES)

        for bullet_index in range(1, 6):
            header = self._bullet_point_header(profile, bullet_index)
            aliases = (
                f"bullet_point{bullet_index}",
                f"bullet point {bullet_index}",
                f"bullet_point {bullet_index}",
            )
            row[header] = self._first_value(source_record.category_data, aliases)

        return row

    def _write_workbook(
        self,
        *,
        output_path: Path,
        headers: list[str],
        rows_by_suffix: Mapping[str, list[dict[str, Any]]],
        template_path: Path | None = None,
    ) -> None:
        if template_path is not None and template_path.exists():
            shutil.copy(template_path, output_path)
            workbook = load_workbook(output_path)
            try:
                worksheet = workbook["Template"]
                display_map = self._build_template_col_map(worksheet, row_number=2)
                machine_map = self._build_template_col_map(worksheet, row_number=3)
                row_styles = self._capture_template_row_styles(worksheet, row_number=4)
                worksheet.delete_rows(4, 500)
                self._reset_column_dimension_styles(worksheet)
                self._reset_row_dimension_styles(worksheet, start_row=4)

                next_row = 4
                all_rows = [
                    row
                    for suffix, rows in sorted(rows_by_suffix.items())
                    for row in rows
                ]
                self._reset_row_dimension_styles(worksheet, start_row=4, end_row=3 + len(all_rows))
                for row in all_rows:
                    for key, value in row.items():
                        col_idx = self._resolve_template_col_idx(
                            key=key,
                            display_map=display_map,
                            machine_map=machine_map,
                        )
                        if col_idx is not None:
                            cell = worksheet.cell(row=next_row, column=col_idx, value=value)
                            self._apply_template_row_style(cell, row_styles.get(col_idx))
                    next_row += 1

                workbook.save(output_path)
            finally:
                workbook.close()
            return

        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        if rows_by_suffix:
            for suffix, rows in sorted(rows_by_suffix.items()):
                worksheet = workbook.create_sheet(title=self._sheet_name_for_suffix(suffix))
                worksheet.append(headers)
                for row in rows:
                    worksheet.append([row.get(header) for header in headers])
        else:
            worksheet = workbook.create_sheet(title="EMPTY")
            worksheet.append(headers)

        workbook.save(output_path)
        workbook.close()

    def _reset_column_dimension_styles(self, worksheet: Any) -> None:
        for column_dimension in worksheet.column_dimensions.values():
            # Keep width and other column settings, but remove template-level default fill.
            column_dimension._style = None

    def _reset_row_dimension_styles(
        self,
        worksheet: Any,
        *,
        start_row: int = 1,
        end_row: int | None = None,
    ) -> None:
        row_indexes = sorted(row_idx for row_idx in worksheet.row_dimensions.keys() if row_idx >= start_row)
        for row_idx in row_indexes:
            if end_row is not None and row_idx > end_row:
                break

            row_dimension = worksheet.row_dimensions.get(row_idx)
            if row_dimension is None:
                continue

            # Keep height and other row settings, but remove template-level default fill.
            row_dimension._style = None

    def _build_template_col_map(self, worksheet: Any, *, row_number: int) -> dict[str, int]:
        col_map: dict[str, int] = {}
        for col_idx in range(1, worksheet.max_column + 1):
            raw_value = worksheet.cell(row=row_number, column=col_idx).value
            text = str(raw_value).strip() if raw_value is not None else ""
            if text:
                col_map[text] = col_idx
        return col_map

    def _capture_template_row_styles(self, worksheet: Any, *, row_number: int) -> dict[int, dict[str, Any]]:
        if worksheet.max_row < row_number:
            return {}

        styles: dict[int, dict[str, Any]] = {}
        for col_idx in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(row=row_number, column=col_idx)
            if not cell.has_style and cell.value is None:
                continue

            styles[col_idx] = {
                "fill": copy(cell.fill),
                "font": copy(cell.font),
                "border": copy(cell.border),
                "alignment": copy(cell.alignment),
                "number_format": cell.number_format,
            }
        return styles

    def _apply_template_row_style(self, cell: Any, style: Mapping[str, Any] | None) -> None:
        if style is None:
            cell.fill = copy(DEFAULT_TEMPLATE_FILL)
            return

        cell.fill = copy(style["fill"])
        cell.font = copy(style["font"])
        cell.border = copy(style["border"])
        cell.alignment = copy(style["alignment"])
        cell.number_format = style["number_format"]

    def _resolve_template_col_idx(
        self,
        *,
        key: str,
        display_map: Mapping[str, int],
        machine_map: Mapping[str, int],
    ) -> int | None:
        if key in display_map:
            return display_map[key]
        if key in machine_map:
            return machine_map[key]

        normalized_key = self._normalize_key(key)
        for col_name, col_idx in display_map.items():
            if self._normalize_key(col_name) == normalized_key:
                return col_idx
        for col_name, col_idx in machine_map.items():
            if self._normalize_key(col_name) == normalized_key:
                return col_idx
        return None

    def _build_headers(self, profile: CountryProfile) -> list[str]:
        headers = [
            "Seller SKU",
            "Parent SKU",
            "Parentage",
            "Relationship Type",
            "Variation Theme",
            "Update Delete",
            "Adult Flag",
            "Country/Region Of Origin",
            "quantity",
            "target_gender",
            "age_range_description",
            "Product Type",
            "Brand Name",
            "Product Name",
            "Outer Material Type",
            "Occasion description",
            "Style Name",
            "Neck Style",
            "Department",
            "Item Length",
            "fabric_type",
            "Product Description",
            "Product Care Instructions",
            "Sleeve Type",
            "Package Length",
            "Package Length Unit Of Measure",
            "Package Width",
            "Package Height",
            "Package Dimensions Unit Of Measure",
            "Package Weight",
            "Package Weight Unit Of Measure",
            "Recommended Browse Nodes",
            "Model Name",
            "Model Number",
            "part_number",
            "Colour",
            "Colour Map",
            "Size",
            "Size Map",
            "apparel_size",
            "apparel_size_system",
            "apparel_size_class",
            "apparel_body_type",
            "apparel_height_type",
            "lifecycle_supply_type",
            "Condition Type",
            "Currency",
            "standard_price",
            "List Price with Tax for Display",
            "main_image_url",
            "Other Image Url1",
            "Other Image Url2",
            "Other Image Url3",
            "Other Image Url4",
            "Other Image Url5",
            "batteries_required",
            "are_batteries_included",
            self._generic_keyword_header(profile),
        ]

        for bullet_index in range(1, 6):
            headers.append(self._bullet_point_header(profile, bullet_index))

        return headers

    def _merge_source_data(self, record: _NormalizedRecord) -> dict[str, Any]:
        merged = dict(record.all_listings_data)
        merged.update(record.category_data)
        return merged

    def _get_records_for_prefix(self, index: Any, prefix: str) -> list[_NormalizedRecord]:
        raw_records: Iterable[Any]
        if hasattr(index, "get_by_prefix"):
            raw_records = index.get_by_prefix(prefix) or []
        elif isinstance(index, Mapping):
            by_prefix = index.get("by_prefix", {})
            if isinstance(by_prefix, Mapping):
                raw_group = by_prefix.get(prefix, {})
                if isinstance(raw_group, Mapping):
                    raw_records = raw_group.values()
                else:
                    raw_records = raw_group or []
            else:
                raw_records = []
        else:
            raw_records = []

        return [normalized for item in raw_records if (normalized := self._normalize_record(item)) is not None]

    def _normalize_record(self, raw_record: Any) -> _NormalizedRecord | None:
        if raw_record is None:
            return None

        if isinstance(raw_record, Mapping):
            sku = str(raw_record.get("sku") or "").strip().upper()
            parsed_sku = raw_record.get("parsed_sku")
            all_listings_data = self._normalize_mapping(raw_record.get("all_listings_data"))
            category_data = self._normalize_mapping(raw_record.get("category_data"))
            price = self._parse_price(raw_record.get("price"))
            if price is None:
                price = self._parse_price(self._first_value({**all_listings_data, **category_data}, PRICE_ALIASES))
            asin = self._string_or_none(raw_record.get("asin"))
            if asin is None:
                asin = self._string_or_none(self._first_value(all_listings_data, ASIN_ALIASES))
            return _NormalizedRecord(
                sku=sku,
                parsed_sku=parsed_sku if isinstance(parsed_sku, SKUInfo) else None,
                all_listings_data=all_listings_data,
                category_data=category_data,
                price=price,
                asin=asin,
            )

        sku = str(getattr(raw_record, "sku", "") or "").strip().upper()
        parsed_sku = getattr(raw_record, "parsed_sku", None)
        all_listings_data = self._normalize_mapping(getattr(raw_record, "all_listings_data", None))
        category_data = self._normalize_mapping(getattr(raw_record, "category_data", None))
        price = self._parse_price(getattr(raw_record, "price", None))
        if price is None:
            price = self._parse_price(self._first_value({**all_listings_data, **category_data}, PRICE_ALIASES))
        asin = self._string_or_none(getattr(raw_record, "asin", None))
        if asin is None:
            asin = self._string_or_none(self._first_value(all_listings_data, ASIN_ALIASES))
        return _NormalizedRecord(
            sku=sku,
            parsed_sku=parsed_sku if isinstance(parsed_sku, SKUInfo) else None,
            all_listings_data=all_listings_data,
            category_data=category_data,
            price=price,
            asin=asin,
        )

    def _collect_suffixes(self, records: Iterable[_NormalizedRecord]) -> list[str]:
        suffixes = {
            record.parsed_sku.suffix
            for record in records
            if record.parsed_sku is not None and record.parsed_sku.suffix
        }
        return sorted(suffixes)

    def _pick_source_record(self, records: Iterable[_NormalizedRecord], suffix: str) -> _NormalizedRecord | None:
        candidates = [
            record
            for record in records
            if record.parsed_sku is not None and record.parsed_sku.suffix == suffix
        ]
        if not candidates:
            return None

        candidates.sort(
            key=lambda record: (
                0 if record.category_data else 1,
                0 if record.all_listings_data else 1,
                record.sku,
            )
        )
        return candidates[0]

    def _build_product_name(
        self,
        *,
        source_data: Mapping[str, Any],
        old_colour: str,
        new_colour: str,
        old_size_map: int,
        new_size_map: int,
        country_code: str,
    ) -> str:
        item_name = self._string_or_none(self._first_value(source_data, ITEM_NAME_ALIASES)) or ""
        if not item_name:
            return ""

        updated = item_name
        if old_colour and new_colour and old_colour.lower() != new_colour.lower():
            updated = re.sub(re.escape(old_colour), new_colour, updated, flags=re.IGNORECASE)

        old_token = f"{old_size_map}{country_code}"
        new_token = f"{new_size_map}{country_code}"
        updated = re.sub(rf"\b{re.escape(old_token)}\b", new_token, updated, flags=re.IGNORECASE)
        updated = re.sub(
            rf"\b{old_size_map}\s*{country_code}\b",
            f"{new_size_map}{country_code}",
            updated,
            flags=re.IGNORECASE,
        )
        return updated

    def _get_source_colour_name(self, record: _NormalizedRecord, lang: str = "en") -> str:
        source_colour = self._string_or_none(self._first_value(record.category_data, COLOUR_ALIASES))
        if source_colour:
            return source_colour
        if record.parsed_sku is not None:
            return self._get_colour_name(record.parsed_sku.color_code, lang=lang)
        return ""

    def _get_colour_name(self, color_code: str, lang: str = "en") -> str:
        return color_mapper.get_mapping(color_code, lang=lang) or color_code

    def _infer_colour_map(self, colour_name: str) -> str:
        lowered = colour_name.strip().lower()
        for family, keywords in COLOUR_MAP_KEYWORDS:
            if any(keyword in lowered for keyword in keywords):
                return family
        return colour_name

    def _build_image_url(self, product_code: str, color_code: str, suffix: str) -> str:
        return f"https://eppic.s3.amazonaws.com/{product_code}{color_code}{suffix}.jpg"

    def _resolve_output_filename(self, output_filename: str | None, request: Any) -> str:
        if output_filename:
            filename = Path(output_filename).name
            if not filename.lower().endswith(".xlsx"):
                filename = f"{filename}.xlsx"
            return filename

        country = request.country.value  # "UK" / "FR" / ...
        prefixes = request.selected_prefixes
        mode = request.mode

        # STYLE_PART
        if len(prefixes) == 1:
            style_part = prefixes[0]
        elif len(prefixes) == 2:
            style_part = f"{prefixes[0]}+{prefixes[1]}"
        else:
            style_part = f"{len(prefixes)}STYLE"

        # OP_TYPE + COLOR_PART
        if mode == "add-color":
            color_part = " " + " ".join(request.target_colors) if request.target_colors else ""
            op_type = f"补色{color_part}"
        else:
            op_type = "补码"

        return f"{country}-{style_part}-{op_type}.xlsx"

    def _build_size_codes(self, *, start_size: str | int, end_size: str | int, size_step: int) -> list[str]:
        step = int(size_step)
        if step <= 0:
            raise ValueError("size_step must be greater than 0")
        start_value = int(start_size)
        end_value = int(end_size)
        if end_value < start_value:
            raise ValueError("end_size must be greater than or equal to start_size")
        return [f"{size_value:02d}" for size_value in range(start_value, end_value + 1, step)]

    def _generic_keyword_header(self, profile: CountryProfile) -> str:
        return "generic_keywords"

    def _bullet_point_header(self, profile: CountryProfile, bullet_index: int) -> str:
        return f"bullet_point{bullet_index}"

    def _sheet_name_for_suffix(self, suffix: str) -> str:
        cleaned = re.sub(r"[:\\\\/?*\\[\\]]", "_", suffix or "EMPTY")
        return cleaned[:31] or "EMPTY"

    def _dedupe_upper(self, values: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = str(value).strip().upper()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    def _normalize_mapping(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            return {}
        return {self._normalize_key(key): item for key, item in value.items()}

    def _first_value(self, data: Mapping[str, Any], aliases: Iterable[str]) -> Any:
        if not data:
            return None
        for alias in aliases:
            normalized_alias = self._normalize_key(alias)
            if normalized_alias in data:
                value = data[normalized_alias]
                if value is not None and value != "":
                    return value
        return None

    def _normalize_key(self, value: Any) -> str:
        return str(value or "").replace("\ufeff", "").strip().casefold()

    def _parse_price(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        cleaned = re.sub(r"[^0-9.\\-]", "", text)
        if cleaned.count(".") > 1:
            first_dot = cleaned.find(".")
            cleaned = cleaned[: first_dot + 1] + cleaned[first_dot + 1 :].replace(".", "")
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
