# Selección del MockUp final de CofiTech mediante AHP (Analytic Hierarchy Process)

*Metodología de ideación multicriterio (Saaty), según el curso de Data Thinking. Juicios del equipo CofiTech. **Versión 2 (19-oct-2026):** cálculo exacto con el vector propio principal en `03_scripts/ahp/ahp_cofitech.py` y matriz de criterios alineada con los pesos de la diapositiva de síntesis (ver §8). El tablero visual que conecta este análisis con las láminas del MockUp está en `CofiTech_AHP_Seleccion_Mockup.png` / `.md`.*

## 1. Estructura jerárquica

```
NIVEL 1 · OBJETIVO
  Seleccionar la arquitectura de MockUp óptima para maximizar la adopción campesina
  y la viabilidad comercial B2B de CofiTech

NIVEL 2 · CRITERIOS
  C1 Usabilidad y Adopción Rural ........ baja barrera de entrada para el caficultor (KR1, KR3)
  C2 Valor B2B / Monetización ........... analítica accionable para Cooperativas y Comités
  C3 Integración Sistémica .............. cero silos: Visión ↔ Clima ↔ Precios ↔ RAG
  C4 Factibilidad Técnica y Conectividad  recursos eficientes, baja dependencia de la red

NIVEL 3 · ALTERNATIVAS
  Op1 Dashboard Analítico Monolítico Web (9 pestañas técnicas densas)
  Op2 App Móvil Asistencial Pura (solo diagnóstico por foto y chat básico)
  Op3 Plataforma Dual Adaptativa por Roles con Estado Compartido
```

## 2. Escala fundamental de Saaty y procedimiento

| Valor | Significado | Recíproco |
|---:|---|---:|
| 1 | Igual importancia | 1 |
| 3 | Importancia moderada de uno sobre otro | 1/3 |
| 5 | Importancia fuerte | 1/5 |
| 7 | Importancia muy fuerte o demostrada | 1/7 |
| 9 | Importancia extrema | 1/9 |
| 2, 4, 6, 8 | Valores intermedios entre dos juicios | 1/2, 1/4, 1/6, 1/8 |

La matriz es recíproca: si *a<sub>ij</sub>* = 3, entonces *a<sub>ji</sub>* = 1/3, y la diagonal vale 1.

**Procedimiento (igual para las 5 matrices):**

1. **Vector propio principal.** Se resuelve *A·w = λmax·w* y se toma el autovalor real dominante λmax (teorema de Perron-Frobenius) y su vector propio *w*, normalizado para que sume 1. Ese *w* es el vector de prioridades.
2. **Comprobación.** Como *w* es vector propio, (A·w)<sub>i</sub>/w<sub>i</sub> = λmax en todas las filas. En una matriz perfectamente consistente λmax = n.
3. **Índice de consistencia:** CI = (λmax − n)/(n − 1).
4. **Razón de consistencia:** CR = CI/RI, con el índice aleatorio de Saaty RI = 0,58 para n = 3 y RI = 0,90 para n = 4. La matriz se acepta si **CR < 0,10**.
5. **Síntesis distributiva:** puntaje<sub>i</sub> = Σ<sub>j</sub> w<sub>j</sub> · p<sub>ij</sub>. Los puntajes globales suman 1.

En castellano también se escriben IC (índice de consistencia), IA (índice aleatorio) y RC (razón de consistencia). Las tablas incluyen, como referencia, el vector aproximado del método de columnas normalizadas que se enseña en clase. Con matrices tan consistentes como estas, la diferencia aparece apenas en la tercera cifra decimal.

## 3. Ponderación de los criterios (matriz 4×4)

**Juicios del equipo (v2):**

- **C1 vs C2 = 1** · El modelo es B2B2C: la cooperativa paga la consola y ofrece la app sin costo a sus asociados. Sin adopción no hay datos de campo que vender, y sin un cliente que pague no hay piloto sostenible. En la comparación directa, ambos criterios valen lo mismo. C1 termina con más peso porque domina con más fuerza a C3 y a C4. *(v1: 2)*
- **C1 vs C3 = 2** · Una plataforma muy integrada que el caficultor no adopta no genera datos ni valor.
- **C1 vs C4 = 4** · La factibilidad ya está acotada por las restricciones del proyecto (presupuesto cero, Streamlit Community Cloud y Supabase, sin Docker). Es una condición que las tres opciones deben cumplir, no lo que las diferencia. *(v1: 3)*
- **C2 vs C3 = 1** · El valor B2B nace justamente de integrar los datos de campo con la analítica: los dos criterios se sostienen mutuamente.
- **C2 vs C4 = 2** · El modelo de negocio depende del cliente B2B; la infraestructura es un medio.
- **C3 vs C4 = 2** · La retroalimentación del profesor («las herramientas se ven desconectadas») convierte la integración en un requisito de la entrega.

