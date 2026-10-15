# Selección del MockUp final de CofiTech mediante AHP (Analytic Hierarchy Process)

*Metodología de ideación multicriterio (Saaty), según el curso de Data Thinking. Juicios del equipo CofiTech; cálculos reproducibles con el script incluido al final.*

## 1. Estructura jerárquica

```
NIVEL 1 · OBJETIVO
  Seleccionar la arquitectura de MockUp óptima para maximizar la adopción campesina
  y la viabilidad comercial B2B de CofiTech

NIVEL 2 · CRITERIOS
  C1 Usabilidad y Adopción Rural ........ baja barrera de entrada para el caficultor (KR1, KR3)
  C2 Valor B2B / Monetización ........... analítica accionable para Cooperativas y Comités
  C3 Integración Sistémica .............. cero silos: Visión ↔ Rendimiento ↔ RAG
  C4 Factibilidad y Resiliencia Rural ... recursos eficientes, baja dependencia de conectividad

NIVEL 3 · ALTERNATIVAS
  Op1 Dashboard Analítico Monolítico Web (9 pestañas técnicas densas)
  Op2 App Móvil Asistencial Pura (solo diagnóstico por foto y chat básico)
  Op3 Plataforma Dual Adaptativa por Roles con Estado Compartido
```

## 2. Escala fundamental de Saaty

| Valor | Significado | Recíproco |
|---:|---|---:|
| 1 | Igual importancia | 1 |
| 3 | Importancia moderada de uno sobre otro | 1/3 |
| 5 | Importancia fuerte | 1/5 |
| 7 | Importancia muy fuerte o demostrada | 1/7 |
| 9 | Importancia extrema | 1/9 |
| 2, 4, 6, 8 | Valores intermedios entre dos juicios | 1/2, 1/4, 1/6, 1/8 |

La matriz es recíproca: si *a<sub>ij</sub>* = 3, entonces *a<sub>ji</sub>* = 1/3. Una matriz es aceptable si su Razón de Consistencia (RC) es menor que 0,10.

**Procedimiento (igual para todas las matrices):** (1) sumar cada columna; (2) dividir cada celda por la suma de su columna (matriz normalizada); (3) promediar cada fila → vector de prioridad, que suma 1; (4) verificar consistencia: λmax = promedio de (A·w)<sub>i</sub>/w<sub>i</sub>, IC = (λmax − n)/(n − 1), RC = IC/IA, con IA = 0,58 para n = 3 e IA = 0,90 para n = 4.

## 3. Ponderación de los criterios (matriz 4×4)

**Juicios del equipo:**

- **C1 vs C2 = 2** · El objetivo del semestre (OKR) es validar adopción con usuarios piloto: la usabilidad del caficultor pesa un poco más que la monetización.
- **C1 vs C3 = 2** · Una plataforma muy integrada que el caficultor no adopta no genera datos ni valor.
- **C1 vs C4 = 3** · Sin adopción, la eficiencia técnica es irrelevante; la resiliencia se puede mejorar después del piloto.
- **C2 vs C3 = 1** · El valor B2B nace justamente de integrar los datos de campo con la analítica: ambos criterios se sostienen mutuamente.
- **C2 vs C4 = 2** · El modelo Freemium del Canvas depende del cliente B2B; la infraestructura es un medio.
- **C3 vs C4 = 2** · La retroalimentación del profesor («las herramientas se ven desconectadas») hace de la integración un requisito de la entrega.

**a) Matriz de comparación por pares** (fila frente a columna)

| | C1 Usabilidad | C2 Valor B2B | C3 Integración | C4 Factibilidad |
|---|---:|---:|---:|---:|
| **C1 Usabilidad** | 1 | 2 | 2 | 3 |
| **C2 Valor B2B** | 1/2 (0,500) | 1 | 1 | 2 |
| **C3 Integración** | 1/2 (0,500) | 1 | 1 | 2 |
| **C4 Factibilidad** | 1/3 (0,333) | 1/2 (0,500) | 1/2 (0,500) | 1 |
| **Suma columna** | **2,3333** | **4,5000** | **4,5000** | **8,0000** |

**b) Matriz normalizada** (cada celda ÷ suma de su columna) **y vector de prioridad** (promedio de cada fila)

