"""颜色映射服务。"""

from app.core.color_mapper import color_mapper


class MappingService:
    def get_all(self) -> dict[str, dict[str, str]]:
        return color_mapper.get_all_mappings()

    def upsert(self, code: str, names: dict[str, str]) -> None:
        color_mapper.set_mapping(code, names)

    def delete(self, code: str) -> bool:
        return color_mapper.delete_mapping(code)
