DOCUMENT_CLASSIFICATION_PROMPT = """
Clasifica el siguiente documento en una de estas categorías:

- novel
- academic
- business_report
- project_documentation
- generic

Devuelve solo una categoría válida.

Texto:
{texto}
"""

INTENT_CLASSIFICATION_PROMPT = """
Clasifica la intención del usuario en una de estas categorías:

- summarize
- qa
- extract_actions
- extract_risks
- extract_keywords
- generate_questions
- compare_documents

Devuelve solo una categoría válida.

Petición del usuario:
{user_request}
"""