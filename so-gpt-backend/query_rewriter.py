"""
Query Rewriting — Step ③ of the RAG pipeline

Calls Azure OpenAI (via AI Foundry Gateway) to resolve follow-up questions
into standalone search queries using session history as context.

Degradation: if OpenAI is not yet configured, returns the original question
unchanged. Retrieval quality will be lower for follow-up questions, but the
pipeline does not break.
"""
from __future__ import annotations
import logging

import config

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Du bist ein Query-Rewriting-Assistent.
Deine Aufgabe: Wandle die aktuelle Nutzerfrage unter Berücksichtigung der \
Gesprächshistorie in eine vollständige, eigenständige Suchanfrage um.
Löse Pronomen und Bezüge auf (z.B. "Wie viele Tage bekomme ich?" → \
"Wie viele Urlaubstage haben Mitarbeitende bei s.Oliver?").
Gib NUR die umformulierte Frage zurück, keine Erklärung."""


def rewrite_query(question: str, history: list[dict]) -> str:
    """
    Returns a standalone version of `question` with references resolved.
    Falls back to the original question if no history or OpenAI not configured.
    """
    if not history:
        return question

    if not (config.OPENAI_ENDPOINT and config.OPENAI_API_KEY):
        logger.warning("OpenAI not configured — skipping query rewriting")
        return question

    history_text = "\n".join(
        f"Nutzer: {t['question']}\nAssistent: {t['answer'][:300]}"
        for t in history[-3:]
    )

    from openai import AzureOpenAI
    client = AzureOpenAI(
        azure_endpoint=config.OPENAI_ENDPOINT,
        api_key=config.OPENAI_API_KEY,
        api_version=config.OPENAI_API_VERSION,
    )
    response = client.chat.completions.create(
        model=config.OPENAI_QUERY_REWRITE_DEPLOYMENT,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Gesprächshistorie:\n{history_text}\n\n"
                f"Aktuelle Frage: {question}"
            )},
        ],
        max_tokens=200,
        temperature=0,
    )
    return response.choices[0].message.content.strip()