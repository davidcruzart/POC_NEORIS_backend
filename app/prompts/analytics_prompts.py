ANALYTICS_INSIGHTS_PROMPT = """
Analiza las siguientes métricas financieras estructuradas y genera insights de negocio.

Reglas obligatorias:
- No inventes valores.
- Usa solo los datos proporcionados.
- No añadas cifras que no aparezcan en los datos.
- Prioriza variaciones relevantes, crecimiento, caídas y métricas clave.
- Si no hay datos suficientes, dilo claramente.
- Devuelve entre 3 y 6 insights.
- Cada insight debe ser una frase clara y breve.

Datos estructurados:
{datos}
"""


CHART_SUGGESTION_PROMPT = """
A partir de los datos estructurados proporcionados, sugiere gráficas útiles.

Reglas:
- No inventes datos.
- Usa solo los datos proporcionados.
- Sugiere solo gráficas con sentido.
- Usa bar chart para comparativas por categoría.
- Usa line chart para series temporales.
- Evita pie chart si hay demasiadas categorías.

Datos:
{datos}
"""