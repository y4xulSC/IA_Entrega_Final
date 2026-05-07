# Diccionario de Datos — Sistema IA Café Colombia
## Base de Datos: `cafe_ia` · PostgreSQL 18.3

**Esquema:** `cafe`
**Codificación:** UTF-8
**Convenciones:** snake_case, claves primarias `id`, FKs `<entidad>_id`

---

## 1. Esquema lógico (Modelo Estrella)

```
                ┌──────────────────────┐
                │  dim_departamento    │
                │  ──────────────      │
                │  PK id_departamento  │◄────┐
                │  codigo_dane         │     │
                │  nombre              │     │
                │  region              │     │
                └──────────────────────┘     │
                                             │
┌──────────────────────┐    ┌──────────────────────┐
│  dim_municipio       │    │  fact_produccion     │
│  ─────────────       │    │  ─────────────       │
│  PK id_municipio     │◄───┤  FK id_municipio     │
│  codigo_dane         │    │  FK id_periodo       │
│  nombre              │    │  area_sembrada_ha    │
│  FK id_departamento  │    │  area_cosechada_ha   │
│  altitud_msnm        │    │  produccion_ton      │
│  lat, lon            │    │  rendimiento_ton_ha  │
│  zona_cafetera       │    │  estado_fisico       │
└──────────────────────┘    └──────────────────────┘
        │
        │
        ▼
┌──────────────────────┐    ┌──────────────────────┐
│  fact_clima          │    │  dim_periodo         │
│  ───────────         │    │  ─────────────       │
│  FK id_municipio     │    │  PK id_periodo       │
│  FK id_periodo       │    │  fecha               │
│  temp_media_c        │    │  anio                │
│  temp_min_c          │    │  mes                 │
│  temp_max_c          │    │  semestre            │
│  precipitacion_mm    │    │  trimestre           │
│  oni                 │    │  fase_enso           │
└──────────────────────┘    └──────────────────────┘

┌──────────────────────┐    ┌──────────────────────┐
│  fact_precio         │    │  dim_imagen_enferm   │
│  ───────────         │    │  ─────────────       │
│  FK id_periodo       │    │  PK id_imagen        │
│  precio_fnc_cop_125kg│    │  ruta_archivo        │
│  precio_ico_usd_lb   │    │  enfermedad          │
│  precio_brasil_fred  │    │  parte_planta        │
│  precio_robusta_fred │    │  severidad_pct       │
│  fnc_cosecha_60kg    │    │  fuente_dataset      │
│  fnc_export_60kg     │    │  resolucion          │
└──────────────────────┘    └──────────────────────┘
```

---

## 2. Tablas dimensionales

### `dim_departamento`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_departamento | SERIAL | PK | ID interno |
| codigo_dane | VARCHAR(2) | NOT NULL UNIQUE | Código DANE 2 dígitos (ej: "41" Huila) |
| nombre | VARCHAR(50) | NOT NULL | Nombre oficial |
| region | VARCHAR(20) | | Andina/Caribe/Pacífico/Orinoquía/Amazonía |
| es_cafetero | BOOLEAN | DEFAULT false | Si está en zona cafetera principal |

**Datos esperados:** ~33 departamentos

### `dim_municipio`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_municipio | SERIAL | PK | ID interno |
| codigo_dane | VARCHAR(5) | NOT NULL UNIQUE | Código DANE 5 dígitos |
| nombre | VARCHAR(80) | NOT NULL | Nombre oficial municipio |
| id_departamento | INT | FK → dim_departamento | |
| altitud_msnm | NUMERIC(6,1) | | Altitud media (DEM SRTM) |
| lat | NUMERIC(8,5) | | Latitud centroide |
| lon | NUMERIC(8,5) | | Longitud centroide |
| zona_cafetera | VARCHAR(20) | | Norte/Centro/Sur (FNC) |
| area_total_ha | NUMERIC(12,2) | | Área total municipio |

**Datos esperados:** ~600 municipios cafeteros (de 1103 totales)

