"""国家配置访问层。"""

from app.config import COUNTRY_PROFILES, Country, CountryProfile


def get_profile(country: str) -> CountryProfile:
    """根据国家代码获取国家配置。"""
    normalized = country.upper()
    try:
        return COUNTRY_PROFILES[Country(normalized)]
    except (KeyError, ValueError) as exc:
        supported = ", ".join(item.value for item in Country)
        raise KeyError(f"Unsupported country '{country}'. Supported countries: {supported}") from exc
