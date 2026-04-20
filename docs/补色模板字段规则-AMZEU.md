# AMZEU 补色模板字段规则

来源文档：https://www.kdocs.cn/l/csWrfDljbvZM（AMZEU-AI加色加码跟卖）

---

## DE 必填字段细节梳理

**模板文件**: DE补色模板.xlsm  
**Marketplace ID**: A1PA6795UKMFR9  
**Language tag**: de_DE

| 输出表字段 | 映射表(源数据key) | 示例值 | 特殊字段 | 调整逻辑 | 映射来源 |
|---|---|---|---|---|---|
| feed_product_type | product_type#1.value | dress | – | 保留（映射） | Vorlage |
| item_sku | contribution_sku#1.value | ES01749SG04 | Y | 颜色/尺码变更 | Vorlage |
| brand_name | brand[A1PA6795UKMFR9][de_DE]#1.value | Ever-Pretty | – | 保留（映射） | Vorlage |
| **external_product_id** | **(无)** | **B0DB1XDXVP** | **Y** | **映射 FR 同 SKU 对应的 ASIN** | **FR--all listing** |
| item_name | item_name[A1PA6795UKMFR9][de_DE]#1.value | Ever-Pretty Women's... Sage Green 36 | Y | 颜色/尺码变更 | Vorlage |
| outer_material_type | outer[A1PA6795UKMFR9]#1.material[de_DE]#1.value | Synthetisch | – | 保留（映射） | Vorlage |
| lifecycle_supply_type | – | Fashion | – | 固定 | – |
| color_map | color[A1PA6795UKMFR9][de_DE]#1.standardized_values#1 | Green | Y | 更换 | 尺码映射关系+尺码规则 |
| color_name | color[A1PA6795UKMFR9][de_DE]#1.value | Sage Green | Y | 更换 | 尺码映射关系+尺码规则 |
| size_name | apparel_size[A1PA6795UKMFR9]#1.size | 36 | Y | 更换 | 尺码映射关系+尺码规则 |
| lifestyle | lifestyle[A1PA6795UKMFR9][de_DE]#1.value | Abendmode | – | 保留（映射） | Vorlage |
| pattern_type | – | Uni | – | 固定 | – |
| style_name | style[A1PA6795UKMFR9][de_DE]#1.value | Empire | – | 保留（映射） | Vorlage |
| neck_style | neck[A1PA6795UKMFR9]#1.neck_style[de_DE]#1.value | V-Neck | – | 保留（映射） | Vorlage |
| department_name | department[A1PA6795UKMFR9][de_DE]#1.value | Damen | – | 保留（映射） | Vorlage |
| size_map | apparel_size[A1PA6795UKMFR9]#1.size | 36 | Y | 更换 | 尺码映射关系+尺码规则 |
| item_length_description | item_length_description[A1PA6795UKMFR9][de_DE]#1.value | Maxi | – | 保留（映射） | Vorlage |
| fulfillment_center_id | – | DEFAULT | – | 固定 | – |
| is_adult_product | – | NO | – | 固定 | – |
| standard_price | Angebotspreis EUR (Bei Amazon verkaufen, DE) | 59.99 | – | 保留（映射） | Vorlage |
| quantity | – | 2 | – | 固定 | – |
| parent_child | – | Child | – | 固定 | – |
| parent_sku | child_parent_sku_relationship[A1PA6795UKMFR9]#1.parent_sku | ES01749 | – | 保留（映射） | Vorlage |
| relationship_type | – | Variation | – | 固定 | – |
| variation_theme | – | SizeName-ColorName | – | 固定 | – |
| update_delete | – | Aktualisierung | – | 固定 | – |
| product_description | product_description[A1PA6795UKMFR9][de_DE]#1.value | – | – | 保留（映射） | Vorlage |
| recommended_browse_nodes | – | Fashion > Damen > Bekleidung > Kleider > Abendkleider 等 | – | 映射 | Browse node mapping |
| apparel_size_system | apparel_size[A1PA6795UKMFR9]#1.size_system | DE / NL / SE / PL | – | 保留（映射） | Vorlage |
| target_gender | target_gender[A1PA6795UKMFR9]#1.value | Weiblich | – | 保留（映射） | Vorlage |
| age_range_description | age_range_description[A1PA6795UKMFR9][de_DE]#1.value | Erwachsener | – | 保留（映射） | Vorlage |
| apparel_size_class | apparel_size[A1PA6795UKMFR9]#1.size_class | Numerisch | – | 保留（映射） | Vorlage |
| apparel_size | apparel_size[A1PA6795UKMFR9]#1.size | 36 | Y | 颜色/尺码变更 | Vorlage |
| apparel_body_type | apparel_size[A1PA6795UKMFR9]#1.body_type | Regular | – | 保留（映射） | Vorlage |
| apparel_height_type | apparel_size[A1PA6795UKMFR9]#1.height_type | Regular | – | 保留（映射） | Vorlage |
| generic_keywords | generic_keyword[A1PA6795UKMFR9][de_DE]#1.value | (German keywords) | – | 保留（映射） | Vorlage |
| bullet_point1~5 | bullet_point[A1PA6795UKMFR9][de_DE]#1~5.value | – | – | 保留（映射） | Vorlage |
| sleeve_type | – | Kurzarm | – | 保留（映射） | Vorlage |
| package_length | – | 13 | – | 固定 | – |
| package_width | – | 9 | – | 固定 | – |
| package_height | – | 1 | – | 固定 | – |
| package_weight | – | 0.4 | – | 固定 | – |
| package_weight_unit_of_measure | – | KG | – | 固定 | – |
| package_dimensions_unit_of_measure | – | IN | – | 固定 | – |
| country_of_origin | – | China | – | 固定 | – |
| fabric_type | fabric_type[A1PA6795UKMFR9][de_DE]#1.value | 100% Polyester | – | 保留（映射） | Vorlage |
| batteries_required | – | NO | – | 固定 | – |
| supplier_declared_dg_hz_regulation1 | – | Nicht zutreffend | – | 固定 | – |
| condition_type | – | Neu | – | 固定 | – |
| list_price_with_tax | – | 69.99 | Y | 更改: =Your Price GBP (UK) + 10 | – |

