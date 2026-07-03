# Canvas & Urlaubsantrag – Implementierungs­dokumentation

Diese Dokumentation beschreibt, wie die beiden interaktiven Features von **s.O. GPT**
umgesetzt sind:

1. **Canvas** – längere, strukturierte Dokumente (Checklisten, Zusammenfassungen,
   Merkblätter) werden nicht im Chat, sondern in einem eigenen Panel erzeugt und
   live hineingeschrieben.
2. **Urlaubsantrag-Assistent** – ein geführter, mehrstufiger Dialog vom
   Urlaubsanspruch über das Urlaubskonto bis zum ausgefüllten Antragsformular.

Der zentrale Gedanke bei beiden Features ist dasselbe Architekturmuster:

> **Das Sprachmodell liefert Inhalt und setzt „Marker".
> Deterministischer Frontend-/Backend-Code interpretiert diese Marker und steuert
> das Verhalten.**

So bleibt die Freiheit des Modells (guter, kontextbezogener Text) erhalten, während
das *Verhalten* (wann öffnet sich ein Canvas, welcher Schritt kommt als Nächstes)
verlässlich und demo-sicher bleibt.

---

## 1. Deterministisch vs. modellgesteuert – der Überblick

| Aspekt | Wer entscheidet? | Mechanismus |
|---|---|---|
| **Formulierung des Textes** | 🤖 Modell | GPT‑4o Streaming |
| **Ob ein Canvas erzeugt wird** | 🤖 Modell schlägt vor → ⚙️ Code bestätigt | `[[CANVAS_START]]`-Marker **+** deterministischer Intent-Guard |
| **Wie der Canvas gerendert/gespeichert wird** | ⚙️ Deterministisch | `formatAnswer`, Cosmos DB |
| **Diff bei Canvas-Ergänzung (Accept/Reject)** | ⚙️ Deterministisch | `appendToCanvas` / `acceptDiff` |
| **Urlaub – erste Antwort (Anspruch + Angebot)** | 🤖 Modell (RAG) | System-Prompt-Ablauf |
| **Urlaub – Saldo- und Formular-Schritt** | ⚙️ **Voll deterministisch** | `_urlaub_flow_shortcut` (kein LLM-Aufruf) |
| **Widgets (Urlaubskonto-Karte, Formular)** | ⚙️ Deterministisch | Marker `[[URLAUB_SALDO]]` / `[[URLAUB_FORMULAR]]` |

Legende: 🤖 = Sprachmodell · ⚙️ = fester Code

---

## 2. Das gemeinsame Muster: Marker

Beide Features nutzen **Marker im Antworttext** als Schnittstelle zwischen Modell und
Anwendung. Ein Marker ist ein eindeutiges Textsymbol, das der Nutzer nie zu sehen
bekommt – der Frontend-Code fängt es ab, entfernt es aus dem sichtbaren Text und
löst stattdessen eine Aktion aus.

| Marker | Bedeutung | Erzeugt von |
|---|---|---|
| `[[CANVAS_START:Titel]] … [[CANVAS_END]]` | Neues Canvas-Dokument | Modell |
| `[[CANVAS_APPEND:Titel]] … [[CANVAS_END]]` | Abschnitt zu bestehendem Canvas ergänzen | Modell |
| `[[URLAUB_SALDO]]` | Urlaubskonto-Karte einblenden | Backend (deterministisch) |
| `[[URLAUB_FORMULAR]]` | Antragsformular einblenden | Backend (deterministisch) |
| `[AKTIONEN] … [/AKTIONEN]` | Handlungs-Box mit Schritten | Modell |

Die Marker sind bewusst „hässlich" und unwahrscheinlich in normalem Text, damit sie
nie versehentlich getriggert werden.

---

## 3. Canvas-Feature

### 3.1 Wie das Modell einen Canvas auslöst

Der **System-Prompt** (`prompt_builder.py`) weist das Modell an, bei expliziten
Dokumenten-Anfragen zuerst einen kurzen Einleitungssatz zu schreiben und danach den
Inhalt in Marker zu setzen:

