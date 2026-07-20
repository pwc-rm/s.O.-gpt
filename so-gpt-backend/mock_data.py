"""
Mock-Daten für Demo-Features (Übergabe-Checkliste, Abwesenheitsnotiz).

Feste, persistente Beispieldaten, die Kalender und Postfach des Nutzers simulieren.
Bei einer entsprechenden Anfrage wird der passende Kontext in den Prompt injiziert,
damit GPT-4o ein personalisiertes Dokument erzeugen kann. Nichts hiervon ist echt —
die Daten sind bewusst konstant, damit die Demo jedes Mal identisch wirkt.
"""
from __future__ import annotations

from typing import Optional


MOCK_USER = {
    "name": "Jan Hoffmann",
    "role": "Category Manager Womenswear",
    "team": "Produktmanagement",
    "email": "jan.hoffmann@soliver.com",
}

MOCK_VERTRETUNG = {
    "name": "Nina Wagner",
    "role": "Category Managerin Menswear",
    "email": "nina.wagner@soliver.com",
}

# Termine während der geplanten Abwesenheit. "wichtig": True → im Dokument markieren.
MOCK_CALENDAR = [
    {"titel": "Q3 Sortiments-Review", "datum": "08.07.2026", "wichtig": True,
     "detail": "Board-Level Review der Herbst/Winter-Sortimente"},
    {"titel": "Kundentermin: Retail-Partner Nord", "datum": "09.07.2026", "wichtig": True,
     "detail": "Konditionsgespräch, Vorbereitung liegt in der Ablage"},
    {"titel": "Lieferanten-Call Winterkollektion", "datum": "07.07.2026", "wichtig": True,
     "detail": "Terminbestätigung Musterversand"},
    {"titel": "Weekly Team-Sync Produktmanagement", "datum": "07.07.2026", "wichtig": False,
     "detail": "Routine, kann an die Vertretung delegiert werden"},
    {"titel": "1:1 mit Sabine Keller (People & Culture)", "datum": "10.07.2026", "wichtig": False,
     "detail": "Unkritisch, kann verschoben werden"},
]

# Offene Themen aus dem Postfach.
MOCK_EMAILS = [
    {"thema": "Freigabe Herbst-Kampagne Visuals", "status": "wartet auf deine Freigabe"},
    {"thema": "Budgetplan Q4 — Rückfrage Controlling", "status": "Antwort ausstehend"},
    {"thema": "Musterversand Winterkollektion", "status": "Terminbestätigung offen"},
]


# ── Erkennung ────────────────────────────────────────────────────────────────
# OOO wird zuerst geprüft, weil "Abwesenheitsnotiz" spezifischer ist als das
# bloße "Abwesenheit" in der Übergabe-Anfrage.
# Keywords sind ASCII-normalisiert (ue/ae/oe/ss), damit sowohl "Übergabe" als
# auch "Uebergabe" erkannt werden — Nutzer tippen Umlaute oft als ue/ae/oe.
_OOO_KEYWORDS = (
    "abwesenheitsnotiz", "abwesenheitsmeldung", "abwesenheits-notiz",
    "out of office", "out-of-office", "ooo", "autoreply", "auto-reply",
    "abwesenheitsassistent",
)
_HANDOVER_KEYWORDS = (
    "uebergabe", "uebergeben", "handover", "uebergabecheckliste", "uebergabe-checkliste",
)


def _normalize(text: str) -> str:
    """Lowercase and expand German umlauts so 'Übergabe' and 'Uebergabe' match alike."""
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return t


def detect_doc_kind(question: str) -> Optional[str]:
    """Returns 'ooo', 'handover' or None based on the user's request."""
    q = _normalize(question)
    if any(k in q for k in _OOO_KEYWORDS):
        return "ooo"
    if any(k in q for k in _HANDOVER_KEYWORDS):
        return "handover"
    return None


# ── Kontext-Builder ──────────────────────────────────────────────────────────

def _fmt_calendar() -> str:
    lines = []
    for e in MOCK_CALENDAR:
        flag = " [WICHTIG]" if e["wichtig"] else ""
        lines.append(f"- {e['datum']}: {e['titel']}{flag} — {e['detail']}")
    return "\n".join(lines)


def _fmt_emails() -> str:
    return "\n".join(f"- {e['thema']} ({e['status']})" for e in MOCK_EMAILS)


def build_handover_context() -> str:
    """System-message content instructing the model to build a personal handover checklist."""
    v = MOCK_VERTRETUNG
    return (
        "AUFGABE — Persönliche Übergabe-Checkliste:\n"
        "Der Nutzer plant eine Abwesenheit und bittet um eine Übergabe-Checkliste. "
        "Für DIESE Aufgabe gilt die 'nur Dokumentauszüge'-Regel NICHT — nutze die folgenden "
        "simulierten Daten aus Kalender und Postfach des Nutzers als Grundlage. Erfinde keine "
        "zusätzlichen Termine oder Themen.\n\n"
        f"Nutzer: {MOCK_USER['name']}, {MOCK_USER['role']} ({MOCK_USER['team']})\n"
        f"Vertretung: {v['name']}, {v['role']} ({v['email']})\n\n"
        f"Anstehende Termine während der Abwesenheit:\n{_fmt_calendar()}\n\n"
        f"Offene Themen im Postfach:\n{_fmt_emails()}\n\n"
        "Erstelle als Canvas eine strukturierte Übergabe-Checkliste mit sinnvollen Abschnitten "
        "(z.B. 'Offene Aufgaben', 'Wichtige Termine', 'Vertretung & Ansprechpartner'). "
        "Hebe die mit [WICHTIG] markierten Termine deutlich hervor und ergänze bei JEDEM "
        "wichtigen Termin explizit den Hinweis, dass noch zu klären ist, ob er abgesagt oder an "
        "die Vertretung übergeben werden soll. Das Wort [WICHTIG] selbst NICHT ausgeben. "
        "Nutze den Canvas-Marker [[CANVAS_START:Übergabe bei Abwesenheit]] … [[CANVAS_END]]."
    )


def build_ooo_context(von: Optional[str], bis: Optional[str]) -> str:
    """System-message content instructing the model to write an out-of-office note."""
    v = MOCK_VERTRETUNG
    if von and bis:
        zeitraum = f"Zeitraum (aus dem bereits eingereichten Urlaubsantrag): {von} bis {bis}."
    else:
        zeitraum = (
            "Es wurde noch kein Urlaubsantrag eingereicht — verwende die Platzhalter "
            "[Startdatum] und [Enddatum], die der Nutzer selbst einträgt."
        )
    return (
        "AUFGABE — Abwesenheitsnotiz (Out-of-Office):\n"
        "Der Nutzer möchte eine Abwesenheitsnotiz für seine E-Mails. Für DIESE Aufgabe gilt die "
        "'nur Dokumentauszüge'-Regel NICHT.\n\n"
        f"{zeitraum}\n"
        f"Vertretung für dringende Anliegen: {v['name']}, {v['role']} ({v['email']})\n\n"
        "Schreibe als Canvas eine freundliche, professionelle deutsche Abwesenheitsnotiz mit dem "
        "genannten Zeitraum und der Vertretung als Kontakt. Füge darunter eine englische Version "
        "an. Nutze den Canvas-Marker [[CANVAS_START:Abwesenheitsnotiz]] … [[CANVAS_END]]."
    )
