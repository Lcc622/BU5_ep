"""将 colorMapping.json 从单语言格式迁移到多语言格式。"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLOR_MAPPING_FILE = DATA_DIR / "colorMapping.json"

# 常用颜色的多语言翻译表
TRANSLATIONS: dict[str, dict[str, str]] = {
    "BK": {"fr": "Noir", "de": "Schwarz", "it": "Nero", "es": "Negro"},
    "PK": {"fr": "Rose", "de": "Rosa", "it": "Rosa", "es": "Rosa"},
    "BH": {"fr": "Rose Blush", "de": "Blush", "it": "Rosa Cipria", "es": "Rosa Empolvado"},
    "HP": {"fr": "Rose Vif", "de": "Pink", "it": "Rosa Acceso", "es": "Rosa Fuerte"},
    "CO": {"fr": "Corail", "de": "Koralle", "it": "Corallo", "es": "Coral"},
    "RD": {"fr": "Rouge", "de": "Rot", "it": "Rosso", "es": "Rojo"},
    "BD": {"fr": "Bordeaux", "de": "Burgunder", "it": "Bordeaux", "es": "Burdeos"},
    "IB": {"fr": "Bleu Glace", "de": "Eisblau", "it": "Azzurro Ghiaccio", "es": "Azul Hielo"},
    "BL": {"fr": "Bleu Ciel", "de": "Himmelblau", "it": "Azzurro", "es": "Azul Cielo"},
    "AQ": {"fr": "Aqua", "de": "Aqua", "it": "Acqua", "es": "Agua"},
    "SB": {"fr": "Bleu Saphir", "de": "Saphirblau", "it": "Blu Zaffiro", "es": "Azul Zafiro"},
    "NB": {"fr": "Bleu Marine", "de": "Marineblau", "it": "Blu Navy", "es": "Azul Marino"},
    "IN": {"fr": "Indigo", "de": "Indigo", "it": "Indaco", "es": "Índigo"},
    "MN": {"fr": "Marine Nuit", "de": "Mitternachtsblau", "it": "Blu Notte", "es": "Azul Medianoche"},
    "MG": {"fr": "Vert Menthe", "de": "Mintgrün", "it": "Verde Menta", "es": "Verde Menta"},
    "EM": {"fr": "Vert Émeraude", "de": "Smaragdgrün", "it": "Verde Smeraldo", "es": "Verde Esmeralda"},
    "DG": {"fr": "Vert Foncé", "de": "Dunkelgrün", "it": "Verde Scuro", "es": "Verde Oscuro"},
    "TQ": {"fr": "Turquoise", "de": "Türkis", "it": "Turchese", "es": "Turquesa"},
    "GR": {"fr": "Vert", "de": "Grün", "it": "Verde", "es": "Verde"},
    "LV": {"fr": "Lavande", "de": "Lavendel", "it": "Lavanda", "es": "Lavanda"},
    "PW": {"fr": "Bleu Pervenche", "de": "Blauviolett", "it": "Pervinca", "es": "Azul Pervinca"},
    "DP": {"fr": "Violet Foncé", "de": "Dunkelviolett", "it": "Viola Scuro", "es": "Morado Oscuro"},
    "PP": {"fr": "Violet", "de": "Lila", "it": "Viola", "es": "Morado"},
    "YL": {"fr": "Jaune", "de": "Gelb", "it": "Giallo", "es": "Amarillo"},
    "WH": {"fr": "Blanc", "de": "Weiß", "it": "Bianco", "es": "Blanco"},
    "CR": {"fr": "Crème", "de": "Creme", "it": "Crema", "es": "Crema"},
    "MR": {"fr": "Champignon", "de": "Pilzbraun", "it": "Fungo", "es": "Seta"},
    "GY": {"fr": "Gris", "de": "Grau", "it": "Grigio", "es": "Gris"},
    "MB": {"fr": "Bleu Nuit", "de": "Mitternachtsblau", "it": "Blu Mezzanotte", "es": "Azul Medianoche"},
    "OR": {"fr": "Orange", "de": "Orange", "it": "Arancione", "es": "Naranja"},
    "BR": {"fr": "Marron", "de": "Braun", "it": "Marrone", "es": "Marrón"},
    "BG": {"fr": "Beige", "de": "Beige", "it": "Beige", "es": "Beige"},
    "CH": {"fr": "Charbon", "de": "Anthrazit", "it": "Antracite", "es": "Antracita"},
    "SL": {"fr": "Ardoise", "de": "Schiefer", "it": "Ardesia", "es": "Pizarra"},
    "TN": {"fr": "Bronzé", "de": "Gebräunt", "it": "Abbronzato", "es": "Tostado"},
    "OL": {"fr": "Olive", "de": "Olivgrün", "it": "Oliva", "es": "Oliva"},
    "RS": {"fr": "Rouille", "de": "Rost", "it": "Ruggine", "es": "Óxido"},
    "TL": {"fr": "Sarcelle", "de": "Blaugrün", "it": "Ottanio", "es": "Cerceta"},
    "PL": {"fr": "Prune", "de": "Pflaume", "it": "Prugna", "es": "Ciruela"},
    "MW": {"fr": "Blanc Cassé", "de": "Gebrochenes Weiß", "it": "Bianco Sporco", "es": "Blanco Roto"},
    "SK": {"fr": "Nude", "de": "Hautfarben", "it": "Nude", "es": "Nude"},
    "DW": {"fr": "Blanc Sale", "de": "Schmutzigweiß", "it": "Bianco Sporco", "es": "Blanco Sucio"},
    "LB": {"fr": "Bleu Clair", "de": "Hellblau", "it": "Azzurro Chiaro", "es": "Azul Claro"},
    "LP": {"fr": "Violet Clair", "de": "Hellviolett", "it": "Viola Chiaro", "es": "Lila Claro"},
    "LG": {"fr": "Vert Clair", "de": "Hellgrün", "it": "Verde Chiaro", "es": "Verde Claro"},
    "LY": {"fr": "Jaune Clair", "de": "Hellgelb", "it": "Giallo Chiaro", "es": "Amarillo Claro"},
    "LR": {"fr": "Rouge Clair", "de": "Hellrot", "it": "Rosso Chiaro", "es": "Rojo Claro"},
    "LN": {"fr": "Lin", "de": "Leinen", "it": "Lino", "es": "Lino"},
    "TW": {"fr": "Pied-de-Poule", "de": "Tweed", "it": "Tweed", "es": "Tweed"},
    "PT": {"fr": "Imprimé", "de": "Gemustert", "it": "Fantasia", "es": "Estampado"},
    "ST": {"fr": "Rayé", "de": "Gestreift", "it": "A Righe", "es": "A Rayas"},
}


def migrate():
    with COLOR_MAPPING_FILE.open("r", encoding="utf-8") as f:
        old: dict = json.load(f)

    # 已经是多语言格式则跳过
    first_val = next(iter(old.values()), None)
    if isinstance(first_val, dict):
        print("已经是多语言格式，无需迁移。")
        return

    new: dict[str, dict[str, str]] = {}
    for code, en_name in old.items():
        extra = TRANSLATIONS.get(code, {})
        new[code] = {
            "en": en_name,
            "fr": extra.get("fr", ""),
            "de": extra.get("de", ""),
            "it": extra.get("it", ""),
            "es": extra.get("es", ""),
        }

    # 备份原文件
    backup = COLOR_MAPPING_FILE.with_suffix(".json.bak")
    backup.write_bytes(COLOR_MAPPING_FILE.read_bytes())
    print(f"已备份原文件到 {backup}")

    with COLOR_MAPPING_FILE.open("w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)

    print(f"迁移完成，共 {len(new)} 个颜色码已转换为多语言格式。")


if __name__ == "__main__":
    migrate()