### `dim_periodo`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_periodo | SERIAL | PK | ID interno |
| fecha | DATE | NOT NULL UNIQUE | Primer día del periodo |
| anio | INT | NOT NULL | Año |
| mes | INT | | Mes (1-12), NULL si periodo anual |
| semestre | INT | | 1 o 2 |
| trimestre | INT | | 1-4 |
| oni | NUMERIC(4,2) | | Índice ONI mensual |
| fase_enso | VARCHAR(10) | CHECK (fase_enso IN ('Nino','Nina','Neutro')) | Fase ENSO |
| es_cosecha | BOOLEAN | | Si es periodo de cosecha cafetera (Mar-Jun, Sep-Dic) |

**Datos esperados:** 1990-2026 mensual ≈ 444 registros

### `dim_variedad_cafe`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_variedad | SERIAL | PK | |
| nombre | VARCHAR(50) | UNIQUE | Caturra, Castillo, Colombia, Bourbon... |
| especie | VARCHAR(20) | | Arábica/Robusta |
| resistencia_roya | VARCHAR(15) | | Alta/Media/Baja |
| altitud_optima_min | INT | | msnm |
| altitud_optima_max | INT | | msnm |

### `dim_enfermedad`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_enfermedad | SERIAL | PK | |
| nombre | VARCHAR(50) | UNIQUE | Roya, Gotera, Cercospora, Phoma, Miner |
| nombre_cientifico | VARCHAR(80) | | Hemileia vastatrix, Phoma costarricensis... |
| sintomas | TEXT | | |
| color_lesion | VARCHAR(30) | | Naranja, marrón, gris... |

---

## 3. Tablas de hechos

### `fact_produccion` (EVA)

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_produccion | BIGSERIAL | PK | |
| id_municipio | INT | FK NOT NULL | |
| id_periodo | INT | FK NOT NULL | |
| id_variedad | INT | FK NULL | NULL si no se discrimina |
| area_sembrada_ha | NUMERIC(12,2) | CHECK >= 0 | |
| area_cosechada_ha | NUMERIC(12,2) | CHECK >= 0 | |
| produccion_ton | NUMERIC(14,2) | CHECK >= 0 | |
| rendimiento_ton_ha | NUMERIC(8,4) | | Calculado o reportado |
| estado_fisico | VARCHAR(30) | | Verde, fresco, seco, pergamino, almendra |
| ciclo_cultivo | VARCHAR(20) | | Permanente, transitorio, anual |
| fuente | VARCHAR(50) | | EVA-MADR, Cenicafé, FNC |

**Indexes:** (id_municipio, id_periodo), (id_periodo)

**Datos esperados:** ~1500-3000 registros (600 municipios × 5 años + agregaciones)

### `fact_clima`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_clima | BIGSERIAL | PK | |
| id_municipio | INT | FK NOT NULL | |
| id_periodo | INT | FK NOT NULL | |
| temp_media_c | NUMERIC(4,1) | | °C |
| temp_min_c | NUMERIC(4,1) | | °C |
| temp_max_c | NUMERIC(4,1) | | °C |
| precipitacion_mm | NUMERIC(8,2) | | Acumulada en periodo |
| precipitacion_chirps_mm | NUMERIC(8,2) | | CHIRPS satelital |
| humedad_rel_pct | NUMERIC(4,1) | | % |
| ndvi | NUMERIC(5,3) | | MODIS NDVI [-1,1] |
| fuente | VARCHAR(20) | | IDEAM, CHIRPS, ERA5 |

**Indexes:** UNIQUE (id_municipio, id_periodo, fuente)

**Datos esperados:** ~30000+ registros municipio-mes

### `fact_precio`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_precio | BIGSERIAL | PK | |
| id_periodo | INT | FK NOT NULL UNIQUE | Un precio por periodo |
| precio_fnc_cop_125kg | NUMERIC(12,2) | | Precio interno FNC (carga 125kg) |
| precio_ico_usd_lb | NUMERIC(8,4) | | ICO Composite USD/lb |
| precio_arabica_brasil_usd_lb | NUMERIC(8,4) | | FRED Brasil arábica |
| precio_robusta_usd_lb | NUMERIC(8,4) | | FRED Robusta |
| precio_world_bank_usd_kg | NUMERIC(8,4) | | World Bank Pink Sheet |
| fnc_cosecha_60kg | NUMERIC(12,2) | | Producción FNC (sacos 60kg) |
| fnc_export_60kg | NUMERIC(12,2) | | Exportaciones FNC |
| trm_cop_usd | NUMERIC(8,2) | | Tasa cambio Banrep |