| | C1 Usabilidad | C2 Valor B2B | C3 Integración | C4 Factibilidad | **Peso w** |
|---|---:|---:|---:|---:|---:|
| **C1 Usabilidad** | 0,4286 | 0,4444 | 0,4444 | 0,3750 | **0,4231** |
| **C2 Valor B2B** | 0,2143 | 0,2222 | 0,2222 | 0,2500 | **0,2272** |
| **C3 Integración** | 0,2143 | 0,2222 | 0,2222 | 0,2500 | **0,2272** |
| **C4 Factibilidad** | 0,1429 | 0,1111 | 0,1111 | 0,1250 | **0,1225** |
| **Suma** | 1,0000 | 1,0000 | 1,0000 | 1,0000 | **1,0000** |

**c) Consistencia**

| C1 Usabilidad | C2 Valor B2B | C3 Integración | C4 Factibilidad |
|---:|---:|---:|---:|
| (A·w)/w = 4,0164 | (A·w)/w = 4,0098 | (A·w)/w = 4,0098 | (A·w)/w = 4,0054 |

λmax = 4,0104 · IC = (λmax − n)/(n − 1) = 0,0035 · IA (n = 4) = 0,90 · **RC = IC/IA = 0,0038** → consistente (RC < 0,10)


**Resultado:** C1 Usabilidad = **0,4231** · C2 Valor B2B = **0,2272** · C3 Integración = **0,2272** · C4 Factibilidad = **0,1225** (suma = 1,0000).

## 4. Prioridad local de las alternativas por criterio (matrices 3×3)

### 4.1 Respecto a C1 · Usabilidad y Adopción Rural (peso 0,4231)

**Juicios:**

- **Op1 vs Op2 = 1/4** · Nueve pestañas técnicas con jerga estadística son una barrera alta en el celular del caficultor; la app asistencial es de uso inmediato.
- **Op1 vs Op3 = 1/5** · La vista de caficultor de la Op3 es móvil, guiada paso a paso («siguiente paso») y pide los datos de la finca una sola vez.
- **Op2 vs Op3 = 1/2** · La Op2 es aún más simple, pero no incluye Predicción: hace imposible KR3 (usar Visión + Predicción + RAG). Por eso la Op3 gana solo moderadamente.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 1/4 (0,250) | 1/5 (0,200) |
| **Op2 Asistencial** | 4 | 1 | 1/2 (0,500) |
| **Op3 Dual** | 5 | 2 | 1 |
| **Suma columna** | **10,0000** | **3,2500** | **1,7000** |

**b) Matriz normalizada** (cada celda ÷ suma de su columna) **y vector de prioridad** (promedio de cada fila)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual | **Prioridad local** |
|---|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,1000 | 0,0769 | 0,1176 | **0,0982** |
| **Op2 Asistencial** | 0,4000 | 0,3077 | 0,2941 | **0,3339** |
| **Op3 Dual** | 0,5000 | 0,6154 | 0,5882 | **0,5679** |
| **Suma** | 1,0000 | 1,0000 | 1,0000 | **1,0000** |

**c) Consistencia**

| Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---:|---:|---:|
| (A·w)/w = 3,0069 | (A·w)/w = 3,0264 | (A·w)/w = 3,0406 |

λmax = 3,0247 · IC = (λmax − n)/(n − 1) = 0,0123 · IA (n = 3) = 0,58 · **RC = IC/IA = 0,0213** → consistente (RC < 0,10)

### 4.2 Respecto a C2 · Generación de Valor B2B / Monetización (peso 0,2272)

**Juicios:**

- **Op1 vs Op2 = 5** · La Op1 ofrece analítica territorial (rendimiento, precios, mapa); la Op2 no tiene nada que vender a una cooperativa.
- **Op1 vs Op3 = 1/3** · La consola de la Op3 tiene la misma analítica, más las alertas fitosanitarias alimentadas por los diagnósticos de campo de los caficultores (dato propio, no disponible en fuentes abiertas).
- **Op2 vs Op3 = 1/7** · Sin vista para cooperativas no hay cliente que pague el plan avanzado del modelo Freemium.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 5 | 1/3 (0,333) |
| **Op2 Asistencial** | 1/5 (0,200) | 1 | 1/7 (0,143) |
| **Op3 Dual** | 3 | 7 | 1 |
| **Suma columna** | **4,2000** | **13,0000** | **1,4762** |

