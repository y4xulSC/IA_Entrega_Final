# Preguntas frecuentes sobre el Sistema IA Café

## Sobre el sistema

**¿Qué hace el Sistema IA Café?**
Integra 11 fuentes públicas de datos del agro colombiano (producción EVA,
precios FNC e ICO, clima IDEAM y Open-Meteo, ENSO de NOAA, suelos
SoilGrids, altitudes SRTM, imágenes de enfermedades) en una base PostgreSQL
y entrena modelos de IA para predicción de rendimiento, pronóstico de
precios, detección de enfermedades por imagen, detección de anomalías
y consulta en lenguaje natural.

**¿Quién está detrás del proyecto?**
Yáxul Santiago Cárdenas y Yesenia Díaz Urrego, estudiantes de Ingeniería
de Datos e IA de la Universidad Autónoma de Occidente, semestre 2026-1.
Es un proyecto académico abierto.

**¿Es un producto certificado para producción?**
No. Es un prototipo académico funcional. La validación operacional con
extensionistas FNC, MADR o asociaciones cafeteras es trabajo futuro.

**¿Es de código abierto?**
Sí, todo el código, modelos y datos son abiertos y reproducibles.

## Sobre los modelos

**¿Qué tan bueno es el modelo de rendimiento?**
R² = 0.818 con CatBoost a escala municipal (NB09). Mejora de +0.75
puntos respecto a la versión departamental de la 2da entrega (R²=0.067).

**¿Qué tan bueno es el modelo de precio?**
- Para precio interno actual (FNC): R² = 0.945, MAPE = 4.3% con Ridge.
- Para pronóstico de precio futuro: R² = 0.472 con BiGRU (NB10).

**¿La CNN detecta todas las enfermedades del café?**
Detecta 6 clases: Roya, Gotera, Cercospora, Phoma, Miner, Sano,
SpiderMite. No detecta Antracnosis aún (trabajo futuro). Requiere
imagen clara de hoja, fondo neutro, buena iluminación.

**¿Por qué los datasets de imágenes son foráneos?**
Porque los datasets públicos disponibles vienen de Brasil (BRACOL),
Ecuador (RoCoLe), Kenia (JMuBEN). Las enfermedades son las mismas en
la región andina, pero las condiciones de captura (cámara, fondo,
variedad de café) pueden diferir. La validación con cafetales
colombianos es trabajo futuro.

## Sobre los datos

**¿Cuántos municipios cubre el sistema?**
600+ municipios en el catálogo, con 21 municipios cafeteros principales
con clima satelital propio (Open-Meteo histórico 1990-2026).

**¿Qué rango temporal cubre?**
- Precios: 1990-2026
- Clima Open-Meteo: 1990-2026
- ENSO ONI: 1950-2026
- Producción EVA: 2007-2024
- Imágenes: snapshot 2018-2024

**¿Por qué la BD usa USD/kg en vez de USD/lb?**
Decisión de diseño para unificar unidades canónicas. Las APIs (FRED)
publican en centavos USD/lb y se convierten en el ETL multiplicando
por (1/45.36). Esto da precios típicos en rango [0.5, 30] USD/kg.

## Sobre eventos climáticos

**¿Qué tanto afecta El Niño al café colombiano?**
Reduce el rendimiento aproximadamente 24% respecto a fase Neutro.
Validado con test estadístico Kruskal-Wallis (p < 0.05) sobre datos
históricos 1990-2024.

**¿Y La Niña?**
Reduce el rendimiento aproximadamente 12% por exceso de humedad y
mayor incidencia de enfermedades fúngicas (gotera, antracnosis, phoma).

**¿Cómo sé si viene El Niño?**
NOAA publica pronósticos mensuales del índice ONI 3-6 meses adelante
en https://origin.cpc.ncep.noaa.gov. El sistema integra estos datos
y muestra alertas en el Asesor del Caficultor.

## Sobre la calidad del café

**¿Qué es el puntaje SCA?**
Calificación de 0-100 puntos por catador certificado Q-Grader,
siguiendo protocolo de la Specialty Coffee Association. Mide 10
atributos sensoriales del café tostado y preparado.

**¿Cuánto vale un café con 85 puntos SCA?**
En promedio 50-100% más que el precio base FNC, dependiendo del
comprador y demanda. La calculadora SCA del sistema da estimaciones
en COP/kg.

**¿Cómo subo el puntaje SCA de mi café?**
- Cosecha selectiva (solo cereza roja madura)
- Fermentación controlada 18-24 horas
- Secado lento 6-12 días
- Almacenamiento en pergamino en lugar seco
- Trillar solo antes de vender

## Sobre fertilización

**¿Cuántas veces al año debo fertilizar mi cafetal?**
4 veces al año: febrero-marzo, mayo-junio, agosto-septiembre, noviembre.
Dosis típica 800-1200 kg NPK 17-6-18-2 por hectárea/año distribuidos.

**¿Qué pasa si no fertilizo mi cafetal?**
- Hojas amarillas (especialmente cercospora)
- Defoliación temprana
- Frutos pequeños y de baja calidad
- Mayor susceptibilidad a roya y otras enfermedades
- Reducción de producción 30-50% al año

**¿Cuánto cuesta fertilizar?**
Aproximadamente 1.2-1.8 millones COP por hectárea/año en NPK. El
retorno es 2-3x en producción cuando se compara contra no fertilizar.

## Sobre el sistema técnico

**¿Cómo instalo el sistema?**
1. Clonar el repositorio
2. Copiar .env.example a .env y configurar credenciales
3. Crear BD PostgreSQL: `psql -U postgres -c "CREATE DATABASE cafe_ia;"`
4. Cargar schema: `psql -U postgres -d cafe_ia -f 03_scripts/bd/01_ddl_schema.sql`
5. Descargar datos: `python 03_scripts/descarga/00_ejecutar_todo.py`
6. ETL: `python 03_scripts/etl/etl_pipeline.py`
7. Cargar BD: `python 03_scripts/bd/02_carga_inicial.py`
8. Lanzar app: `cd 07_app_web && streamlit run app.py`

**¿Necesito GPU para entrenar?**
- Para NB07, NB09, NB10, NB11, NB12: NO. CPU suficiente.
- Para NB08 (CNN con ~10K imágenes): GPU muy recomendada.
  Sin GPU son 6-8 horas; con RTX 3060+ son 30-90 minutos.
  Alternativa: Google Colab gratis con GPU T4.

**¿Puedo desplegar la app en internet gratis?**
Sí. Opciones:
- Streamlit Cloud (1 GB RAM, gratis)
- HuggingFace Spaces (16 GB RAM, gratis, mejor para ML)
- Render.com (512 MB, gratis con sleep)

**¿Cómo configuro el chatbot RAG?**
1. Crear cuenta en https://console.groq.com (gratis)
2. Generar API key
3. Agregar al .env: `GROQ_API_KEY=gsk_xxx`
4. Indexar: `python 06_agente_rag/rag_pipeline.py indexar --force`
5. Probar: `python 06_agente_rag/rag_pipeline.py demo`

## Limitaciones honestas

- Modelos de pronóstico no extrapolan eventos atípicos (surge 2024-2025).
- CNN entrenado con datasets foráneos, requiere validación colombiana.
- Solo 21 municipios con clima satelital de detalle.
- No incluye variables socioeconómicas profundas (costo mano obra,
  acceso a crédito, etc.).
- Datos EVA tienen rezago de 1-2 años respecto a la realidad actual.
- El sistema es prototipo, no certificado para uso operativo regulado.