**a) Matriz de comparación por pares** (fila frente a columna)

| | C1 Usabilidad | C2 Valor B2B | C3 Integración | C4 Factibilidad |
|---|---:|---:|---:|---:|
| **C1 Usabilidad** | 1 | 1 | 2 | 4 |
| **C2 Valor B2B** | 1 | 1 | 1 | 2 |
| **C3 Integración** | 1/2 (0,500) | 1 | 1 | 2 |
| **C4 Factibilidad** | 1/4 (0,250) | 1/2 (0,500) | 1/2 (0,500) | 1 |

**b) Vector propio principal** (`numpy.linalg.eig`, autovalor real dominante, normalizado a suma 1)

| | **w (vector propio principal)** | (A·w)ᵢ / wᵢ | w aproximado (columnas normalizadas) |
|---|---:|---:|---:|
| **C1 Usabilidad** | **0,3858** | 4,0607 | 0,3846 |
| **C2 Valor B2B** | **0,2742** | 4,0606 | 0,2734 |
| **C3 Integración** | **0,2267** | 4,0606 | 0,2280 |
| **C4 Factibilidad** | **0,1133** | 4,0606 | 0,1140 |
| **Suma** | **1,0000** | | 1,0000 |

**c) Consistencia** · λmax = 4,0606 · CI = (λmax − n)/(n − 1) = (4,0606 − 4)/3 = 0,0202 · RI (n = 4) = 0,90 · **CR = CI/RI = 0,0225** → consistente (CR < 0,10)

**Resultado:** C1 = **0,3858** · C2 = **0,2742** · C3 = **0,2267** · C4 = **0,1133** (suma = 1,0000). Coinciden con los de la diapositiva de síntesis (0,38 · 0,28 · 0,22 · 0,12) con una diferencia máxima de 0,007 por criterio. Con la escala entera de Saaty no hay una matriz ordinalmente coherente que se acerque más.

## 4. Prioridad local de las alternativas por criterio (matrices 3×3)

### 4.1 Respecto a C1 · Usabilidad y Adopción Rural (peso 0,3858)

**Juicios:**

- **Op1 vs Op2 = 1/4** · Nueve pestañas técnicas con jerga estadística son una barrera alta en el celular del caficultor; la app asistencial es de uso inmediato.
- **Op1 vs Op3 = 1/5** · La vista de caficultor de la Op3 es móvil, guiada paso a paso («siguiente paso») y pide los datos de la finca una sola vez.
- **Op2 vs Op3 = 1/2** · La Op2 es aún más simple, pero no incluye Predicción, y sin Predicción KR3 (usar Visión + Predicción + RAG) es imposible. Por eso la Op3 gana solo moderadamente.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 1/4 (0,250) | 1/5 (0,200) |
| **Op2 Asistencial** | 4 | 1 | 1/2 (0,500) |
| **Op3 Dual** | 5 | 2 | 1 |

**b) Vector propio principal** (`numpy.linalg.eig`, autovalor real dominante, normalizado a suma 1)

| | **w (vector propio principal)** | (A·w)ᵢ / wᵢ | w aproximado (columnas normalizadas) |
|---|---:|---:|---:|
| **Op1 Monolítico** | **0,0974** | 3,0246 | 0,0982 |
| **Op2 Asistencial** | **0,3331** | 3,0246 | 0,3339 |
| **Op3 Dual** | **0,5695** | 3,0246 | 0,5679 |
| **Suma** | **1,0000** | | 1,0000 |

**c) Consistencia** · λmax = 3,0246 · CI = (λmax − n)/(n − 1) = (3,0246 − 3)/2 = 0,0123 · RI (n = 3) = 0,58 · **CR = CI/RI = 0,0212** → consistente (CR < 0,10)

### 4.2 Respecto a C2 · Generación de Valor B2B / Monetización (peso 0,2742)

**Juicios:**