**b) Matriz normalizada** (cada celda ÷ suma de su columna) **y vector de prioridad** (promedio de cada fila)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual | **Prioridad local** |
|---|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,2381 | 0,3846 | 0,2258 | **0,2828** |
| **Op2 Asistencial** | 0,0476 | 0,0769 | 0,0968 | **0,0738** |
| **Op3 Dual** | 0,7143 | 0,5385 | 0,6774 | **0,6434** |
| **Suma** | 1,0000 | 1,0000 | 1,0000 | **1,0000** |

**c) Consistencia**

| Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---:|---:|---:|
| (A·w)/w = 3,0624 | (A·w)/w = 3,0127 | (A·w)/w = 3,1215 |

λmax = 3,0655 · IC = (λmax − n)/(n − 1) = 0,0328 · IA (n = 3) = 0,58 · **RC = IC/IA = 0,0565** → consistente (RC < 0,10)

### 4.3 Respecto a C3 · Integración Sistémica (peso 0,2272)

**Juicios:**

- **Op1 vs Op2 = 1/2** · La Op2 conecta foto y chat (dos herramientas); la Op1 tiene las tres pero en silos, cada pestaña pide sus propios datos.
- **Op1 vs Op3 = 1/7** · La Op3 comparte estado: el diagnóstico de la foto ajusta el riesgo en Rendimiento y se inyecta como contexto al RAG.
- **Op2 vs Op3 = 1/4** · La Op2 deja por fuera la predicción y el panorama regional; la integración es parcial.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 1/2 (0,500) | 1/7 (0,143) |
| **Op2 Asistencial** | 2 | 1 | 1/4 (0,250) |
| **Op3 Dual** | 7 | 4 | 1 |
| **Suma columna** | **10,0000** | **5,5000** | **1,3929** |

**b) Matriz normalizada** (cada celda ÷ suma de su columna) **y vector de prioridad** (promedio de cada fila)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual | **Prioridad local** |
|---|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,1000 | 0,0909 | 0,1026 | **0,0978** |
| **Op2 Asistencial** | 0,2000 | 0,1818 | 0,1795 | **0,1871** |
| **Op3 Dual** | 0,7000 | 0,7273 | 0,7179 | **0,7151** |
| **Suma** | 1,0000 | 1,0000 | 1,0000 | **1,0000** |

**c) Consistencia**

| Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---:|---:|---:|
| (A·w)/w = 3,0006 | (A·w)/w = 3,0011 | (A·w)/w = 3,0042 |

λmax = 3,0020 · IC = (λmax − n)/(n − 1) = 0,0010 · IA (n = 3) = 0,58 · **RC = IC/IA = 0,0017** → consistente (RC < 0,10)

### 4.4 Respecto a C4 · Factibilidad Técnica y Resiliencia Rural (peso 0,1225)

**Juicios:**

- **Op1 vs Op2 = 1/4** · La Op1 carga todos los modelos y tablas en cada sesión; la Op2 solo necesita una CNN y un chat, y podría funcionar casi sin red.
- **Op1 vs Op3 = 1/2** · La Op3 carga solo las pantallas del rol y guarda localmente si la nube no responde, pero sigue siendo una aplicación web completa.
- **Op2 vs Op3 = 2** · Reconocemos que la Op2 es la más liviana y la más resistente a la falta de conectividad: en este criterio gana.

**a) Matriz de comparación por pares** (fila frente a columna)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---|---:|---:|---:|
| **Op1 Monolítico** | 1 | 1/4 (0,250) | 1/2 (0,500) |
| **Op2 Asistencial** | 4 | 1 | 2 |
| **Op3 Dual** | 2 | 1/2 (0,500) | 1 |
| **Suma columna** | **7,0000** | **1,7500** | **3,5000** |

**b) Matriz normalizada** (cada celda ÷ suma de su columna) **y vector de prioridad** (promedio de cada fila)

| | Op1 Monolítico | Op2 Asistencial | Op3 Dual | **Prioridad local** |
|---|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,1429 | 0,1429 | 0,1429 | **0,1429** |
| **Op2 Asistencial** | 0,5714 | 0,5714 | 0,5714 | **0,5714** |
| **Op3 Dual** | 0,2857 | 0,2857 | 0,2857 | **0,2857** |
| **Suma** | 1,0000 | 1,0000 | 1,0000 | **1,0000** |

