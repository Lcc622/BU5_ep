export interface ParsedDirectSku {
  normalized: string;
  productCode: string;
  colorCode: string;
  sizeCode: string;
}

export interface DirectSkuParseResult {
  entries: ParsedDirectSku[];
  uniqueSkus: string[];
  productCodes: string[];
  colorCodes: string[];
  invalidEntries: string[];
  duplicateCount: number;
}

const DIRECT_SKU_SEPARATOR_REGEX = /[\s,，、;；]+/;
const DIRECT_SKU_REGEX = /^([A-Z0-9]{7,8})([A-Z0-9]{2})(\d{2})(?:-([A-Z0-9]{2,4}))?$/;

export const splitDirectSkuText = (value: string) =>
  value
    .split(DIRECT_SKU_SEPARATOR_REGEX)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);

export const parseDirectSkuText = (value: string): DirectSkuParseResult => {
  const tokens = splitDirectSkuText(value);
  const entries: ParsedDirectSku[] = [];
  const invalidEntries: string[] = [];
  const uniqueSkuSet = new Set<string>();
  const productCodeSet = new Set<string>();
  const colorCodeSet = new Set<string>();

  for (const token of tokens) {
    const match = token.match(DIRECT_SKU_REGEX);
    if (!match) {
      invalidEntries.push(token);
      continue;
    }

    const normalized = token;
    const productCode = match[1];
    const colorCode = match[2];
    const sizeCode = match[3];

    entries.push({
      normalized,
      productCode,
      colorCode,
      sizeCode,
    });

    uniqueSkuSet.add(normalized);
    productCodeSet.add(productCode);
    colorCodeSet.add(colorCode);
  }

  return {
    entries,
    uniqueSkus: [...uniqueSkuSet],
    productCodes: [...productCodeSet],
    colorCodes: [...colorCodeSet],
    invalidEntries,
    duplicateCount: entries.length - uniqueSkuSet.size,
  };
};