- **Op1 vs Op2 = 5** · La Op1 ofrece analítica territorial (rendimiento, precios, mapa); la Op2 no tiene nada que vender a una cooperativa.
- **Op1 vs Op3 = 1/3** · La consola de la Op3 tiene la misma analítica y además las alertas fitosanitarias alimentadas por los diagnósticos de campo de los caficultores, un dato propio que no existe en fuentes abiertas.
- **Op2 vs Op3 = 1/7** · Sin vista para cooperativas no hay cliente que pague la consola del modelo B2B2C.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 5 | 1/3 (0,333) |
| **Op2 Asistencial** | 1/5 (0,200) | 1 | 1/7 (0,143) |
| **Op3 Dual** | 3 | 7 | 1 |

**b) Vector propio principal** (`numpy.linalg.eig`, autovalor real dominante, normalizado a suma 1)

| | **w (vector propio principal)** | (A·w)ᵢ / wᵢ | w aproximado (columnas normalizadas) |
|---|---:|---:|---:|
| **Op1 Monolítico** | **0,2790** | 3,0648 | 0,2828 |
| **Op2 Asistencial** | **0,0719** | 3,0653 | 0,0738 |
| **Op3 Dual** | **0,6491** | 3,0649 | 0,6434 |
| **Suma** | **1,0000** | | 1,0000 |

**c) Consistencia** · λmax = 3,0649 · CI = (λmax − n)/(n − 1) = (3,0649 − 3)/2 = 0,0324 · RI (n = 3) = 0,58 · **CR = CI/RI = 0,0559** → consistente (CR < 0,10)

### 4.3 Respecto a C3 · Integración Sistémica (Visión + Clima + Precios + RAG) (peso 0,2267)

**Juicios:**

- **Op1 vs Op2 = 1/2** · La Op2 conecta foto y chat (dos herramientas); la Op1 tiene todas, pero en silos: cada pestaña pide sus propios datos.
- **Op1 vs Op3 = 1/7** · La Op3 comparte estado: el diagnóstico de la foto ajusta el riesgo en Rendimiento y se inyecta como contexto al RAG.
- **Op2 vs Op3 = 1/4** · La Op2 deja por fuera la predicción y el panorama regional: la integración es parcial.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 1/2 (0,500) | 1/7 (0,143) |
| **Op2 Asistencial** | 2 | 1 | 1/4 (0,250) |
| **Op3 Dual** | 7 | 4 | 1 |

**b) Vector propio principal** (`numpy.linalg.eig`, autovalor real dominante, normalizado a suma 1)

| | **w (vector propio principal)** | (A·w)ᵢ / wᵢ | w aproximado (columnas normalizadas) |
|---|---:|---:|---:|
| **Op1 Monolítico** | **0,0977** | 3,0023 | 0,0978 |
| **Op2 Asistencial** | **0,1870** | 3,0020 | 0,1871 |
| **Op3 Dual** | **0,7153** | 3,0020 | 0,7151 |
| **Suma** | **1,0000** | | 1,0000 |

**c) Consistencia** · λmax = 3,0020 · CI = (λmax − n)/(n − 1) = (3,0020 − 3)/2 = 0,0010 · RI (n = 3) = 0,58 · **CR = CI/RI = 0,0017** → consistente (CR < 0,10)

### 4.4 Respecto a C4 · Factibilidad Técnica y Conectividad (peso 0,1133)

**Juicios:**

- **Op1 vs Op2 = 1/4** · La Op1 carga todos los modelos y tablas en cada sesión; la Op2 solo necesita una CNN y un chat, y podría funcionar casi sin red.
- **Op1 vs Op3 = 1/2** · La Op3 carga solo las pantallas del rol y guarda localmente si la nube no responde, pero sigue siendo una aplicación web completa.
- **Op2 vs Op3 = 2** · La Op2 es la más liviana y la más resistente a la falta de conectividad: en este criterio gana.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 1/4 (0,250) | 1/2 (0,500) |
| **Op2 Asistencial** | 4 | 1 | 2 |
| **Op3 Dual** | 2 | 1/2 (0,500) | 1 |

**b) Vector propio principal** (`numpy.linalg.eig`, autovalor real dominante, normalizado a suma 1)

