DOCUMENT_COMPARISON_PROMPT = """
Eres un analista senior de software.

Compara los dos documentos y extrae información clara, breve y útil.

OBJETIVO:
- Detectar similitudes clave.
- Detectar diferencias clave.
- Identificar ventajas y desventajas de cada documento/proyecto.
- Generar una conclusión comparativa final.

REGLAS:
- Usa solo el contenido proporcionado.
- No inventes información.
- No añadas conocimiento externo.
- Usa frases cortas.
- Máximo 5 elementos por sección.
- No escribas párrafos largos.
- No repitas la misma idea.
- Las ventajas y desventajas deben derivarse de diferencias reales.
- Prioriza diferencias funcionales, arquitectura, tecnologías, autenticación, persistencia, despliegue, colaboración, seguridad, escalabilidad y experiencia de usuario.

FORMATO ESPERADO:
- Resumen breve del documento A.
- Resumen breve del documento B.
- Palabras clave del documento A.
- Palabras clave del documento B.
- Similitudes.
- Diferencias.
- Ventajas del documento A.
- Desventajas del documento A.
- Ventajas del documento B.
- Desventajas del documento B.
- Conclusión final.

Documento A:
{document_a}

Documento B:
{document_b}

Petición del usuario:
{user_request}
"""