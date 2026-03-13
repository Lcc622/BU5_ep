from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Country
import app.core.processors.add_color_size_processor as processor_module
from app.core.color_mapper import color_mapper
from app.core.parsers.sku import parse_sku
from app.core.processors.add_color_size_processor import AddColorSizeProcessor
from app.models.excel import ProcessRequest


class _FakeListingRecord:
    def __init__(
        self,
        *,
        sku: str,
        all_listings_data: dict[str, object],
        category_data: dict[str, object],
        price: float,
        asin: str | None = None,
    ) -> None:
        self.sku = sku
        self.parsed_sku = parse_sku(sku)
        self.all_listings_data = all_listings_data
        self.category_data = category_data
        self.price = price
        self.asin = asin


class _FakeListingIndex:
    def __init__(self, by_prefix: dict[str, list[_FakeListingRecord]]) -> None:
        self._by_prefix = by_prefix

    def get_by_prefix(self, prefix: str) -> list[_FakeListingRecord]:
        return list(self._by_prefix.get(prefix, []))


def _sheet_rows(workbook_path: Path, sheet_name: str) -> tuple[list[str], list[dict[str, object]]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet_name]
        headers = [str(value) if value is not None else "" for value in next(worksheet.iter_rows(max_row=1, values_only=True))]
        rows: list[dict[str, object]] = []
        for values in worksheet.iter_rows(min_row=2, values_only=True):
            if not any(value not in (None, "") for value in values):
                continue
            rows.append(dict(zip(headers, values)))
        return headers, rows
    finally:
        workbook.close()


def _template_rows(workbook_path: Path) -> tuple[list[str], list[dict[str, object]]]:
    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        worksheet = workbook["Template"]
        headers = [
            str(worksheet.cell(row=2, column=column_index).value or "")
            for column_index in range(1, worksheet.max_column + 1)
        ]
        rows: list[dict[str, object]] = []
        for row_index in range(4, worksheet.max_row + 1):
            values = [worksheet.cell(row=row_index, column=column_index).value for column_index in range(1, worksheet.max_column + 1)]
            if not any(value not in (None, "") for value in values):
                continue
            rows.append(dict(zip(headers, values)))
        return headers, rows
    finally:
        workbook.close()


class AddColorSizeProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._results_dir = tempfile.TemporaryDirectory()
        self._uploads_dir = tempfile.TemporaryDirectory()
        self._templates_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._results_dir.cleanup)
        self.addCleanup(self._uploads_dir.cleanup)
        self.addCleanup(self._templates_dir.cleanup)

        self._original_results_dir = processor_module.RESULTS_DIR
        self._original_uploads_dir = processor_module.UPLOADS_DIR
        self._original_templates_dir = processor_module.TEMPLATES_DIR
        self._original_mappings = color_mapper.mappings.copy()

        processor_module.RESULTS_DIR = Path(self._results_dir.name)
        processor_module.UPLOADS_DIR = Path(self._uploads_dir.name)
        processor_module.TEMPLATES_DIR = Path(self._templates_dir.name)
        color_mapper.mappings = {
            "BK": {"en": "Black", "fr": "Noir", "de": "Schwarz", "it": "Nero", "es": "Negro"},
            "BD": {"en": "Royal Blue", "fr": "Bleu Royal", "de": "Königsblau", "it": "Blu Reale", "es": "Azul Real"},
            "SG": {"en": "Sage Green", "fr": "", "de": "", "it": "", "es": ""},
        }

        self.addCleanup(self._restore_environment)

    def _restore_environment(self) -> None:
        processor_module.RESULTS_DIR = self._original_results_dir
        processor_module.UPLOADS_DIR = self._original_uploads_dir
        processor_module.TEMPLATES_DIR = self._original_templates_dir
        color_mapper.mappings = self._original_mappings

    def _create_template_workbook(self) -> Path:
        template_path = processor_module.TEMPLATES_DIR / processor_module.COUNTRY_PROFILES[Country.UK].template_file
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Template"
        worksheet.append(["Metadata"])
        worksheet.append(
            [
                "Seller SKU",
                "Parent SKU",
                "Variation Theme",
                "Colour",
                "Colour Map",
                "Size",
                "Size Map",
                "Product Name",
                "Currency",
                "List Price with Tax for Display",
                "Main Image Url",
                "Other Image Url5",
                "bullet_point[marketplace_id=A1F83G8C2ARO7P][language_tag=en_GB]#1.value",
                "generic_keyword[marketplace_id=A1F83G8C2ARO7P][language_tag=en_GB]#1.value",
            ]
        )
        worksheet.append(
            [
                "item_sku",
                "parent_sku",
                "variation_theme",
                "color_name",
                "color_map",
                "size_name",
                "size_map",
                "item_name",
                "currency",
                "list_price_with_tax",
                "main_image_url",
                "other_image_url5",
                "bullet_point1",
                "generic_keywords",
            ]
        )
        worksheet.append(["stale", "stale", "stale"])
        workbook.save(template_path)
        workbook.close()
        return template_path

    def test_process_generates_grouped_workbook_for_listing_index_style_input(self) -> None:
        self._create_template_workbook()
        base_category = {
            "Item Name": "Black Maxi Dress 8UK",
            "Colour": "Black",
            "Product Type": "Dress",
            "Brand Name": "Ever-Pretty",
            "Outer Material Type": "Polyester",
            "Occasion description": "Formal",
            "Style Name": "Maxi",
            "Neck Style": "V-Neck",
            "Department": "womens",
            "Item Length": "Maxi",
            "fabric_type": "100% Polyester",
            "Product Description": "A flowing evening dress.",
            "Product Care Instructions": "Hand Wash Only",
            "Sleeve Type": "Sleeveless",
            "Package Length": "35",
            "Package Length Unit Of Measure": "centimeters",
            "Package Height": "5",
            "Package Height Unit Of Measure": "centimeters",
            "Package Weight": "0.6",
            "Package Weight Unit Of Measure": "kilograms",
            "Recommended Browse Nodes": "123456",
            "apparel_size_body_type": "Regular",
            "apparel_size_height_type": "Regular",
            "bullet_point1": "Soft lining",
            "bullet_point2": "Elegant pleats",
            "bullet_point3": "V-neck cut",
            "bullet_point4": "Floor length",
            "bullet_point5": "Concealed zip",
        }
        base_listing = {
            "price": "19.99",
            "generic keyword": "evening dress formal wedding",
            "asin1": "ASIN123",
        }
        index = _FakeListingIndex(
            {
                "EG02230": [
                    _FakeListingRecord(
                        sku="EG02230BK04-UK1",
                        all_listings_data=base_listing,
                        category_data=base_category,
                        price=19.99,
                        asin="ASIN123",
                    ),
                    _FakeListingRecord(
                        sku="EG02230BK04-UK2",
                        all_listings_data=base_listing,
                        category_data=base_category,
                        price=19.99,
                        asin="ASIN456",
                    ),
                ]
            }
        )

        result = AddColorSizeProcessor().process(
            index,
            country="UK",
            selected_prefixes=["EG02230"],
            target_colors=["BD"],
            start_size="04",
            end_size="06",
            size_step=2,
            output_filename="uk-output.xlsx",
        )

        self.assertEqual(result.output_file, "uk-output.xlsx")
        self.assertEqual(result.processed_count, 4)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.errors, [])

        output_path = Path(self._results_dir.name) / result.output_file
        self.assertTrue(output_path.exists())

        workbook = load_workbook(output_path, read_only=True, data_only=True)
        try:
            self.assertEqual(workbook.sheetnames, ["Template"])
        finally:
            workbook.close()

        headers, template_rows = _template_rows(output_path)
        bullet_header = (
            "bullet_point[marketplace_id=A1F83G8C2ARO7P]"
            "[language_tag=en_GB]#1.value"
        )
        keyword_header = (
            "generic_keyword[marketplace_id=A1F83G8C2ARO7P]"
            "[language_tag=en_GB]#1.value"
        )
        self.assertIn(bullet_header, headers)
        self.assertIn(keyword_header, headers)

        self.assertEqual(len(template_rows), 4)
        self.assertEqual(template_rows[0]["Seller SKU"], "EG02230BD04-UK1")
        self.assertEqual(template_rows[0]["Parent SKU"], "EG02230-UK1")
        self.assertEqual(template_rows[0]["Variation Theme"], "SizeName-ColorName")
        self.assertEqual(template_rows[0]["Colour"], "Royal Blue")
        self.assertEqual(template_rows[0]["Colour Map"], "Blue")
        self.assertEqual(template_rows[0]["Size"], 8)
        self.assertEqual(template_rows[0]["Size Map"], 8)
        self.assertEqual(template_rows[0]["Product Name"], "Royal Blue Maxi Dress 8UK")
        self.assertEqual(template_rows[1]["Product Name"], "Royal Blue Maxi Dress 10UK")
        self.assertEqual(template_rows[0]["Currency"], "GBP")
        self.assertEqual(template_rows[0]["List Price with Tax for Display"], 29.99)
        self.assertEqual(
            template_rows[0]["Main Image Url"],
            "https://eppic.s3.amazonaws.com/EG02230BD-L.jpg",
        )
        self.assertEqual(
            template_rows[0]["Other Image Url5"],
            "https://eppic.s3.amazonaws.com/EG02230BD-S-UK.jpg",
        )
        self.assertEqual(template_rows[0][bullet_header], "Soft lining")
        self.assertEqual(template_rows[0][keyword_header], "evening dress formal wedding")
        self.assertEqual(template_rows[2]["Seller SKU"], "EG02230BD04-UK2")
        self.assertEqual(template_rows[3]["Seller SKU"], "EG02230BD06-UK2")

    def test_process_request_uses_listing_indexer_dict_output(self) -> None:
        self._create_template_workbook()
        uploads_dir = Path(self._uploads_dir.name)
        listings_file = uploads_dir / "UK_all_listings_test.txt"
        listings_file.write_text(
            "seller-sku\titem-name\tprice\tasin1\tgeneric keyword\n"
            "EG02230BK04-UK1\tBlack Maxi Dress 8UK\t19.99\tASIN123\tevening dress\n",
            encoding="utf-8",
        )

        category_files: list[str] = []
        for index in range(3):
            category_file = uploads_dir / f"UK_category_{index}.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Template"
            sheet.append(["SKU", "Item Name", "Colour", "Product Type", "bullet_point1"])
            sheet.append(["EG02230BK04-UK1", "Black Maxi Dress 8UK", "Black", "Dress", "Soft lining"])
            workbook.save(category_file)
            workbook.close()
            category_files.append(category_file.name)

        request = ProcessRequest(
            country=Country.UK,
            all_listings_file=listings_file.name,
            category_files=category_files,
            selected_prefixes=["EG02230"],
            target_colors=["SG"],
            start_size="04",
            end_size="04",
            size_step=1,
            mode="add-color",
        )

        result = AddColorSizeProcessor().process(request, output_filename="request-output")

        self.assertEqual(result.output_file, "request-output.xlsx")
        self.assertEqual(result.processed_count, 1)
        self.assertEqual(result.skipped_count, 0)

        output_path = Path(self._results_dir.name) / result.output_file
        _, rows = _template_rows(output_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Seller SKU"], "EG02230SG04-UK1")
        self.assertEqual(rows[0]["Colour"], "Sage Green")
        self.assertEqual(rows[0]["Colour Map"], "Green")
        self.assertEqual(rows[0]["Parent SKU"], "EG02230-UK1")

    def test_write_workbook_falls_back_to_blank_workbook_when_template_is_missing(self) -> None:
        headers = ["Seller SKU", "Colour", "main_image_url"]
        rows_by_suffix = {
            "-UK1": [{"Seller SKU": "SKU1", "Colour": "Royal Blue", "main_image_url": "https://example.com/1.jpg"}],
            "-UK2": [{"Seller SKU": "SKU2", "Colour": "Sage Green", "main_image_url": "https://example.com/2.jpg"}],
        }
        output_path = Path(self._results_dir.name) / "fallback-output.xlsx"

        AddColorSizeProcessor()._write_workbook(
            output_path=output_path,
            headers=headers,
            rows_by_suffix=rows_by_suffix,
            template_path=processor_module.TEMPLATES_DIR / "missing-template.xlsx",
        )

        workbook = load_workbook(output_path, read_only=True, data_only=True)
        try:
            self.assertEqual(workbook.sheetnames, ["-UK1", "-UK2"])
        finally:
            workbook.close()

        _, rows = _sheet_rows(output_path, "-UK1")
        self.assertEqual(rows[0]["Seller SKU"], "SKU1")
        self.assertEqual(rows[0]["main_image_url"], "https://example.com/1.jpg")

    def test_write_workbook_preserves_template_row_styles_for_new_rows(self) -> None:
        template_path = self._create_template_workbook()
        workbook = load_workbook(template_path)
        try:
            worksheet = workbook["Template"]
            orange_fill = PatternFill(fill_type="solid", fgColor="F4B183")
            bold_font = Font(name="Calibri", bold=True, color="9C0006")
            border = Border(left=Side(style="thin", color="C65911"), right=Side(style="thin", color="C65911"))
            alignment = Alignment(horizontal="center")

            styled_columns = (1, 2, 3, 4)
            for col_idx in styled_columns:
                cell = worksheet.cell(row=4, column=col_idx)
                cell.fill = orange_fill
                cell.font = bold_font
                cell.border = border
                cell.alignment = alignment
                cell.number_format = "@"

            workbook.save(template_path)
        finally:
            workbook.close()

        output_path = Path(self._results_dir.name) / "styled-output.xlsx"
        AddColorSizeProcessor()._write_workbook(
            output_path=output_path,
            headers=["Seller SKU", "Parent SKU", "Variation Theme", "Colour", "Colour Map"],
            rows_by_suffix={
                "-UK1": [
                    {
                        "Seller SKU": "SKU1",
                        "Parent SKU": "PARENT1",
                        "Variation Theme": "SizeName-ColorName",
                        "Colour": "Royal Blue",
                        "Colour Map": "Blue",
                    }
                ]
            },
            template_path=template_path,
        )

        styled_workbook = load_workbook(output_path)
        try:
            worksheet = styled_workbook["Template"]
            self.assertEqual(worksheet["A4"].fill.fgColor.rgb, "00F4B183")
            self.assertTrue(worksheet["A4"].font.bold)
            self.assertEqual(worksheet["A4"].alignment.horizontal, "center")
            self.assertEqual(worksheet["A4"].number_format, "@")
            self.assertEqual(worksheet["E4"].fill.fgColor.rgb, "00FCE4D6")
        finally:
            styled_workbook.close()


if __name__ == "__main__":
    unittest.main()
