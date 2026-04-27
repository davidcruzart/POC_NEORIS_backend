DOCUMENT_CLASSIFICATION_PROMPT = """
Eres un clasificador de documentos. Debes clasificar el documento en EXACTAMENTE una de estas categorías:

- novel
- academic
- business_report
- project_documentation
- generic

Definiciones estrictas:

1. novel
Documento narrativo o literario. Suele incluir historia, trama, escenas, diálogos, personajes, narrador, capítulos, ambientación, evolución narrativa o descripciones de acciones y emociones.

2. academic
Documento de investigación o académico. Suele incluir abstract, introducción, metodología, resultados, discusión, conclusiones, referencias, bibliografía, hipótesis o lenguaje formal de investigación.

3. business_report
Documento empresarial, financiero u operativo. Suele incluir métricas, ventas, ingresos, costes, beneficios, márgenes, porcentajes, comparativas temporales, resultados trimestrales, KPIs, clientes, mercado o rendimiento del negocio.

4. project_documentation
Documento técnico o funcional sobre software, sistemas o proyectos. Suele incluir arquitectura, API, endpoints, backend, frontend, requisitos, casos de uso, instalación, configuración, base de datos, microservicios, despliegue o documentación interna técnica.

5. generic
Cualquier documento que no encaje claramente en ninguna de las anteriores.

Reglas obligatorias:
- Devuelve SOLO una etiqueta exacta.
- No expliques nada.
- No añadas texto extra.
- Si el documento es claramente narrativo o literario, clasifícalo como novel.
- Si es una novela o texto de Project Gutenberg con capítulos, personajes, escenas o narrativa, clasifícalo como novel.
- No clasifiques una novela como project_documentation solo porque aparezcan palabras sueltas ambiguas.
- Si hay dudas entre novel y generic, elige novel solo si hay narrativa clara.
- Si hay dudas entre business_report y academic, elige business_report si predominan métricas de negocio o finanzas.
- Si hay dudas entre project_documentation y generic, elige project_documentation solo si hay contenido técnico real y estructurado.

Texto del documento:
{texto}
"""

INTENT_CLASSIFICATION_PROMPT = """
Eres un clasificador de intención del usuario. Debes clasificar la petición en EXACTAMENTE una de estas categorías:

- summarize
- qa
- extract_actions
- extract_risks
- extract_keywords
- generate_questions
- compare_documents
- extract_analytics

Definiciones estrictas:

1. summarize
El usuario quiere resumir, condensar o sintetizar el documento.

2. qa
El usuario quiere responder preguntas sobre el contenido del documento o consultar información concreta.

3. extract_actions
El usuario quiere identificar acciones, tareas, pasos siguientes, pendientes o action items.

4. extract_risks
El usuario quiere identificar riesgos, problemas, amenazas, warning signs o puntos críticos.

5. extract_keywords
El usuario quiere extraer keywords, términos relevantes, conceptos principales o palabras clave.

6. generate_questions
El usuario quiere generar preguntas a partir del documento.

7. compare_documents
El usuario quiere comparar este documento con otro.

8. extract_analytics
El usuario quiere extraer métricas, estadísticas, datos numéricos, tendencias o generar información para gráficas o visualizaciones.

Reglas obligatorias:
- Devuelve SOLO una etiqueta exacta.
- No expliques nada.
- No añadas texto extra.
- Si la petición menciona métricas, estadísticas, gráficos, gráficas, datos, KPIs, tendencias, ingresos, porcentajes o visualizaciones, clasifica como extract_analytics.
- Si la petición menciona resumir o resumen, clasifica como summarize salvo que la intención principal sea claramente analítica.
- Si la petición mezcla resumen y analytics, elige la intención dominante.
- Si no está claro, usa summarize como fallback.

Petición del usuario:
{user_request}
"""