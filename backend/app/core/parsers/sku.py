"""SKU 解析器。"""

from dataclasses import dataclass
import re

SUFFIX_PATTERN = re.compile(r"(-[A-Z]{1,2}\d?)$")


@dataclass(frozen=True, slots=True)
class SKUInfo:
    """解析后的 SKU 信息。"""

    product_code: str
    color_code: str
    size_code: str
    suffix: str | None
    raw_sku: str


def parse_sku(raw_sku: str) -> SKUInfo:
    """解析欧洲站 SKU，支持 7 位或 8 位产品码，后缀可选。"""
    sku = raw_sku.strip().upper()
    if not sku:
        raise ValueError("SKU cannot be empty")

    suffix_match = SUFFIX_PATTERN.search(sku)
    if suffix_match:
        suffix: str | None = suffix_match.group(0)
        base = sku[: suffix_match.start()]
    else:
        suffix = None
        base = sku

    if len(base) < 11:
        raise ValueError(f"SKU is too short to parse: {raw_sku}")

    size_code = base[-2:]
    color_code = base[-4:-2]
    product_code = base[:-4]

    if len(product_code) not in (7, 8):
        raise ValueError(f"Unsupported product code length in SKU: {raw_sku}")
    if not product_code.isalnum():
        raise ValueError(f"Invalid product code in SKU: {raw_sku}")
    if not color_code.isalpha():
        raise ValueError(f"Invalid color code in SKU: {raw_sku}")
    if not size_code.isalnum():
        raise ValueError(f"Invalid size code in SKU: {raw_sku}")

    return SKUInfo(
        product_code=product_code,
        color_code=color_code,
        size_code=size_code,
        suffix=suffix,
        raw_sku=raw_sku,
    )