| | **w (vector propio principal)** | (A·w)ᵢ / wᵢ | w aproximado (columnas normalizadas) |
|---|---:|---:|---:|
| **Op1 Monolítico** | **0,1429** | 3,0000 | 0,1429 |
| **Op2 Asistencial** | **0,5714** | 3,0000 | 0,5714 |
| **Op3 Dual** | **0,2857** | 3,0000 | 0,2857 |
| **Suma** | **1,0000** | | 1,0000 |

**c) Consistencia** · λmax = 3,0000 · CI = (λmax − n)/(n − 1) = (3,0000 − 3)/2 = 0,0000 · RI (n = 3) = 0,58 · **CR = CI/RI = 0,0000** → consistente (CR < 0,10)

## 5. Síntesis final (Alternativa = Σ w<sub>criterio j</sub> × Prioridad<sub>opción en criterio j</sub>)

**a) Prioridades locales y pesos de los criterios**

| Alternativa | C1 Usabilidad<br>(w = 0,3858) | C2 Valor B2B<br>(w = 0,2742) | C3 Integración<br>(w = 0,2267) | C4 Factibilidad<br>(w = 0,1133) |
|---|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,0974 | 0,2790 | 0,0977 | 0,1429 |
| **Op2 Asistencial** | 0,3331 | 0,0719 | 0,1870 | 0,5714 |
| **Op3 Dual** | 0,5695 | 0,6491 | 0,7153 | 0,2857 |

**b) Aporte ponderado (w × prioridad local) y puntaje global**

| Alternativa | C1 Usabilidad | C2 Valor B2B | C3 Integración | C4 Factibilidad | **Puntaje global** | **Ranking** |
|---|---:|---:|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,3858 × 0,0974 = 0,0376 | 0,2742 × 0,2790 = 0,0765 | 0,2267 × 0,0977 = 0,0222 | 0,1133 × 0,1429 = 0,0162 | **0,1524** | **3.º** |
| **Op2 Asistencial** | 0,3858 × 0,3331 = 0,1285 | 0,2742 × 0,0719 = 0,0197 | 0,2267 × 0,1870 = 0,0424 | 0,1133 × 0,5714 = 0,0648 | **0,2554** | **2.º** |
| **Op3 Dual** | 0,3858 × 0,5695 = 0,2197 | 0,2742 × 0,6491 = 0,1780 | 0,2267 × 0,7153 = 0,1621 | 0,1133 × 0,2857 = 0,0324 | **0,5922** | **1.º** |
| **Suma** | | | | | **1,0000** | |

**Ejemplo de cálculo (Opción 3):** (0,3858 × 0,5695) + (0,2742 × 0,6491) + (0,2267 × 0,7153) + (0,1133 × 0,2857) = 0,2197 + 0,1780 + 0,1621 + 0,0324 = **0,5922**

*Los productos se muestran redondeados a cuatro decimales; su suma puede diferir en la última cifra del puntaje calculado sin redondear.*

**c) Tabla comparativa final**

| Ranking | Alternativa | Puntaje global | % del total | Criterio donde gana |
|---:|---|---:|---:|---|
| 1.º | **Opción 3 · Plataforma Dual Adaptativa por Roles** | **0,5922** | 59,2 % | C1 Usabilidad, C2 Valor B2B, C3 Integración |
| 2.º | Opción 2 · App Móvil Asistencial Pura | 0,2554 | 25,5 % | C4 Factibilidad |
| 3.º | Opción 1 · Dashboard Analítico Monolítico Web | 0,1524 | 15,2 % | — |

## 6. Análisis de sensibilidad

Para comprobar que el resultado no depende de un peso puntual, se varió el peso de cada criterio de 0 a 1, repartiendo el resto entre los demás en la misma proporción:

| Escenario | Op1 | Op2 | Op3 | Ganadora |
|---|---:|---:|---:|---|
| Pesos del equipo (v2) | 0,1524 | 0,2554 | 0,5922 | Op3 Dual |
| Todos los criterios iguales (0,25) | 0,1542 | 0,2908 | 0,5549 | Op3 Dual |
| C1 Usabilidad con peso 0,50 | 0,1422 | 0,2698 | 0,5880 | Op3 Dual |
| C2 Valor B2B con peso 0,50 | 0,1918 | 0,1983 | 0,6099 | Op3 Dual |
| C3 Integración con peso 0,50 | 0,1331 | 0,2312 | 0,6357 | Op3 Dual |
| C4 Factibilidad con peso 0,50 | 0,1482 | 0,3932 | 0,4586 | Op3 Dual |