### DE 特殊说明
- **尺码逻辑**：SKU 尺码 +32（UK size code → EU size，如 04 → 36）
- **ASIN 列**：匹配 FR 同 SKU 的 ASIN（从 FR all-listings 报告中查找）

---

## IT 必填字段细节梳理

**模板文件**: IT补色模板.xlsm
**Marketplace ID**: APJ6JRA9NG5V4
**Language tag**: it_IT

| 输出表字段 | 映射表(源数据key) | 示例值 | 特殊字段 | 调整逻辑 | 映射来源 |
|---|---|---|---|---|---|
| feed_product_type | product_type#1.value | dress | – | 保留（映射） | Modello |
| item_sku | – | EG01756MG04 | Y | 颜色/尺码变更 | Modello |
| brand_name | brand[APJ6JRA9NG5V4][it_IT]#1.value | Ever-Pretty | – | 保留（映射） | Modello |
| **external_product_id** | **(无)** | **B0DS1SSHJY** | **Y** | **映射 FR 同 SKU 对应的 ASIN** | **FR--all listing** |
| external_product_id_type | – | ASIN | – | 固定 | – |
| item_name | item_name[APJ6JRA9NG5V4][it_IT]#1.value | Ever-Pretty Vestito da Sera... Menta Verde 36 | Y | 颜色/尺码变更 | Modello |
| product_description | product_description[APJ6JRA9NG5V4][it_IT]#1.value | – | – | 保留（映射） | Modello |
| model | – | EG01756MG04 | Y | 颜色/尺码变更 | Modello |
| recommended_browse_nodes | – | 13901050031 / 13901049031 / 13901048031 | – | 映射 | Browse node mapping |
| outer_material_type | outer[APJ6JRA9NG5V4]#1.material[it_IT]#1.value | sintetico | – | 保留（映射） | Modello |
| care_instructions | care_instructions[APJ6JRA9NG5V4][it_IT]#1.value | Cura del vestito: lavare a mano... | – | 保留（映射） | Modello |
| standard_price | Prezzo EUR (Vendita su Amazon, IT) | 54.99 | – | 保留（映射） | Modello |
| quantity | – | 2 | – | 固定 | – |
| target_gender | target_gender[APJ6JRA9NG5V4]#1.value | Femmina | – | 保留（映射） | Modello |
| age_range_description | age_range_description[APJ6JRA9NG5V4][it_IT]#1.value | Adulto | – | 保留（映射） | Modello |
| apparel_size_system | apparel_size[APJ6JRA9NG5V4]#1.size_system | IT | – | 保留（映射） | Modello |
| apparel_size_class | apparel_size[APJ6JRA9NG5V4]#1.size_class | Numero | – | 保留（映射） | Modello |
| apparel_size | apparel_size[APJ6JRA9NG5V4]#1.size | 36 | Y | 颜色/尺码变更 | Modello |
| apparel_body_type | apparel_size[APJ6JRA9NG5V4]#1.body_type | Regular | – | 保留（映射） | Modello |
| apparel_height_type | apparel_size[APJ6JRA9NG5V4]#1.height_type | Regular | – | 保留（映射） | Modello |
| parent_child | – | Child | – | 固定 | – |
| parent_sku | child_parent_sku_relationship[APJ6JRA9NG5V4]#1.parent_sku | EG01756 | – | 保留（映射） | Modello |
| relationship_type | – | Variation | – | 固定 | – |
| variation_theme | – | SizeName-ColorName | – | 固定 | – |
| package_level | – | unit | – | 固定 | – |
| color_map | color[APJ6JRA9NG5V4][it_IT]#1.standardized_values#1 | verde | Y | 更换（意大利语色系名） | 颜色映射 |
| color_name | color[APJ6JRA9NG5V4][it_IT]#1.value | Menta Verde | Y | 更换 | 颜色映射 |
| size_name | apparel_size[APJ6JRA9NG5V4]#1.size | 36 | Y | 更换 | 尺码规则 |
| update_delete | – | Aggiorna | – | 固定 | – |
| generic_keywords | generic_keyword[APJ6JRA9NG5V4][it_IT]#1.value | abito da sposa... | – | 保留（映射） | Modello |
| bullet_point1~5 | bullet_point[APJ6JRA9NG5V4][it_IT]#1~5.value | – | – | 保留（映射） | Modello |
| pattern_type | – | tinta unita | – | 固定 | – |
| lifestyle | lifestyle[APJ6JRA9NG5V4][it_IT]#1.value | Sera | – | 保留（映射） | Modello |
| style_name | style[APJ6JRA9NG5V4][it_IT]#1.value | stile impero | – | 保留（映射） | Modello |
| department_name | department[APJ6JRA9NG5V4][it_IT]#1.value | Donna | – | 保留（映射） | Modello |
| neck_style | neck[APJ6JRA9NG5V4]#1.neck_style[it_IT]#1.value | a v | – | 保留（映射） | Modello |
| material_type | material_type[APJ6JRA9NG5V4][it_IT]#1.value | 100%Polyester | – | 保留（映射） | Modello |
| lifecycle_supply_type | – | Fashion | – | 固定 | – |
| sleeve_type | sleeve[APJ6JRA9NG5V4]#1.type[it_IT]#1.value | manica corta | – | 保留（映射） | Modello |
| size_map | apparel_size[APJ6JRA9NG5V4]#1.size | 36 | Y | 更换 | 尺码规则 |
| item_length_description | item_length_description[APJ6JRA9NG5V4][it_IT]#1.value | midi | – | 保留（映射） | Modello |
| package_length | – | 13.00 | – | 固定 | – |
| package_width | – | 9.00 | – | 固定 | – |
| package_height | – | 1.00 | – | 固定 | – |
| package_length_unit_of_measure | – | IN | – | 固定 | – |
| package_height_unit_of_measure | – | IN | – | 固定 | – |
| package_width_unit_of_measure | – | IN | – | 固定 | – |
| package_weight | – | 500.00 | – | 固定 | – |
| package_weight_unit_of_measure | – | GR | – | 固定 | – |
| country_of_origin | – | Cina | – | 固定 | – |
| batteries_required | – | No | – | 固定 | – |
| are_batteries_included | – | No | – | 固定 | – |
| fabric_type | fabric_type[APJ6JRA9NG5V4][it_IT]#1.value | Chiffon | – | 保留（映射） | Modello |
| supplier_declared_material_regulation1 | – | Non applicabile | – | 固定 | – |
| list_price_with_tax | – | 62.99 | Y | 更改: =Prezzo EUR (IT) + 10 | – |
| condition_type | – | Nuovo | – | 固定 | – |

