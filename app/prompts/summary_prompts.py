DIRECT_SUMMARY_PROMPT = """
Resume el siguiente texto en español.

Instrucciones:
- El resumen debe tener aproximadamente {palabras_objetivo} palabras.
- Elimina detalles secundarios y repeticiones.
- Mantén la coherencia y las ideas principales del texto original.
- No inventes información.
- Devuelve solo el resumen, sin introducciones ni comentarios adicionales.

Texto a resumir:
{texto}
"""

PARTIAL_SUMMARY_PROMPT = """
Resume el siguiente bloque de texto en español.

Instrucciones:
- El resumen debe tener aproximadamente {palabras_objetivo} palabras.
- Elimina detalles secundarios y repeticiones.
- Conserva las ideas principales.
- No inventes información.
- Devuelve solo el resumen, sin introducciones ni comentarios adicionales.

Texto a resumir:
{texto}
"""

FINAL_SUMMARY_PROMPT = """
A partir de los siguientes resúmenes parciales, genera un resumen final en español.

Instrucciones:
- El resumen final debe tener aproximadamente {palabras_objetivo} palabras.
- Unifica la información.
- Elimina redundancias.
- Mantén coherencia global.
- No inventes información.
- Devuelve solo el resumen final, sin introducciones ni comentarios adicionales.

Resúmenes parciales:
{texto}
"""