**Indexes:** UNIQUE (id_periodo)

**Datos esperados:** 1990-2026 mensual ≈ 444 registros

### `fact_imagen_enfermedad`

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_imagen | BIGSERIAL | PK | |
| id_enfermedad | INT | FK | NULL si "sano" |
| ruta_archivo | TEXT | NOT NULL | Path relativo `01_datos/imagenes_cafe/...` |
| nombre_archivo | VARCHAR(200) | NOT NULL | |
| parte_planta | VARCHAR(20) | CHECK IN ('hoja','fruto','tallo') | |
| severidad_pct | NUMERIC(5,2) | CHECK 0<=x<=100 | NULL si no aplica |
| nivel_severidad | VARCHAR(15) | CHECK IN ('Sin','Bajo','Medio','Alto') | |
| fuente_dataset | VARCHAR(20) | | RoCoLe, BRACOL, JMuBEN, CoLeaf, CALIBRO |
| resolucion_px | VARCHAR(15) | | "1024x768" |
| variedad_cafe | VARCHAR(50) | | Si está reportada |
| split_modelo | VARCHAR(10) | CHECK IN ('train','val','test') | Asignación CV |

**Indexes:** (id_enfermedad), (fuente_dataset)

**Datos esperados:** ~10000+ imágenes consolidadas

### `fact_prediccion_modelo`

Tabla para guardar predicciones de los modelos en producción.

| Columna | Tipo | Restricciones | Descripción |
|---------|------|---------------|-------------|
| id_prediccion | BIGSERIAL | PK | |
| nombre_modelo | VARCHAR(50) | | rf_rendimiento_v1, lstm_precio_v2, cnn_efficientnet_v3 |
| version | VARCHAR(20) | | Semver |
| id_municipio | INT | FK NULL | Si aplica |
| id_periodo | INT | FK NULL | Si aplica |
| variable_predicha | VARCHAR(30) | | rendimiento, precio, severidad |
| valor_predicho | NUMERIC(14,4) | | |
| valor_real | NUMERIC(14,4) | NULL | Si se conoce post-hoc |
| confianza_lo | NUMERIC(14,4) | | Intervalo confianza inferior |
| confianza_hi | NUMERIC(14,4) | | superior |
| timestamp_pred | TIMESTAMPTZ | DEFAULT NOW() | |
| metadata_json | JSONB | | Inputs y meta arbitrarios |

---

## 4. Tablas auxiliares

### `aux_evento_climatico`

Eventos ENSO catalogados.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id_evento | SERIAL PK | |
| fase | VARCHAR(10) | Nino/Nina |
| intensidad | VARCHAR(15) | Débil/Moderado/Fuerte/Muy Fuerte |
| fecha_inicio | DATE | |
| fecha_fin | DATE | |
| oni_pico | NUMERIC(4,2) | |
| descripcion | TEXT | |

### `aux_diccionario_columnas`

Metadata viva del diccionario (para auto-documentación).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| tabla | VARCHAR(80) | |
| columna | VARCHAR(80) | |
| tipo_dato | VARCHAR(40) | |
| descripcion | TEXT | |
| ejemplos | TEXT | |
| es_pii | BOOLEAN | Si contiene info personal |

---

## 5. Vistas materializadas

### `vw_master_municipal_mensual`

Vista que junta producción + clima + precio + ENSO a nivel municipio-mes.
Equivalente al `master_cafe_mensual.csv` de la 2da entrega, pero ahora directo de la BD.