La Opción 3 sigue primera con cualquier peso de C1, C2 o C3. Solo pierde frente a la Opción 2 si C4 Factibilidad Técnica y Conectividad pesara **0,59 o más**. Hoy pesa 0,11: tendría que valer más que los otros tres criterios juntos.

Con la matriz de criterios v1 (pesos 0,4236 · 0,2270 · 0,2270 · 0,1223, CR = 0,0038), los puntajes globales serían Op3 0,5860 · Op2 0,2698 · Op1 0,1443. El ranking es el mismo: el cambio de dos juicios mueve el puntaje del ganador menos de una centésima.

## 7. Conclusión y justificación

La **Opción 3 · Plataforma Dual Adaptativa por Roles con Estado Compartido** obtiene el mayor puntaje global (**0,5922**, 59,2 % del total): 2,32 veces el de la Opción 2 (0,2554) y 3,9 veces el de la Opción 1 (0,1524). Las cinco matrices son consistentes (CR máximo = 0,0559).

1. **Gana en los tres criterios de mayor peso.** En Usabilidad (C1, w = 0,3858) obtiene 0,5695: la vista móvil guiada conserva la baja barrera de entrada de una app sencilla y además ofrece los tres módulos que exige KR3. En Valor B2B (C2) obtiene 0,6491 y en Integración (C3) 0,7153.
2. **La integración es la que crea el valor B2B.** Los diagnósticos que los caficultores hacen con la cámara alimentan el mapa de alertas de roya de la consola de cooperativas. Ese dato propio no lo puede ofrecer la Opción 1, que no tiene datos de campo, ni la Opción 2, que no tiene vista para cooperativas.
3. **Su debilidad está acotada.** La Opción 2 es mejor en Factibilidad y Conectividad (0,5714 frente a 0,2857), pero ese criterio pesa 0,1133 y la ventaja no compensa. Para mitigarla, la Opción 3 guarda los diagnósticos localmente cuando no hay conexión y solo carga las pantallas del rol activo (RNF03).
4. **La Opción 1 queda última** porque concentra la complejidad sin resolver los silos: es la arquitectura que originó la observación «las herramientas se ven desconectadas».

## 8. Nota metodológica y control de cambios

- **v1 → v2 (19-oct-2026).** (a) El cálculo pasa del método aproximado al vector propio principal exacto, con script reproducible. (b) La matriz de criterios cambia dos juicios: C1 vs C2 pasa de 2 a 1 y C1 vs C4 pasa de 3 a 4. Con esos juicios, el vector propio da pesos que coinciden con los de la diapositiva de síntesis (0,38 · 0,28 · 0,22 · 0,12) con una diferencia máxima de 0,007. Antes daba 0,42 · 0,23 · 0,23 · 0,12, que no coincidía con la diapositiva. Los pesos no se imponen a mano: salen de la matriz.
- **Sobre las cifras 0,596 · 0,297 · 0,232.** Este grupo de valores no puede salir de una síntesis AHP distributiva: suma 1,125 y los puntajes globales siempre suman 1. Con los juicios documentados, las cifras correctas son las del §5. Si alguna diapositiva tiene esos valores, hay que reemplazarlos.
- Los juicios de las matrices son del equipo CofiTech y se basan en la evidencia del proyecto: OKR, Canvas, DIB y la retroalimentación del profesor. Para reducir el sesgo, cada integrante puede llenar sus propias matrices y agregarlas con la **media geométrica** celda a celda, que es el método que recomienda Saaty para decisiones en grupo.

**Reproducir los cálculos (Python 3.11+, numpy):**

```bash
python 03_scripts/ahp/ahp_cofitech.py          # informe en consola: w, λmax, CI, CR, síntesis y sensibilidad
python 03_scripts/ahp/ahp_cofitech.py --json   # además escribe 05_resultados/ahp/ahp_resultados.json
```

El núcleo del cálculo:

```python
valores, vectores = np.linalg.eig(A)
k = np.argmax(valores.real)                 # autovalor real dominante (Perron-Frobenius)
w = np.abs(vectores[:, k].real); w /= w.sum()
lambda_max = valores[k].real
CI = (lambda_max - n) / (n - 1)
CR = CI / RI[n]                             # RI = 0,58 (n = 3) · 0,90 (n = 4); aceptar si CR < 0,10
puntajes = locales @ pesos                  # síntesis distributiva: suman 1
```
