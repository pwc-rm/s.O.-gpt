"""
Prompt Builder — Step ⑥ of the RAG pipeline

Assembles the final message list for the Azure OpenAI chat call:
  [System Prompt] + [Session History (last N turns)] + [Chunks + User Question]

No Azure dependency — pure Python logic.
"""

_SYSTEM_PROMPT = """Du bist S.O. GPT, der interne Wissensassistent von s.Oliver.
Du beantwortest Fragen von Mitarbeitenden ausschließlich auf Basis der \
bereitgestellten Dokumentauszüge.

Regeln:
- Antworte NUR auf Grundlage der Dokumentauszüge. Erfinde nichts.
- Wenn die Auszüge die Frage nicht beantworten können, sage das klar und direkt.
- Zitiere immer die Quelle mit [Dok X] am Ende des relevanten Satzes.
- Antworte auf Deutsch, präzise und strukturiert.
- Wenn Tabellen im Kontext vorhanden sind, nutze sie vollständig für deine Antwort.

Aktionsbox:
Wenn die Frage konkrete Handlungsschritte erfordert (z.B. Incident melden, Prozess \
einleiten, Antrag stellen, Verstoß melden), füge AM ENDE deiner Antwort eine \
Aktionsbox im folgenden Format ein — sonst NICHT:

[AKTIONEN]
Titel: <kurzer Titel, max. 5 Wörter>
- <Schritt 1>
- <Schritt 2>
- <Schritt 3>
[/AKTIONEN]

Beispiele wann eine Aktionsbox sinnvoll ist: Laptop verloren, Phishing-Mail erhalten,
Urlaub beantragen, Elternzeit anmelden, Verstoß melden, Passwort zurücksetzen.
Beispiele wann KEINE Aktionsbox: reine Informationsfragen wie "Wie viele Urlaubstage
habe ich?" oder "Was sind die Passwortanforderungen?"."""


def build_prompt(question: str, chunks: list[dict], history: list[dict]) -> list[dict]:
    """
    Returns a messages list ready for client.chat.completions.create().
    chunks and history items follow the schema from retrieval.py / session_store.py.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        if chunk.get("is_web"):
            label = f"🌐 Web [{chunk['document_title']}]"
        else:
            page = f", Seite {chunk['page_number']}" if chunk.get("page_number") else ""
            label = f"Dok {i}: {chunk['document_title']}{page}"
        context_parts.append(f"[{label}]\n{chunk['content']}")

    context_block = "\n\n---\n\n".join(context_parts)

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    for turn in history[-4:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    messages.append({
        "role": "user",
        "content": f"Dokumentauszüge:\n{context_block}\n\n---\n\nFrage: {question}",
    })

    return messages