```
Kurzer Einleitungssatz (1 Zeile).
[[CANVAS_START:Kurzer Titel (max 5 Wörter)]]
<vollständiger Dokumentinhalt in Markdown>
[[CANVAS_END]]
```

Der Prompt enthält **explizite Verbote** (z. B. niemals Canvas bei Urlaubsfragen oder
reinen Faktenfragen), damit das Modell nicht bei jeder langen Antwort ein Canvas
öffnet.

### 3.2 Deterministische Schutzschicht (Intent-Guard)

Man kann sich nicht allein darauf verlassen, dass das Modell die Prompt-Regeln
befolgt. Deshalb gibt es im Frontend einen **deterministischen Guard**: Ein Canvas
wird nur zugelassen, wenn die *Nutzerfrage* ein Erstellungs-Stichwort enthält.

```js
const _canvasTrigger =
  /erstell|schreib|fass zusammen|mach mir|erstelle (ein|eine[mn]?)|dokument|
   checkliste|übersicht|merkblatt|plan|leitfaden|zusammenfassung|
   füg|ergänz|erweiter|abschnitt|hinzu/i;

const _questionAllowsCanvas = _canvasTrigger.test(_lastUserMessage);
```

Selbst wenn das Modell fälschlich `[[CANVAS_START]]` ausgibt, aber die Frage kein
Trigger-Wort enthält (z. B. „Wie viele Urlaubstage habe ich?"), wird **kein** Canvas
geöffnet – der Marker wird stattdessen entfernt.

### 3.3 Live-Streaming in den Canvas

Während die SSE-Tokens ankommen (`updateStreamBubble`), wird der Rohtext laufend auf
Marker geprüft:

- **Vor** dem Marker: normaler Einleitungstext landet in der Chat-Blase.
- **Ab** `[[CANVAS_START:`: Der Inhalt wird **live in das Canvas-Panel** geschrieben
  (`_streamCanvasContent`), während in der Chat-Blase nur ein Hinweis
  „📄 *Titel* ▌" mit Streaming-Cursor steht.

Die Chat-Blase zeigt am Ende also **nur** den Einleitungssatz + einen Button
„Canvas öffnen ↗" – der eigentliche Inhalt lebt im Canvas.

Ein `setTimeout(…, 0)` beim Abschluss (`formatAnswer`) rendert den finalen Markdown,
speichert in Cosmos und verknüpft den Chat-Button mit der Canvas-ID. Die Variable
`_streamingCanvasId` koordiniert dabei die Streaming- und die Finalisierungs-Phase,
damit **kein Canvas doppelt** angelegt wird.

### 3.4 Ergänzungen & Diff-Engine (deterministisch)

Bittet der Nutzer um eine Ergänzung, gibt das Modell `[[CANVAS_APPEND:Titel]]` aus.
Das Frontend zeigt den neuen Abschnitt als **grünen Diff-Block** mit
**Übernehmen / Verwerfen**-Buttons:

- `appendToCanvas()` merkt sich den ausstehenden Diff (`_pendingDiff`).
- `acceptDiff()` hängt den Abschnitt deterministisch als `## Titel` an den Inhalt an,
  speichert und rendert neu.
- `rejectDiff()` verwirft ihn.

Das Zusammenführen selbst ist reiner Code – das Modell entscheidet **nicht**, wie
gemergt wird.

### 3.5 Persistenz & Wiederherstellung (Cosmos DB)

Canvas-Dokumente werden in derselben Cosmos-Container gespeichert wie die Chat-Turns,
unterschieden durch `doc_type: "canvas"` (siehe [Datenmodell](#7-datenmodell-cosmos-db)).
Gespeichert werden `title`, `content` (Roh-Markdown **inkl.** `[Dok X]`-Marker) und
`sources`.

Beim Öffnen eines alten Chats (`loadSession`) werden die Canvases **vor** den
Nachrichten aus Cosmos geladen. Die Chat-Blasen werden dann im **Replay-Modus**
gerendert (`formatAnswer(text, sources, { replay: true })`):

- **Kein** erneutes Anlegen, **kein** erneuter Diff-Dialog.
- Die „Canvas öffnen"-Buttons in der Historie werden per Titel mit den bereits
  geladenen Canvases verknüpft.

Dieser Replay-Modus ist wichtig, weil `formatAnswer` sonst Seiteneffekte hätte
(Canvas anlegen, Diff auslösen) – beim Nachladen der Historie wäre das falsch.

### 3.6 Quellen im Canvas als klickbare Chips

Im Canvas werden dieselben klickbaren Quellen-Chips angezeigt wie im Chat (z. B.
„s.Oliver IT-Sicherheit" statt „Dok 1"). Damit das **auch nach dem Neuladen**
konsistent bleibt:

- Der **Rohinhalt** mit den `[Dok X]`-Markern wird gespeichert.
- Die **Quellenliste** wird pro Canvas mitgespeichert (`sources`).
- Beim Rendern werden Marker + Quellen zu Chips aufgelöst; fehlen Quellen, werden die
  Marker sauber entfernt (nie ein nacktes „Dok 1").

---

## 4. Urlaubsantrag-Assistent

Der Urlaubs-Flow ist ein bewusst **hybrides** Feature: Der Einstieg ist
modellgesteuert (echte RAG-Antwort), die kritischen Bestätigungsschritte sind
**voll deterministisch**.

### 4.1 Schritt 1 – Anspruch + Angebot (modellgesteuert, RAG)

Fragt jemand allgemein nach Urlaub, läuft eine normale RAG-Antwort. Der System-Prompt
weist das Modell an:

- den allgemeinen Anspruch aus den Dokumenten mit Quelle zu nennen,
- **keine** persönlichen Zahlen zu nennen,
- proaktiv anzubieten: *„Möchtest du, dass ich in deinem persönlichen Urlaubskonto
  nachsehe …?"*

### 4.2 Schritte 2 & 3 – Saldo und Formular (voll deterministisch)

Die beiden folgenden „Ja"-Bestätigungen dürfen **nicht** davon abhängen, dass das
Modell zwei identische „Ja" korrekt auseinanderhält. Deshalb greift **vor** jeder
Retrieval-/LLM-Logik ein deterministischer Shortcut im Backend
(`main.py → _urlaub_flow_shortcut`):

```python
def _urlaub_flow_shortcut(question, history):
    if not history or not _is_affirmative(question):
        return None
    last_answer = history[-1]["answer"]

    # Schritt 2 → 3: Saldo wurde gezeigt, Nutzer bestätigt → Formular
    if "[[URLAUB_SALDO]]" in last_answer:
        return "Gerne, hier ist das Antragsformular:\n\n[[URLAUB_FORMULAR]]"

    # Schritt 1 → 2: Angebot wurde gemacht, Nutzer bestätigt → Saldo
    if "persönlichen Urlaubskonto" in last_answer:
        return ("Ich habe dein Urlaubskonto abgerufen:\n\n[[URLAUB_SALDO]]\n\n"
                "Möchtest du direkt einen Urlaubsantrag stellen?")
    return None
```

Die Logik erkennt den nächsten Schritt **allein am vorherigen Assistenten-Turn**:

- Enthält die letzte Antwort das Angebot („persönlichen Urlaubskonto") und der Nutzer
  bejaht → **Saldo** einblenden.
- Enthält die letzte Antwort bereits den Saldo-Marker und der Nutzer bejaht →
  **Formular** einblenden.

Zustimmung wird über eine feste Wortliste erkannt (`_is_affirmative`: „ja", „gerne",
„ok", „klar" …). Trifft der Shortcut zu, wird die Antwort als **statischer Text**
gestreamt (`_stream_static`) – **kein LLM-Aufruf, keine Token-Kosten**. Ein kleiner
Delay pro Zeile sorgt für ein natürliches, nachvollziehbares Tempo.

> **Warum deterministisch?** Für eine Live-Demo muss der Ablauf
> Frage → Saldo → Formular **jedes Mal** exakt gleich funktionieren. Würde man die
> Schritt-Erkennung dem Modell überlassen, könnte es bei einem schlichten „Ja"
> gelegentlich abweichen. Der Shortcut macht den Flow „bombensicher".

### 4.3 Widgets & Persistenz

Die Marker `[[URLAUB_SALDO]]` und `[[URLAUB_FORMULAR]]` werden im Frontend
(`formatAnswer`) durch echte UI-Widgets ersetzt:

- **Urlaubskonto-Karte** – zeigt Resttage & Überstunden.
- **Antragsformular** – Datumsauswahl; nach dem Absenden wird der Antrag über
  `POST /urlaub/antrag` in Cosmos gespeichert (`doc_type: "urlaub_antrag"`, ein
  Eintrag pro Session).

Beim Wiederöffnen der Session wird ein bereits gestellter Antrag als **Timeline**
statt als leeres Formular gerendert.

---

## 5. Ablauf einer Anfrage (End-to-End)

```
Nutzerfrage
   │
   ▼
POST /chat  (main.py)
   │
   ├─ Ist es ein "Ja" im Urlaubs-Flow?  ──► JA ──► _stream_static(Marker)   [deterministisch, kein LLM]
   │                                                      │
   │                                                      ▼
   │                                          Frontend ersetzt Marker durch Widget
   │
   └─ NEIN ──► RAG-Pipeline (Retrieval → Prompt → GPT-4o Streaming)
                    │
                    ▼
             SSE-Tokens ans Frontend
                    │
        ┌───────────┴───────────────┐
        ▼                           ▼
  [[CANVAS_*]] erkannt?       normaler Text
        │  (+ Intent-Guard)          │
        ▼                            ▼
  Live in Canvas-Panel        Chat-Blase
  + Speichern in Cosmos
```

---

## 6. Beteiligte Dateien

| Datei | Rolle |
|---|---|
| `so-gpt-backend/static/index.html` | Gesamtes Frontend: Marker-Erkennung, Canvas-Panel, Diff-Engine, Widgets, Persistenz-Aufrufe |
| `so-gpt-backend/prompt_builder.py` | System-Prompt: wann Canvas-Marker, Urlaubs-Ablauf, Verbote |
| `so-gpt-backend/main.py` | `/chat`-Endpoint, deterministischer Urlaubs-Shortcut (`_urlaub_flow_shortcut`, `_stream_static`), Canvas- und Urlaubs-Endpoints |
| `so-gpt-backend/session_store.py` | Cosmos-Zugriff: Sessions, Canvases (`save_canvas`/`list_canvases`), Urlaubsanträge |

### Wichtige Funktionen (Frontend)

| Funktion | Zweck |
|---|---|
| `updateStreamBubble` | Trennt während des Streamings Chat-Text von Canvas-Inhalt |
| `_streamCanvasContent` | Schreibt Tokens live ins Canvas-Panel |
| `formatAnswer` | Finale Verarbeitung: Marker→Widgets/Canvas, Markdown, Quellen-Chips; `replay`-Modus für Historie |
| `appendToCanvas` / `acceptDiff` / `rejectDiff` | Diff-Engine für Ergänzungen |
| `_renderCanvasMd` | Rendert Canvas-Markdown inkl. Quellen-Chips |
| `_saveCanvasToDB` | Persistiert Canvas (Inhalt + Quellen) nach Cosmos |

---

## 7. Datenmodell (Cosmos DB)

Ein Container, partitioniert nach `session_id`. Das Feld `doc_type` unterscheidet die
Dokumenttypen:

| `doc_type` | Inhalt |
|---|---|
| *(nicht gesetzt)* | Normaler Q&A-Turn (`question`, `answer`, `sources`, Tokens) |
| `canvas` | Canvas-Dokument (`canvas_id`, `title`, `content`, `sources`) |
| `urlaub_antrag` | Urlaubsantrag (`von`, `bis`, `days`, `overtime`, `status`) |

Die Session-Liste (Recent Chats) nutzt als Titel die **erste** Frage der Session
(nicht die neueste), sortiert nach letzter Aktivität.

---

## 8. Zusammenfassung in einem Satz

> **Das Modell schreibt den Inhalt und setzt Marker; deterministischer Code
> entscheidet über das Verhalten** – beim Canvas zusätzlich abgesichert durch einen
> Intent-Guard, beim Urlaubsantrag komplett vom Modell entkoppelt für maximale
> Demo-Verlässlichkeit.