**c) Consistencia**

| Op1 Monolítico | Op2 Asistencial | Op3 Dual |
|---:|---:|---:|
| (A·w)/w = 3,0000 | (A·w)/w = 3,0000 | (A·w)/w = 3,0000 |

λmax = 3,0000 · IC = (λmax − n)/(n − 1) = 0,0000 · IA (n = 3) = 0,58 · **RC = IC/IA = 0,0000** → consistente (RC < 0,10)

## 5. Síntesis final (diapositiva 35: Alternativa = Σ Peso<sub>criterio i</sub> × Prioridad<sub>opción en criterio i</sub>)

**a) Matriz de prioridades locales y pesos de los criterios**

| Alternativa | C1 Usabilidad<br>(w = 0,4231) | C2 Valor B2B<br>(w = 0,2272) | C3 Integración<br>(w = 0,2272) | C4 Factibilidad<br>(w = 0,1225) |
|---|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,0982 | 0,2828 | 0,0978 | 0,1429 |
| **Op2 Asistencial** | 0,3339 | 0,0738 | 0,1871 | 0,5714 |
| **Op3 Dual** | 0,5679 | 0,6434 | 0,7151 | 0,2857 |

**b) Contribución ponderada (peso × prioridad local) y puntaje global**

| Alternativa | C1 Usabilidad | C2 Valor B2B | C3 Integración | C4 Factibilidad | **Puntaje global** | **Ranking** |
|---|---:|---:|---:|---:|---:|---:|
| **Op1 Monolítico** | 0,4231 × 0,0982 = 0,0415 | 0,2272 × 0,2828 = 0,0643 | 0,2272 × 0,0978 = 0,0222 | 0,1225 × 0,1429 = 0,0175 | **0,1455** | **3.º** |
| **Op2 Asistencial** | 0,4231 × 0,3339 = 0,1413 | 0,2272 × 0,0738 = 0,0168 | 0,2272 × 0,1871 = 0,0425 | 0,1225 × 0,5714 = 0,0700 | **0,2706** | **2.º** |
| **Op3 Dual** | 0,4231 × 0,5679 = 0,2403 | 0,2272 × 0,6434 = 0,1462 | 0,2272 × 0,7151 = 0,1625 | 0,1225 × 0,2857 = 0,0350 | **0,5839** | **1.º** |
| **Suma** | | | | | **1,0000** | |

**Ejemplo de cálculo (Opción 3):** (0,4231 × 0,5679) + (0,2272 × 0,6434) + (0,2272 × 0,7151) + (0,1225 × 0,2857) = 0,2403 + 0,1462 + 0,1625 + 0,0350 = **0,5839**

*Los productos se muestran redondeados a cuatro decimales; por eso su suma puede diferir en la última cifra (0,5840) del puntaje calculado sin redondear (0,5839).*

**c) Tabla comparativa final**

| Ranking | Alternativa | Puntaje global | % del total | Criterio donde gana |
|---:|---|---:|---:|---|
| 1.º | **Opción 3 · Plataforma Dual Adaptativa por Roles** | **0,5839** | 58,4 % | C1 Usabilidad, C2 Valor B2B, C3 Integración |
| 2.º | Opción 2 · App Móvil Asistencial Pura | 0,2706 | 27,1 % | C4 Factibilidad |
| 3.º | Opción 1 · Dashboard Analítico Monolítico Web | 0,1455 | 14,6 % | — |

## 6. Análisis de sensibilidad

Para comprobar que el resultado no depende de un peso puntual, se varió el peso de cada criterio de 0 a 1, repartiendo el resto entre los demás en la misma proporción:

| Escenario | Op1 | Op2 | Op3 | Ganadora |
|---|---:|---:|---:|---|
| Pesos del equipo | 0,1455 | 0,2706 | 0,5839 | Op3 Dual |
| Todos los criterios iguales (0,25) | 0,1554 | 0,2916 | 0,5530 | Op3 Dual |
| C1 Usabilidad con peso 0,50 | 0,1392 | 0,2790 | 0,5818 | Op3 Dual |
| C2 Valor B2B con peso 0,50 | 0,1940 | 0,2011 | 0,6049 | Op3 Dual |
| C3 Integración con peso 0,50 | 0,1287 | 0,2411 | 0,6302 | Op3 Dual |
| C4 Factibilidad con peso 0,50 | 0,1444 | 0,4000 | 0,4556 | Op3 Dual |

