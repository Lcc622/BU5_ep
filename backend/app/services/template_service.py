"""模板服务骨架。"""

from pathlib import Path

from app.config import BASE_DIR, Country
from app.core.profiles.country_profiles import get_profile


class TemplateService:
    """提供模板路径查询。"""

    def get_template_path(self, country: Country) -> Path:
        profile = get_profile(country.value if isinstance(country, Country) else str(country))
        template_path = BASE_DIR / "templates" / profile.template_file
        if template_path.exists():
            return template_path
        raise NotImplementedError(f"Template file not found yet: {template_path}")
