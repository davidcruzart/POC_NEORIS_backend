ANALYTICS_EXTRACTION_PROMPT = """
Analiza el siguiente documento y extrae información de negocio útil en formato estructurado.

Objetivos:
- detectar métricas numéricas
- detectar porcentajes
- detectar comparativas
- detectar si hay datos que puedan representarse en gráficas
- no inventar ningún valor
- devolver únicamente datos que estén explícitos o claramente inferibles del texto

Texto:
{texto}
"""

CHART_SUGGESTION_PROMPT = """
A partir de los datos extraídos de un documento, propone gráficas útiles.

Reglas:
- no inventes datos
- sugiere solo gráficas con sentido
- usa bar chart para comparativas por categoría
- usa line chart para series temporales
- evita pie chart si hay demasiadas categorías

Datos:
{datos}
"""