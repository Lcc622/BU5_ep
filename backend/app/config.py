"""配置管理模块。"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Country(str, Enum):
    """支持的欧洲站国家。"""

    UK = "UK"
    FR = "FR"
    DE = "DE"
    IT = "IT"
    ES = "ES"


@dataclass(frozen=True, slots=True)
class CountryProfile:
    """国家配置。"""

    country: str
    template_file: str
    marketplace_id: str
    currency: str
    language_tag: str
    required_category_reports: int
    image_suffix_main: str
    image_suffixes_other: list[str]
    size_offset: int


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"
RESULTS_DIR = BASE_DIR / "results"

for directory in (DATA_DIR, UPLOADS_DIR, RESULTS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

COLOR_MAPPING_FILE = DATA_DIR / "colorMapping.json"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

COUNTRY_PROFILES: dict[Country, CountryProfile] = {
    Country.UK: CountryProfile(
        country="UK",
        template_file="AMZEU_UK_AddColor_Template.xlsx",
        marketplace_id="A1F83G8C2ARO7P",
        currency="GBP",
        language_tag="en_GB",
        required_category_reports=3,
        image_suffix_main="-L",
        image_suffixes_other=["-L1", "-L5", "-L3", "-L4", "-S-UK"],
        size_offset=4,
    ),
    Country.FR: CountryProfile(
        country="FR",
        template_file="FR补色模板.xlsx",
        marketplace_id="A13V1IB3VIYZZH",
        currency="EUR",
        language_tag="fr_FR",
        required_category_reports=2,
        image_suffix_main="-L",
        image_suffixes_other=["-L1", "-L5", "-L3", "-L4", "-S-FR"],
        size_offset=0,
    ),
    Country.DE: CountryProfile(
        country="DE",
        template_file="DE补色模板.xlsx",
        marketplace_id="A1PA6795UKMFR9",
        currency="EUR",
        language_tag="de_DE",
        required_category_reports=2,
        image_suffix_main="-L",
        image_suffixes_other=["-L1", "-L5", "-L3", "-L4", "-S-DE"],
        size_offset=0,
    ),
    Country.IT: CountryProfile(
        country="IT",
        template_file="IT补色模板.xlsx",
        marketplace_id="APJ6JRA9NG5V4",
        currency="EUR",
        language_tag="it_IT",
        required_category_reports=2,
        image_suffix_main="-L",
        image_suffixes_other=["-L1", "-L5", "-L3", "-L4", "-S-IT"],
        size_offset=0,
    ),
    Country.ES: CountryProfile(
        country="ES",
        template_file="ES上新模板.xlsx",
        marketplace_id="A1RKKUPIHCS9HS",
        currency="EUR",
        language_tag="es_ES",
        required_category_reports=2,
        image_suffix_main="-L",
        image_suffixes_other=["-L1", "-L5", "-L3", "-L4", "-S-ES"],
        size_offset=0,
    ),
}