```sql
CREATE MATERIALIZED VIEW vw_master_municipal_mensual AS
SELECT
    m.codigo_dane AS cod_mun,
    m.nombre AS municipio,
    d.nombre AS departamento,
    m.altitud_msnm,
    m.zona_cafetera,
    p.fecha, p.anio, p.mes, p.semestre,
    p.oni, p.fase_enso,
    pr.area_sembrada_ha, pr.area_cosechada_ha,
    pr.produccion_ton, pr.rendimiento_ton_ha,
    cl.temp_media_c, cl.temp_min_c, cl.temp_max_c,
    cl.precipitacion_mm, cl.precipitacion_chirps_mm,
    cl.ndvi,
    pc.precio_fnc_cop_125kg, pc.precio_ico_usd_lb,
    pc.precio_arabica_brasil_usd_lb,
    pc.fnc_cosecha_60kg, pc.fnc_export_60kg, pc.trm_cop_usd
FROM dim_municipio m
JOIN dim_departamento d USING (id_departamento)
JOIN dim_periodo p ON true
LEFT JOIN fact_produccion pr ON pr.id_municipio = m.id_municipio AND pr.id_periodo = p.id_periodo
LEFT JOIN fact_clima cl ON cl.id_municipio = m.id_municipio AND cl.id_periodo = p.id_periodo
LEFT JOIN fact_precio pc ON pc.id_periodo = p.id_periodo
WHERE m.zona_cafetera IS NOT NULL;

CREATE INDEX ON vw_master_municipal_mensual (anio, mes, codigo_dane);
```

### `vw_imagenes_balanceadas`

Vista que sobre-muestrea imágenes por clase para entrenamiento balanceado.

---

## 6. Reglas de calidad de datos (Constraints + Triggers)

```sql
-- Rendimiento debe ser consistente
ALTER TABLE fact_produccion ADD CONSTRAINT chk_rendimiento
  CHECK (rendimiento_ton_ha IS NULL OR
         (area_cosechada_ha IS NULL OR area_cosechada_ha = 0 OR
          ABS(produccion_ton/NULLIF(area_cosechada_ha,0) - rendimiento_ton_ha) < 0.5));

-- Temperatura plausible Colombia (0 a 40°C)
ALTER TABLE fact_clima ADD CONSTRAINT chk_temp
  CHECK (temp_media_c IS NULL OR (temp_media_c BETWEEN -5 AND 45));

-- Severidad porcentual
ALTER TABLE fact_imagen_enfermedad ADD CONSTRAINT chk_sev_pct
  CHECK (severidad_pct IS NULL OR severidad_pct BETWEEN 0 AND 100);
```

---

## 7. Plan de carga (ETL)

| Orden | Origen | Destino | Script |
|-------|--------|---------|--------|
| 1 | DIVIPOLA DANE | dim_departamento, dim_municipio | `etl_01_divipola.py` |
| 2 | Calendar gen | dim_periodo (1990-2030) | `etl_02_calendario.py` |
| 3 | Cenicafé/FNC | dim_variedad_cafe | `etl_03_variedades.py` |
| 4 | Static | dim_enfermedad | `etl_04_enfermedades.py` |
| 5 | EVA + DANE municipal | fact_produccion | `etl_05_produccion.py` |
| 6 | IDEAM + CHIRPS + ERA5 | fact_clima | `etl_06_clima.py` |
| 7 | FNC + ICO + FRED + WB | fact_precio | `etl_07_precios.py` |
| 8 | RoCoLe + BRACOL + JMuBEN + CALIBRO | fact_imagen_enfermedad | `etl_08_imagenes.py` |
| 9 | NOAA ONI | aux_evento_climatico | `etl_09_eventos_enso.py` |

---

## 8. Tamaño esperado

| Tabla | Filas | Storage |
|-------|-------|---------|
| dim_municipio | ~600 | <100KB |
| dim_periodo | ~444 | <50KB |
| fact_produccion | ~3000 | ~500KB |
| fact_clima | ~30000 | ~5MB |
| fact_precio | ~444 | ~50KB |
| fact_imagen_enfermedad | ~10000 | ~2MB metadata + ~5GB imágenes en disco |
| **Total BD (sin imgs)** | ~45000 filas | ~10MB |
| **Total con imgs filesystem** | — | ~5-10 GB |

---

*Versión 1.0 · Mayo 2026*