La Opción 3 se mantiene primera para cualquier peso de C1, C2 o C3. Solo pierde frente a la Opción 2 si la Factibilidad y Resiliencia (C4) pesara **0,58 o más** (hoy pesa 0,12), es decir, si el proyecto valorara la operación sin conectividad por encima de todos los demás criterios juntos.

## 7. Conclusión y justificación

La **Opción 3 · Plataforma Dual Adaptativa por Roles con Estado Compartido** obtiene el mayor puntaje global (**0,5839**, 58,4 % del total), más del doble que la Opción 2 (0,2706) y cuatro veces el de la Opción 1 (0,1455). Todas las matrices son consistentes (RC < 0,10).

1. **Gana en los tres criterios de mayor peso.** En Usabilidad (C1, peso 0,4231) obtiene 0,5679: la vista móvil guiada mantiene la baja barrera de entrada de una app sencilla, pero con los tres módulos, que es lo que exige KR3. En Valor B2B (C2) obtiene 0,6434 y en Integración (C3) 0,7151.
2. **La integración es la que crea el valor B2B.** Los diagnósticos que los caficultores hacen con la cámara alimentan el mapa de alertas de roya de la consola de cooperativas: un dato propio que ni la Opción 1 (sin datos de campo) ni la Opción 2 (sin vista para cooperativas) pueden ofrecer.
3. **Su debilidad está acotada.** La Opción 2 es mejor en Factibilidad y Resiliencia (0,5714 frente a 0,2857), pero ese criterio pesa 0,1225 y la ventaja no alcanza a compensar. Para mitigarla, la Opción 3 guarda los diagnósticos localmente cuando no hay conexión y solo carga las pantallas del rol activo.
4. **La Opción 1 queda última** porque concentra la complejidad sin resolver los silos: es la arquitectura que originó la observación «las herramientas se ven desconectadas».

## 8. Nota metodológica

- Los juicios de las matrices son del equipo CofiTech y se basan en la evidencia del proyecto (OKR, Canvas, DIB y la retroalimentación del profesor). Para reducir el sesgo, cada integrante puede llenar sus propias matrices y agregarlas con la **media geométrica** celda a celda, que es el método recomendado por Saaty para decisiones en grupo.
- Los valores se calcularon con el método aproximado (normalización por columnas y promedio por filas). El método del vector propio principal da resultados prácticamente iguales con matrices tan consistentes como estas.

**Reproducir los cálculos (Python 3.11+, numpy):**

```python
import numpy as np

IA = {3: 0.58, 4: 0.90}  # índice aleatorio de Saaty

def ahp(A):
    A = np.array(A, dtype=float)
    w = (A / A.sum(axis=0)).mean(axis=1)          # normalizar columnas y promediar filas
    lam = ((A @ w) / w).mean()                    # λmax
    n = len(A)
    rc = ((lam - n) / (n - 1)) / IA[n]            # razón de consistencia
    return w, rc

criterios = [[1, 2, 2, 3], [1/2, 1, 1, 2], [1/2, 1, 1, 2], [1/3, 1/2, 1/2, 1]]
alternativas = {   # orden: Op1, Op2, Op3
    'C1': [[1, 1/4, 1/5], [4, 1, 1/2], [5, 2, 1]],
    'C2': [[1, 5, 1/3], [1/5, 1, 1/7], [3, 7, 1]],
    'C3': [[1, 1/2, 1/7], [2, 1, 1/4], [7, 4, 1]],
    'C4': [[1, 1/4, 1/2], [4, 1, 2], [2, 1/2, 1]],
}
w_crit, rc = ahp(criterios)
locales = np.column_stack([ahp(m)[0] for m in alternativas.values()])
print('Pesos criterios:', w_crit.round(4), 'RC =', round(rc, 4))
print('Puntaje global:', (locales @ w_crit).round(4))   # [Op1, Op2, Op3]
```