### IT 特殊说明
- **尺码逻辑**：SKU 尺码 +32（如 04 → 36）
- **ASIN 列**：匹配 FR 同 SKU 的 ASIN（从 FR all-listings 报告中查找）
- **package_weight 单位**：GR（克），值为 500.00（非 KG）
- **package_dimensions 单位**：IN（英寸）
- **IT 独有字段**：`package_level = unit`、`supplier_declared_material_regulation1`（DE 用的是 `supplier_declared_dg_hz_regulation1`）
- **country_of_origin**：IT 用 `Cina`（意大利语），DE 用 `China`

### IT Browse Node 映射参考
| 类目 | Node ID |
|---|---|
| Moda > Donna > Abbigliamento > Vestiti > Sera e Cerimonia | 13901050031 |
| Moda > Donna > Abbigliamento > Vestiti > Cocktail | 13901049031 |
| Moda > Donna > Abbigliamento > Vestiti > Casual | 13901048031 |
| Moda > Donna > Abbigliamento > Vestiti > Sposa | 2893181031 |

---

## FR 必填字段细节梳理

**模板文件**: FR补色模板.xlsm
**Marketplace ID**: A13V1IB3VIYZZH
**Language tag**: fr_FR

| 输出表字段 | 映射表(源数据key) | 示例值 | 特殊字段 | 调整逻辑 | 映射来源 |
|---|---|---|---|---|---|
| feed_product_type | Type de produit | dress | – | 保留（映射） | Modèle |
| item_sku | SKU | ES01749SG04 | Y | 颜色/尺码变更 | Modèle |
| brand_name | Marque | Ever-Pretty | – | 保留（映射） | Modèle |
| item_name | Nom de l'article | Ever-Pretty Women's... Sage Green 36 | Y | 颜色/尺码变更 | Modèle |
| outer_material_type | Outer Material | Synthetic | – | 保留（映射） | Modèle |
| material_composition | Type de tissu | Polyester | – | 保留（映射） | Modèle |
| color_map | Couleur dominante | Vert | Y | 更换（法语色系名） | 颜色映射 |
| color_name | Couleur | Sage Green | Y | 更换 | 颜色映射 |
| size_name | Taille du vêtement | 36 | Y | 更换 | 尺码规则 |
| lifestyle | Style de vie | Soirée | – | 保留（映射） | Modèle |
| pattern_type | – | Unie | – | 固定 | – |
| style_name | Style | Taille empire | – | 保留（映射） | Modèle |
| neck_style | Style de col | V-Neck | – | 保留（映射） | Modèle |
| department_name | Nom de la boutique | Femme | – | 保留（映射） | Modèle |
| size_map | Taille du vêtement | 36 | Y | 更换 | 尺码规则 |
| item_length_description | Description de la longueur | Maxi | – | 保留（映射） | Modèle |
| is_adult_product | – | Non | – | 固定 | – |
| standard_price | Votre prix EUR (Vendez sur Amazon, FR) | 59.99 | – | 保留（映射） | Modèle |
| quantity | – | 2 | – | 固定 | – |
| main_image_url | main_product_image_locator[A13V1IB3VIYZZH]#1.media_location | .../ES01749BK-L1.jpg | Y | 颜色替换 | 颜色映射 |
| other_image_url1 | other_product_image_locator_1[A13V1IB3VIYZZH]#1.media_location | .../ES01749BK-L2.jpg | Y | 颜色替换 | 颜色映射 |
| other_image_url2 | other_product_image_locator_2[A13V1IB3VIYZZH]#1.media_location | .../ES01749BK-L3.jpg | Y | 颜色替换 | 颜色映射 |
| other_image_url3 | other_product_image_locator_3[A13V1IB3VIYZZH]#1.media_location | .../ES01749BK-L4.jpg | Y | 颜色替换 | 颜色映射 |
| other_image_url4 | other_product_image_locator_4[A13V1IB3VIYZZH]#1.media_location | .../ES01749BK-L5.jpg | Y | 颜色替换 | 颜色映射 |
| other_image_url5 | other_product_image_locator_5[A13V1IB3VIYZZH]#1.media_location | .../EE02665-S-EU.jpg | Y | 颜色替换 | 颜色映射 |
| parent_child | – | Child | – | 固定 | – |
| parent_sku | SKU parent | ES01749 | – | 保留（映射） | Modèle |
| relationship_type | – | Variation | – | 固定 | – |
| variation_theme | – | SizeName-ColorName | – | 固定 | – |
| update_delete | – | Actualisation | – | 固定 | – |
| product_description | Description du produit | – | – | 保留（映射） | Modèle |
| recommended_browse_nodes | – | 13880102031 / 13880101031 / 13880100031 | – | 映射 | Browse node mapping |
| care_instructions | Conseils d'Entretien | Lavage à la main... | – | 保留（映射） | Modèle |
| model_name | Numéro du modèle | ES01749SG04 | Y | 颜色/尺码变更 | Modèle |
| model | – | ES01749SG04 | Y | 颜色/尺码变更 | Modèle |
| part_number | – | ES01749SG04 | Y | 颜色/尺码变更 | Modèle |
| apparel_size_system | Système de taille | FR / ES | – | 保留（映射） | Modèle |
| target_gender | Sexe ciblé | Féminin | – | 保留（映射） | Modèle |
| age_range_description | Description de la tranche d'âge | Adulte | – | 保留（映射） | Modèle |
| apparel_size_class | Classification des tailles | Numérique | – | 保留（映射） | Modèle |
| apparel_size | Taille du vêtement | 36 | Y | 颜色/尺码变更 | Modèle |
| apparel_body_type | Type de morphologie | Taille normale | – | 保留（映射） | Modèle |
| apparel_height_type | Type de taille | Taille normale | – | 保留（映射） | Modèle |
| generic_keywords | – | robe femme chic... | – | 保留（映射） | Modèle |
| bullet_point1~5 | bullet_point[A13V1IB3VIYZZH][fr_FR]#1~5.value | – | – | 保留（映射） | Modèle |
| sleeve_type | Type de manches | – | – | 保留（映射） | Modèle |
| closure_type | Type de fermeture | fermeture à glissière dissimulée | – | 保留（映射） | Modèle |
| package_length | – | 13 | – | 固定 | – |
| package_width | – | 9 | – | 固定 | – |
| package_height | – | 1 | – | 固定 | – |
| package_weight | – | 0.4 | – | 固定 | – |
| package_weight_unit_of_measure | – | KG | – | 固定 | – |
| package_dimensions_unit_of_measure | – | IN | – | 固定 | – |
| country_of_origin | – | Chine | – | 固定 | – |
| fabric_type | Type de tissu | 100% Polyester | – | 保留（映射） | Modèle |
| batteries_required | – | No | – | 固定 | – |
| are_batteries_included | – | No | – | 固定 | – |
| supplier_declared_dg_hz_regulation1 | – | Not Applicable | – | 固定 | – |
| condition_type | État de l'article | Neuf | – | 固定 | – |
| list_price_with_tax | – | 69.99 | Y | 更改: =Votre prix EUR (FR) + 10 | – |

