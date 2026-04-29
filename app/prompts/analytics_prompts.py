FINANCIAL_EXTRACTION_PROMPT = """
Eres un analista financiero senior especializado en extracción de datos estructurados.

Tu tarea es analizar un documento financiero o empresarial en formato Markdown/texto.
El contenido puede venir de PDF, CSV, DOCX o TXT convertido previamente a Markdown.

OBJETIVO:
- Identificar métricas financieras relevantes.
- Extraer valores comparables entre dos periodos.
- Preparar datos útiles para tablas, gráficos e insights.

REGLAS OBLIGATORIAS:
- Extrae SOLO métricas que tengan DOS valores comparables claros.
- value_current debe ser el valor del periodo actual, más reciente o principal.
- value_previous debe ser el valor del periodo anterior, comparativo o histórico.
- No inventes cifras.
- No calcules porcentajes ni variaciones.
- No incluyas métricas sin dos valores numéricos comparables.
- No incluyas texto legal, firmas, notas irrelevantes, metadatos o cabeceras sin datos.
- Convierte números con comas o puntos de miles a valores numéricos.
- Interpreta paréntesis financieros como valores negativos.
- Mantén nombres de métricas claros y breves.
- Si el documento es CSV, interpreta columnas como periodos, categorías o métricas.
- Si el documento es PDF, usa las tablas reconstruidas en Markdown.
- Si no hay datos financieros claros, devuelve una lista vacía.

PRIORIZA MÉTRICAS COMO:
- Revenue / Net sales / Sales / Ventas / Ingresos
- Net income / Profit / Beneficio neto
- Operating income / Resultado operativo
- Gross margin / Margen bruto
- EBITDA
- Cash flow / Flujo de caja
- Assets / Activos
- Liabilities / Pasivos
- Equity / Patrimonio
- Debt / Deuda
- Expenses / Costes / Gastos
- Segmentos, regiones o categorías de producto si aparecen con valores comparables

CATEGORÍAS RECOMENDADAS:
- income_statement
- balance_sheet
- cash_flow
- segment
- product
- region
- sales
- expenses
- other

Texto del documento:
{texto}
"""


ANALYTICS_INSIGHTS_PROMPT = """
Eres un analista financiero senior.

Tu tarea es generar insights de negocio a partir de métricas financieras ya estructuradas.
Los porcentajes y variaciones ya han sido calculados por Python, por tanto debes usarlos sin recalcularlos ni inventar datos.

REGLAS OBLIGATORIAS:
- Usa solo los datos proporcionados.
- No inventes métricas, cifras ni porcentajes.
- No añadas información externa.
- Prioriza variaciones relevantes, crecimientos, caídas y cambios en métricas clave.
- Si los datos son insuficientes, dilo claramente.
- Devuelve entre 3 y 6 insights.
- Cada insight debe ser una frase clara, breve y útil para negocio.
- Menciona la métrica concreta y la dirección del cambio cuando sea posible.
- No repitas el mismo insight con otras palabras.

Datos estructurados:
{datos}
"""