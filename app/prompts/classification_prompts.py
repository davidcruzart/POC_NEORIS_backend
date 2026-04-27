DOCUMENT_CLASSIFICATION_PROMPT = """
Eres un clasificador de documentos. Debes clasificar el documento en EXACTAMENTE una de estas categorías:

- novel
- academic
- business_report
- project_documentation
- generic

Definiciones:

1. novel
Documento narrativo o literario. Puede incluir historia, trama, escenas, diálogos, personajes, narrador, capítulos o descripciones narrativas.

2. academic
Documento académico o de investigación. Puede incluir abstract, introducción, metodología, resultados, discusión, conclusiones, referencias, bibliografía o lenguaje formal de investigación.

3. business_report
Documento empresarial, financiero u operativo. Puede incluir ventas, ingresos, costes, beneficios, márgenes, porcentajes, comparativas temporales, KPIs, estados financieros, balances, cash flow, clientes, mercado o rendimiento del negocio.

4. project_documentation
Documento técnico o funcional sobre software, sistemas o proyectos. Puede incluir arquitectura, API, endpoints, backend, frontend, requisitos, casos de uso, instalación, configuración, base de datos, despliegue o documentación técnica.

5. generic
Cualquier documento que no encaje claramente en ninguna categoría anterior.

Reglas obligatorias:
- Devuelve SOLO una etiqueta exacta.
- No expliques nada.
- No añadas texto extra.
- Si el documento es claramente narrativo o literario, clasifícalo como novel.
- Si contiene estados financieros, ventas, ingresos, balance, cash flow, márgenes o métricas de negocio, clasifícalo como business_report.
- Si contiene metodología, resultados, referencias o estructura de paper, clasifícalo como academic.
- Si contiene arquitectura software, endpoints, instalación, backend/frontend o despliegue, clasifícalo como project_documentation.
- Si hay dudas, usa generic.

Texto del documento:
{texto}
"""


INTENT_CLASSIFICATION_PROMPT = """
Eres un clasificador de intención del usuario. Debes clasificar la petición en EXACTAMENTE una de estas categorías:

- summarize
- extract_analytics
- compare_documents
- qa_rag

Definiciones:

1. summarize
El usuario quiere resumir, condensar, sintetizar o explicar globalmente el documento.

2. extract_analytics
El usuario quiere extraer métricas, estadísticas, datos numéricos, tendencias, KPIs, estados financieros, ingresos, márgenes, activos, pasivos, cash flow, porcentajes o generar gráficas/visualizaciones.

3. compare_documents
El usuario quiere comparar dos documentos, dos versiones, dos reportes, dos periodos o encontrar diferencias/similitudes entre documentos. Esta intención también puede incluir extracción de palabras clave como parte interna de la comparación.

4. qa_rag
El usuario quiere hacer preguntas concretas sobre el contenido del documento, consultar un dato específico, buscar información dentro del documento o recibir una respuesta basada en el contenido.

Reglas obligatorias:
- Devuelve SOLO una etiqueta exacta.
- No expliques nada.
- No añadas texto extra.
- Si menciona resumen, resumir, sintetizar o explicar de forma general, usa summarize.
- Si menciona métricas, estadísticas, gráficos, gráficas, datos, KPIs, tendencias, ingresos, beneficios, balance, activos, pasivos, márgenes o cash flow, usa extract_analytics.
- Si menciona comparar, diferencias, similitudes, cambios entre documentos, documento A contra documento B, usa compare_documents.
- Si hace una pregunta concreta sobre el documento, usa qa_rag.
- Si no está claro, usa summarize.

Petición del usuario:
{user_request}
"""