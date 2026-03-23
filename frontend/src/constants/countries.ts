import type { Country, TemplateInfo } from '../types/api';

export const COUNTRIES: Array<{
  code: Country;
  label: string;
  flag: string;
  locale: string;
  categoryReportCount: number;
  perStoreCategoryCount: number;
}> = [
  { code: 'UK', label: 'United Kingdom', flag: '🇬🇧', locale: 'en-GB', categoryReportCount: 3, perStoreCategoryCount: 0 },
  { code: 'FR', label: 'France', flag: '🇫🇷', locale: 'fr-FR', categoryReportCount: 4, perStoreCategoryCount: 2 },
  { code: 'DE', label: 'Germany', flag: '🇩🇪', locale: 'de-DE', categoryReportCount: 4, perStoreCategoryCount: 2 },
  { code: 'IT', label: 'Italy', flag: '🇮🇹', locale: 'it-IT', categoryReportCount: 4, perStoreCategoryCount: 2 },
  { code: 'ES', label: 'Spain', flag: '🇪🇸', locale: 'es-ES', categoryReportCount: 4, perStoreCategoryCount: 2 },
];

export const TEMPLATE_MAP: Record<Country, TemplateInfo> = {
  UK: { country: 'UK', template_name: 'AMZEU_UK_AddColor_Template.xlsx', required_category_reports: 3 },
  FR: { country: 'FR', template_name: 'AMZEU_FR_AddColor_Template.xlsx', required_category_reports: 4 },
  DE: { country: 'DE', template_name: 'AMZEU_DE_AddColor_Template.xlsx', required_category_reports: 4 },
  IT: { country: 'IT', template_name: 'AMZEU_IT_AddColor_Template.xlsx', required_category_reports: 4 },
  ES: { country: 'ES', template_name: 'AMZEU_ES_AddColor_Template.xlsx', required_category_reports: 4 },
};

export const getCountryMeta = (country: Country) =>
  COUNTRIES.find((item) => item.code === country) ?? COUNTRIES[0];