### FR 特殊说明
- **尺码逻辑**：SKU 尺码 +32（如 04 → 36）
- **FR 不需要 ASIN 映射**：FR 本身就是 FR marketplace，external_product_id 字段无需额外处理
- **country_of_origin**：FR 用 `Chine`（法语）
- **pattern_type**：FR 用 `Unie`（非 DE 的 `Uni`、IT 的 `tinta unita`）
- **is_adult_product**：FR 用 `Non`（法语 No）
- **supplier_declared_dg_hz_regulation1**：FR 用 `Not Applicable`（英语，非 DE 的 `Nicht zutreffend`）
- **color_map**：FR 用**法语**色系名（Vert、Rouge 等），与 DE/IT 一致
- **图片顺序**：main=L1, other1=L2, other2=L3, other3=L4, other4=L5, other5=S-EU（比 DE/IT 多一张 L2）
- **FR 独有字段**：`material_composition`、`closure_type`

### FR Browse Node 映射参考
| 类目 | Node ID |
|---|---|
| Mode > Femme > Vêtements > Robes > Soirée | 13880102031 |
| Mode > Femme > Vêtements > Robes > Cocktail | 13880101031 |
| Mode > Femme > Vêtements > Robes > Casual | 13880100031 |

---

## ES

待补充（用户提供字段规则后整理）

---

## 字段调整逻辑说明

- **保留（映射）**：直接从源数据（Vorlage = 模板/源文件）读取，不修改
- **固定**：写入硬编码的固定值
- **颜色/尺码变更**：根据新颜色和尺码生成对应值
- **更换**：根据尺码映射关系和尺码规则替换
- **映射**：根据映射表（如 browse node mapping）转换
- **更改**：按特定公式计算（如 list_price_with_tax = UK price + 10）
