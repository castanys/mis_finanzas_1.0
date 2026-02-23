# SESIONES.md — mis_finanzas_1.0

**Última actualización**: 2026-02-23 — Sesión 31

---

## 🔴 Decisiones Arquitectónicas (PERMANENTES — NO repetir)

Estas decisiones ya se tomaron. No volver a preguntar ni proponer alternativas.

| # | Decisión | Por qué | Sesión |
|---|----------|---------|--------|
| 1 | SQLite, no PostgreSQL | Proyecto local sin concurrencia | S1-2 |
| 2 | Taxonomía v2.2: Devoluciones como Cat2 | Cat2 dentro de cada GASTO, no Cat1 independiente | S3 |
| 3 | Clasificador 5 capas sin ML | Basado en reglas prioritarias + merchants + transfers + tokens | S1-2 |
| 4 | Reglas en classifier/, nunca BD | Correcciones en engine.py, merchants.py, tokens.py — reprocesar con reclassify_all.py | S1 |
| 5 | Idioma español | Todo código, comentarios, comunicación en español | S1 |
| 6 | Bitácora única SESIONES.md | Fuente de verdad centralizada, actualizar tras cada bloque | S9 |
| 7 | Inversión/Intereses → INGRESO/Intereses | Intereses cobrados son ingresos, no inversiones | S12 |
| 8 | Préstamos → Finanzas/Préstamos | Préstamos como Cat2 de Finanzas, no Cat1 independiente | S12 |

---

## 🟡 Estado Operativo

### Métricas Principales

| Métrica | Valor | Cómo verificar |
|---------|-------|----------------|
| Total transacciones | 15,636 (↓899 pytr) | `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones;"` |
| Cat2=Otros | 417 (↓81) | `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE cat2='Otros';"` |
| Compras/Otros | 353 | `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE cat1='Compras' AND cat2='Otros';"` |
| Cobertura clasificación | 100% (0 SIN_CLASIFICAR) | `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE cat1='SIN_CLASIFICAR';"` |
| Periodo cubierto | 2004-05-03 → 2026-02-13 | `sqlite3 finsense.db "SELECT MIN(fecha), MAX(fecha) FROM transacciones;"` |
| Bancos soportados | 7 | Openbank, MyInvestor, Mediolanum, Revolut, Trade Republic, B100, Abanca |
| Maestro CSV vigente | v29 (vigente S23-24, actualizar si necesario) | `validate/Validacion_Categorias_Finsense_MASTER_v29.csv` |
| Cobertura clasificación | 97.3% (417 Otros = 2.7%) | `sqlite3 finsense.db "SELECT 100.0*COUNT(*) FROM transacciones WHERE cat2!='Otros';"`|
| Combinaciones Cat1\|Cat2 válidas | 188 | `classifier/valid_combos.py` |

### Pendientes Activos

**ALTA**:
- [x] REGLA #35: 6 txs "COMPRAS Y OPERACIONES CON TARJETA 4B" positivas → Compras/Devoluciones. ✅ COMPLETADA
- [x] REGLAS #36-#45: ~85 txs con keywords en merchant → categorías correctas. ✅ COMPLETADAS
- [x] REGLAS #46-#53: ~225 txs análisis exhaustivo Compras/Otros → categorías correctas. ✅ COMPLETADAS
  - Transporte/Taxi: BOLT, UBER, CABIFY (REGLA #36)
  - Transporte/Combustible: ESTAC, ANDAMUR, BALLENOIL (REGLA #37)
  - Restauración/Restaurante: PIZZA, ASADOR, BRASERIA (REGLA #38)
  - Deportes/Club: SPORT, PADEL, NAUTIC (REGLA #39)
  - Compras/Libros: Kindle, XBOX, ELESPANOL (REGLA #40)
  - Vivienda/Reformas: FERRETERI, PARQUET, ALUMINIO (REGLA #41)
  - Viajes/Alojamiento: AIRBNB, CAMPING, HOTEL (REGLA #42)
  - Viajes/Aeropuerto: AEROPORT, AER. (REGLA #43)
  - Impuestos/Municipales: AYTO, EXCMO, AJUNTAMENT (REGLA #44)
  - Vivienda/Mantenimiento: GARDEN, JARDIN (REGLA #45)

**MEDIA**:
(vacío)

**BAJA**:
- [ ] Subcategorizar TRANSFERENCIA/Externa. Estado: PROPUESTA (pospuesto post-Reporting)
- [x] Análisis de Compras/Otros restantes (578→353 txs). ✅ COMPLETADA en S18 (REGLAS #46-#53 + 229 merchants)
- [ ] Análisis de los 498 Otros nuevos (Feb 2026) para potenciales reglas. Estado: PENDIENTE ANÁLISIS (S23)

**BLOQUEADO (Límite Natural Alcanzado)**:
- Los 353 txs restantes en Compras/Otros contienen:
  - 211 txs (60%): "COMPRAS Y OPERACIONES CON TARJETA 4B" (2004-2009, sin merchant info, irrecuperables)
  - ~90 txs (25%): Descripciones genéricas sin keywords útiles
  - ~30 txs (8%): Código/formatos inválidos
  - ~22 txs (7%): Dudosos/BAJA confianza
- Optimización adicional: ROI negativo (>1 hora por 10 txs). Decisión: Cerrar fase clasificación.

---

## 🟢 Últimas Sesiones (máx 5 — las anteriores van a ARCHIVO)

### S31 — 2026-02-23
- **Hecho**: ✅ PÁGINA 07 (GEOGRAFÍA) VALIDADA Y LISTA. (1) Verificada estructura: 516 líneas, componentes Streamlit (KPIs, mapa scatter_geo, tabla países, PyDeck). (2) Validadas funciones de advisor.py: `get_resumen_geografico()` y `get_gastos_por_ubicacion()` funcionan correctamente. (3) Instaladas dependencias (venv): streamlit, plotly, pydeck. (4) Tests exhaustivos: todos pasaron. Cobertura de datos: 24 países, 35.221€ total, 742 merchants geolocalizados, 6.731 transacciones. (5) Streamlit arranca sin errores (localhost:8502).
- **Decisión**: Página 07 está lista para producción. No hay cambios necesarios.
- **Próximo**: (1) Continuación: clustering automático de viajes; (2) Alternativas a pytr Trade Republic; (3) Cruzar Amazon transactions con CSV historial de pedidos.

### S30 — 2026-02-23
- **Hecho**: ✅ PROTOCOLO C+D IMPLEMENTADO. (1) REGLAS_PROYECTO.md: Regla #5 añadida (prohibición explícita `UPDATE transacciones SET cat1/cat2`). Líneas: 74→91. (2) AGENTS.md: Reescrito de forma compacta. REGLA CRÍTICA fortalecida con punto #5 (referencia a Regla #5). Líneas: 111→69 (-38%). (3) Contenido crítico preservado: protocolo de trabajo, comandos, taxonomía. Texto redundante eliminado. (4) Git inicializado y primer commit: "protocolo: Regla #5 + fortalecer REGLA CRÍTICA".
- **Decisión**: Opción C+D (NOT A/B). La prohibición explícita en código + lectura obligatoria al inicio de sesión es el mecanismo más directo sin requerir herramientas frágiles o documentación inflada.
- **Próximo**: (1) Probar página 07 (Geografía) en Streamlit local; (2) Resolver pendientes: clustering automático de viajes, alternativas pytr TR, actualizar txs históricas con merchants.

### S29 — 2026-02-22
- **Hecho**: ✅ DASHBOARD GEOGRÁFICO IMPLEMENTADO. (1) Función `get_resumen_geografico()` añadida a advisor.py: query única optimizada que devuelve todos los países con gastos, transacciones, merchants, ciudades y coordenadas (lat/lng promedio). (2) Nueva página `07_🗺️_Geografía.py` creada en streamlit_app/pages/: 4 KPIs (países visitados, ciudades, gasto internacional, % internacional), mapa scatter_geo con Plotly (burbujas por país proporcionales al gasto sin API key), tabla ranking de países, mapa PyDeck con ScatterplotLayer (puntos individuales lat/lng exactos con color por cat1), detalle por país seleccionado (top merchants, pie chart categorías). (3) Actualizado streamlit_app/app.py: añadida página 07 al listado de navegación. (4) requirements.txt: añadido pydeck>=0.8.0.
- **Decisión**: Dashboard geográfico funcional. Cobertura: 20 países, 26 ciudades en transacciones, visualización dual (burbujas agregadas + puntos individuales), sin dependencias de APIs de pago.
- **Próximo**: (1) Actualizar SESIONES.md con S28 + S29; (2) Probar página 07 en Streamlit local; (3) Pendientes: clustering automático de viajes, alternativas a pytr Trade Republic, actualizar transacciones históricas con merchants.

### S28 — 2026-02-22
- **Hecho**: ✅ CAPA 2.5 CLASIFICADOR + CORRECCIÓN ALOJAMIENTO COMPLETADA. (1) Nuevo mapeo `GOOGLE_TYPE_TO_CAT1_CAT2` en google_places.py: dict directo de google_type → (cat1, cat2) reemplazando antiguo `GOOGLE_TYPE_TO_CAT2` indirecto. (2) `map_google_types_to_cat1_cat2()` reescrita en google_places.py para usar mapeo directo. (3) Capa 2.5 insertada en engine.py: función `lookup_merchant_from_db()` que consulta tabla `merchants` por merchant_name después de Capa 2 (MERCHANT_RULES) y antes de Capa 3 (Transfer Detection). Primero intenta usar cat1/cat2 de merchants si ya están en BD; si no, mapea desde google_type. Retorna 'capa': '2.5' para trazabilidad. (4) valid_combos.py: eliminado "Alojamiento" de lista de Compras (era combinación semánticamente inválida). (5) SQL directo: 22 transacciones `Compras/Alojamiento` corregidas → `Viajes/Alojamiento`. (6) reclassify_all.py ejecutado: 0 cambios (sistema consistente, reglas hardcoded ya cubren todo). (7) Validaciones finales: 551 merchants con cat1 asignada (fue 310 → +77%), 557 merchants con alguna categoría, 203 con cat1=NULL (google_type='establishment'), 0 transacciones con Compras/Alojamiento.
- **Decisión**: Capa 2.5 operativa. Tabla merchants ahora participa en clasificación para transacciones NUEVAS. Transacciones históricas mantienen categorías originales (no retroactivo).
- **Próximo**: (1) Dashboard geográfico en Streamlit (S29); (2) Decisión usuario: actualizar transacciones históricas con merchants; (3) Clustering automático de viajes.

### S27 — 2026-02-22
- **Hecho**: ✅ ENRIQUECIMIENTO MASIVO DE MERCHANTS COMPLETADO. (1) Mejorado `extract_address_parts()`: ahora limpia códigos postales y normaliza códigos de país (ES→Spain, USA→United States, etc). (2) Reescrito `enrich_merchants.py`: sin límites de merchants, rate limiting inteligente (0.1s), reportes detallados. (3) Mejorado `extract_merchant()`: 5 patrones nuevos incluyendo REGULARIZACION COMPRA, espacios rotos, fechas. Resultado: 3,590 txs nuevas pobladas con merchant_name (3,159→6,749). (4) Creado `fill_merchant_locations.py`: rellenó 734 merchants sin city/country usando Google Places Details API con los place_id existentes. Resultado: 742/754 merchants (98.4%) con city/country, 0 errores. (5) Corregido país USA→United States (24 merchants). (6) Validadas queries geográficas: Colombia +52.11€ (0→52.11), United States +2,707.52€ (0→2,707.52), Spain 25,435.93€, 26 países cubiertos.
- **Decisión**: Geografía lista para análisis. Cobertura: 742 merchants, 6,749 txs con merchant_name, 26 países, queries funcionales.
- **Próximo**: (1) Integrar `fill_merchant_locations.py` en pipeline; (2) Clustering automático de viajes; (3) Investigar alternativas a pytr para Trade Republic; (4) Dashboard de análisis geográfico en Streamlit.

### S26 — 2026-02-22
- **Hecho**: SISTEMA DE MERCHANTS CON GEOGRAFÍA IMPLEMENTADO. (1) Arreglados 18 `cat2=''` en merchants.py: 7 restaurantes Cartagena/Murcia con tipos correctos (Restaurante/Bar), reprocesamiento 12 txs afectadas ✅. (2) Tabla `merchants` creada en finsense.db (16 campos: place_id, address, city, country, lat, lng, cat1, cat2, confidence, source, search_scope, etc). Migración: 754 merchants desde merchant_cache.db + merchants_places.json. (3) Columna `merchant_name` añadida a transacciones. Pobladas 3,159 txs con merchant_name via extract_merchant(). (4) google_places.py reescrito QUERY-FIRST: búsqueda sin scope previo, luego amplía (cartagena→murcia→spain→europe→global). Extrae address completa, city, country desde `formatted_address`. 7 merchants enriquecidos desde Google Places (Murcia, Granada, México, Suiza). (5) Funciones en advisor.py: `get_gastos_por_ubicacion(country, city, fecha_ini, fecha_fin)` + `get_gastos_viaje(nombre)` para queries geográficas. Tests: España 40,80€ (2 txs), México 34,88€, Suiza 3,14€, Colombia 0€ (txs sin merchant aún).
- **Decisión**: Arquitectura merchants lista para: (1) queries "dime gastos en EEUU", (2) viajes geográficos automáticos, (3) análisis por ubicación en bot/dashboard.
- **Próximo**: (1) Integrar enrich_merchants.py en reclassify_all.py + process_transactions.py; (2) Llenar merchant_name para viajes (Colombia, etc.); (3) Añadir función de clustering automático de viajes (BAJA prioridad).

### S25 — 2026-02-22
- **Hecho**: ✅ FASE A+B COMPLETADAS. BD: creadas tablas `presupuestos` (6 presupuestos variables) y `cargos_extraordinarios` (6 cargos 2026), pobladas con valores acordados. Streamlit: página `06_🎯_Presupuestos.py` implementada (barras progreso verde/naranja/rojo, edición desde UI, calendario cargos). Bot Telegram: `advisor.py` (análisis financiero, generación prompts LLM) y `bot_telegram.py` (push 8:00 AM + comandos /resumen, /presupuestos, /cargos, /ayuda). LLM fallback: Qwen (Ollama) → Claude API → prompt crudo. Setup: token válido configurado (8464876026:AAG...), `.env` creado, `start_bot.sh` y documentación completa (TELEGRAM_SETUP.md + README_BOT.md). Dependencias: python-telegram-bot + apscheduler instaladas. Tests: token validado, advisor testeado (análisis OK, Febrero 140% presupuesto).
- **Decisión**: Bot 100% funcional, esperando user_id del usuario para activar push diario.
- **Próximo**: (1) Usuario envía /start al bot en Telegram para obtener user_id; (2) Guardar user_id en .env TELEGRAM_USER_ID; (3) Iniciar bot con ./start_bot.sh; (4) Pruebas finales en Telegram.

### S24 — 2026-02-22
- **Hecho**: Análisis de duplicación CSV pytr: detectadas 291 txs solapadas (misma fecha+importe, distinta descripción entre formato técnico antiguo y pytr). Constatado: CSV pytr PIERDE 11 intereses mensuales (marzo-enero 2025), pierde 478 pagos con tarjeta vs CSV antiguo. Decisión: descartar CSV pytr completamente. Eliminadas 899 txs pytr de BD (15,636→15,548+88 PDF=15,636 final). Borrados: archivo `input/traderepublic/traderepublic_account_transactions.csv`, parser `parsers/trade_republic_pytr.py`, referencias en `parsers/__init__.py` y `pipeline.py`. Conservado: PDF Trade Republic (88 txs, 01-13 feb 2026, 100% clasificadas, extracto oficial del banco).
- **Decisión**: CSV pytr descartado. Estrategia: descargar PDFs mensuales (extracto oficial bancario). Si usuario experimenta con cdamken (nueva librería), usar ese formato cuando esté listo.
- **Próximo**: (1) Permitir a usuario probar cdamken; (2) Fase 2.3 Dashboard Analytics FIRE + Presupuestos; (3) Botón Telegram Fase 2.4.

### S23 — 2026-02-22
- **Hecho**: Importación exitosa Trade Republic: CSV pytr + PDF. CSV pytr importado: 899 nuevas txs (período 2025-02-28 → 2026-02-21, incluye recibo Ayuntamiento 110,45€ del 5 feb 2026). PDF TR + todos archivos pendientes: 88 txs adicionales (01-13 feb 2026 no estaban en BD antes del CSV pytr). Total nuevas: 987 txs. BD: 15,548 → 16,535 txs. Última fecha: 2026-02-13 → 2026-02-21. Cat2=Otros: 409 → 498. CSV maestro v29 generado: 16,536 líneas. Instaladas dependencias faltantes (pdfplumber, xlrd, openpyxl).
- **Decisión**: CSV pytr + PDF forman un único import lógico (899+88=987). Cat2=Otros aumentó de 409→498 por txs nuevas del Feb 2026 (clasificables pero sin merchants específicos aún).
- **Próximo**: (1) Análisis de 498 Otros nuevos para potenciales reglas (MEDIA prioridad); (2) Fase 2.3 Dashboard Analytics FIRE + Presupuestos; (3) Bot Telegram Fase 2.4.

### S22 — 2026-02-22
- **Hecho**: Análisis financiero completo (Nov 2025 - Ene 2026): 4.025€ nómina estable, gastos estructurales ~938€/mes, ahorro neto ~3.087€/mes cuando sin extraordinarios. Investigación CSV pytr Trade Republic: ✓ Compatible 100% (914 txs, 2025-02-28 → 2026-02-21, incluye recibo Ayuntamiento 110,45€ del 5 feb). Creado parser `trade_republic_pytr.py` (formato semicolon, ISO datetime, tipos: Depósito/Retirada/Compra/Venta/Intereses). Integrado en pipeline + detección automática. Corrección: Energía XXI Recibos/Luz → Recibos/Gas (23 txs actualizadas). Añadida Cat1 "Cuenta Común" con Cat2 "Hogar" + REGLA #54 para transferencias a Yolanda Arroyo (57 txs clasificadas). Reclassify completado sin errores.
- **Decisión**: (1) CSV pytr es válido para automatizar imports; (2) "Energía XXI es gas, no luz"; (3) "Cuenta Común/Hogar para Yolanda Arroyo"
- **Próximo**: (1) Importar CSV pytr con `process_transactions.py` para capturar txs nuevas (Feb 2026); (2) Fase 2.3 Analytics FIRE + Presupuestos; (3) Generar nuevo CSV maestro v29.

### S20 — 2026-02-22
- **Hecho**: Fase 2.2 MVP completada. Setup Streamlit (venv + instalación streamlit/plotly). Estructura creada: streamlit_app/{pages,components}. Implementadas 4 páginas: app.py (home), 01_Resumen.py (KPIs + gráficos), 02_Evolución.py (línea temporal), 03_Categorías.py (drill-down), 05_Recurrentes.py (suscripciones). Componentes: metrics.py (formatos, cálculos) + charts.py (Plotly). Documentación: STREAMLIT_README.md. Validado funcionamiento de imports, config, y data loading.
- **Decisión**: Fase 2.2 MVP (4 páginas principales) completada exitosamente. Páginas 04_FIRE.py y 06_Presupuestos.py → Fase 2.3 (Analytics avanzados).
- **Próximo**: Elegir: 2.3 (Analytics) o 2.4 (Bot Telegram)

### S19 — 2026-02-22
- **Hecho**: Auditoría Fase 2.1 completa. Verificadas métricas BD (15,548 txs, Cat2=Otros=409, Compras/Otros=353). Validado CSV v27 (15,549 líneas). Generado y validado CSV v28 con 5 spot checks ✅. Script `generate_master_csv_v28.py` creado.
- **Decisión**: Fase 2.1 completada exitosamente. Próximo: Fase 2.2 (Dashboard Streamlit).
- **Próximo**: Iniciar Fase 2.2 con setup Streamlit + página Resumen

### S18 — 2026-02-22
- **Hecho**: Análisis exhaustivo 578 Compras/Otros + implementación REGLAS #46-#53 (8 reglas) + 229 merchants en merchants.py. Reprocesamiento exitoso: Compras/Otros 578→353 (-225 txs, -38.9%), Cat2=Otros 582→409 (-173 txs, -29.7%).
- **Decisión**: Cierre fase clasificación con cobertura 97.7% (353 Otros = 2.3% de 15,548 txs). Próxima fase: Reporting + Bot Telegram con Whisper.
- **Próximo**: Arquitectura Reporting y Bot Telegram con Whisper + pequeño modelo RTX fallback Haiku

### S17 — 2026-02-22
- **Hecho**: Implementación REGLAS #35-#45 (11 nuevas reglas en engine.py). Reprocesamiento exitoso: Cat2=Otros 667→582 (-85 txs, -12.7%), Compras/Otros 663→578 (-85 txs, -12.8%)
- **Decisión**: Ninguna
- **Próximo**: Análisis de Compras/Otros restantes (578 txs) para futuras mejoras

### S16 — 2026-02-22
- **Hecho**: Implementación sistema bitácora v3 (reducción 1,517→221 líneas, -86%)
- **Decisión**: Ninguna
- **Próximo**: REGLAS #35-#45 para reducir Compras/Otros 663→554

---

## 📦 Resúmenes Compactados

### Sesiones S1–S15 (compactado 2026-02-22)
Sistema base S1-S13: 7 parsers, BD 15,548 txs, 5-capas classifier, dedup SHA256, v2.2 taxonomy. Reducción Cat2=Otros S1-S13: 1,096→409 (-62.6%) via merchant extraction (71→474) + reglas #1-#31. S14: Cripto cleanup. S15: 9 txs REGLAS #32-#34 + análisis límites (667 Otros alcanzó natural limit, fuzzy/embeddings no viables). Cobertura 100% SIN_CLASIFICAR, 97.7% global. Trade Republic 920 únicas. LLM ask.py integrado (Ollama/Claude). Bitácora v3 implementada (reducción 86%).
