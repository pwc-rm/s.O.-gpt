# s.Oliver Agent Cockpit — Screen-Analyse & Verständnis

> Quelle: Stitch-Export in `docs/cockpit-stitch-screens/` (7 Screens).
> Ziel dieses Dokuments: belegen, dass die Logik **jeder** Seite verstanden ist —
> was sie fachlich tut, womit sie verbunden ist, welches Datenmodell dahinter
> steht und welche **Änderungen** ich vor dem Bauen vorschlage.

---

## 0. Was ist das „Agent Cockpit" überhaupt?

Der Stitch-Entwurf heißt intern **„sO Agent Cockpit — Governance & Marketplace"**.
Es ist **nicht** nur eine Verwaltungsansicht für den einen s.O GPT, sondern eine
**AI-Control-Tower-Ebene** über *mehreren* KI-Agenten — konzeptionell genau die
Rolle, die in `docs/junk/so-gpt-architecture-for-cockpit.txt` beschrieben ist:

- **s.O GPT** = *Execution Engine* (führt RAG-Chat aus).
- **Agent Cockpit** = *Governance-/Katalog-Autorität* (welche Agenten existieren,
  wem sie gehören, was sie kosten, wie gesund sie sind, wer sie nutzen darf).

Das deckt sich 1:1 mit der ServiceNow-AI-Control-Tower-Analogie aus der
Architektur-Doku (Business Owner, Application Container, Configuration Item,
ServiceNow-Link sind sogar als Felder im Agent-Detail vorhanden).

### Design-System (aus `DESIGN.md`, identisch über alle Screens)
- **s.Oliver-Rot** `#d92b3a` (primary-container) / `#b50625` (primary) als Aktionsfarbe.
- **Zinc-900 Sidebar** `#18181b`, weißer/heller Content (`#f8f9fa`).
- **Inter**-Font, flaches „Corporate Modern"-Design, 260px feste Sidebar.
- Semantik: `success-green #10b981`, `warning-amber #f59e0b`, `error #ba1a1a`.
- ⚠️ Unterschied zum **Live-s.O-GPT**: dessen Sidebar ist `#212121`, nutzt
  **Phosphor-Icons**; das Cockpit nutzt **Material Symbols** und Zinc-900.
  → Beim Angleichen des Buttons darauf achten (siehe Screen 00).

---

## 1. Screen-Landkarte & Navigationsfluss

Die Stitch-Exporte referenzieren sich über `{{DATA:SCREEN:SCREEN_x}}`-Platzhalter
(Stitch-intern, **inkonsistent** zwischen den Dateien — nicht als echte Routen
verwenden). Der *logische* Fluss ist aber eindeutig:

```
        ┌─────────────────────────────┐
        │  00 s.O GPT Chat (bestehend)│
        │  [Button: „Zum Agent Cockpit"]──────┐   ← EINZIGE Änderung am s.O GPT
        └─────────────────────────────┘        │
                                                ▼
        ┌───────────────────────────────────────────────────┐
        │  01 Cockpit — Marktplatz (Hub)                     │
        │  Sidebar: Marktplatz · FinOps · AgentOps · Einst.  │
        │  [Zurück zu s.O GPT] ──────────────────────────────┼──► 00
        └───────┬───────────────┬───────────────┬───────────┘
                │ „Verwalten"   │ „Agent starten"│  Sidebar-Nav
                ▼               ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────┐
        │02 Agent-Detail│ │06 Agent-Chat │ │03 FinOps · 04 AgentOps  │
        │(Tabs)         │ │(agent-scoped)│ │05 Einstellungen         │
        └──────────────┘ └──────────────┘ └─────────────────────────┘
```

---

## 2. Screen-für-Screen

### 00 · `00-sogpt-chat-entry` — s.O GPT (bestehend, mit neuem Button)
**Was es tut:** Stitchs Re-Skin des bestehenden s.O-GPT-Chats (Welcome-State,
Recent-Chats-Sidebar, Vorschlags-Chips, Eingabefeld). Oben rechts der **neue,
s.Oliver-rote Button „Zum Agent Cockpit"** (Rocket-Icon) + Badge „Output basiert
auf Mock-Daten".

**Verbindung:** Button → Cockpit (01). Das ist die *einzige* Änderung, die laut
Auftrag am s.O GPT vorgenommen wird.

**Datenmodell:** keins neu — nutzt die bestehende s.O-GPT-Chat-/Session-Logik.

> **⚠️ Wichtiger Vorschlag:** Wir übernehmen **NICHT** Stitchs kompletten Re-Skin
> in die Live-`static/index.html`. Stitch nutzt anderes Icon-Set (Material statt
> Phosphor) und eine andere Sidebar-Farbe — ein Voll-Austausch wäre eine große
> Regression auf Rajs App. **Wir fügen nur den Button** oben rechts ein
> (Phosphor-Icon, `#d92b3a`), verlinkt auf die Cockpit-URL. Minimal-invasiv.

---

### 01 · `01-cockpit-marketplace` — Marktplatz (Hub)
**Was es tut:** Einstiegsseite des Cockpits. Ein **Agenten-Marktplatz**: Karten,
gruppiert nach Abteilung (*HR & People*, *IT & Infrastructure*, *Sales &
Marketing*). Jede Karte zeigt: Icon, Kategorie, **Status** (Aktiv/Inaktiv),
**Business Owner**, **Org-Zuordnung**, Modell-Badge, Beschreibung und die Aktionen
**„Agent starten"** + **„Verwalten"**. Kopf: Suche („Search for Agents…", Cmd+K),
„Auto-Discovery: Active"-Indikator, Kategorie-Filter.

Technisch ist die Datei eine **Mini-SPA**: sie enthält per `switchView()` auch die
Views FinOps/AgentOps/Einstellungen inline (vereinfachte Duplikate von 03/04/05).
→ Für die echte App nehmen wir die **eigenständigen** Screens 03/04/05 als Wahrheit
und bauen 01 als reine Marktplatz-Seite.

**Verbindung:** „Verwalten" → 02 (Detail). „Agent starten" → 06 bzw. **echter s.O
GPT** (siehe Vorschlag unten). Sidebar → 03/04/05. „Zurück zu s.O GPT" → 00.

**Datenmodell — `agent` (Kern des Katalogs):**
```jsonc
{
  "id": "hr-vacation-assistant",
  "doc_type": "agent",
  "name": "HR Urlaubsassistent",
  "description": "Automatisiert die Beantragung …",
  "category": "HR & People",          // HR | IT | Sales | Marketing | …
  "status": "active",                  // active | inactive
  "business_owner": "Sarah Müller",
  "org_unit": "HR Dept",
  "model": "gpt-4o",
  "icon": "event_available"
}
```

> **Vorschläge:**
> - **„Agent starten" muss in den echten s.O GPT deep-linken:**
>   `https://<sogpt-url>/?agent_id=hr-vacation-assistant` — exakt der Handoff aus
>   der Architektur-Doku (Abschnitt 4A). So bleibt der Katalog die Autorität und
>   der s.O GPT die Engine. (Siehe auch Screen 06.)
> - Status (Aktiv/Inaktiv) und Modell-Badge sollten aus dem Katalog kommen, nicht
>   hardcodiert. „Deine Gruppe"-Tag = Ableitung aus der AD-Gruppe des Nutzers
>   (POC: statisch).
> - Kleiner HTML-Bug in der HR-Gruppe (die 2. Karte liegt außerhalb des Grids) —
>   beim Nachbau bereinigen.

---

### 02 · `02-agent-detail` — Agent verwalten (Tabs)
**Was es tut:** Governance-/Konfigurations-Detail **eines** Agenten (Beispiel „HR
Vacation Assistant"). Vier Tabs:

1. **Konfiguration** — Name, Kurzbeschreibung, **System Prompt**, Business Owner,
   **Application Container**, **Configuration Item (CI)**, **ServiceNow-Link**
   (CMDB!), Basis-Modell (GPT-4o/GPT-4 Turbo/Claude 3.5/Mistral), **Temperature**.
2. **Berechtigungen** — Zugriffstabelle: Entität (AD-Gruppe/Einzelnutzer), Typ,
   Rolle (Nutzer/Admin-Owner). „Gruppe/Nutzer hinzufügen".
3. **Wissensdatenbank** — verknüpfte Dokumente (PDF/DOCX, Upload/URL, Status
   „Indexed") + **Retrieval-Settings**: Chunk-Size (disabled=1024), **Top-K** (5),
   **Strict Mode** („nur Antworten aus Doks").
4. **Analytics** — Token-Usage (30 T.), Ø Antwortzeit, Nutzerzufriedenheit
   (Sterne), Chart-Placeholder.

**Das ist der eigentliche Governance-Kern:** Genau hier wird das, was im s.O GPT
heute **hartcodiert** ist (`_SYSTEM_PROMPT`, `TOP_N_CHUNKS`, Strict-Mode), zu
**editierbarer, pro-Agent-Konfiguration**.

**Verbindung:** aus 01 „Verwalten". Schreibt in den `agent`-Datensatz. Die
Retrieval-Settings + System-Prompt werden zur Laufzeit vom s.O GPT konsumiert
(via `agent_id`).

**Datenmodell — Erweiterung von `agent`:**
```jsonc
{
  // … Kernfelder von oben …
  "system_prompt": "Du bist ein hilfsbereiter HR-Assistent …",
  "temperature": 0.2,
  "cmdb": {
    "application_container": "HR-Services-Prod",
    "configuration_item": "CI-992834",
    "servicenow_link": "https://service-now.com/…"
  },
  "permissions": [
    { "entity": "All_Employees", "type": "ad_group", "role": "user" },
    { "entity": "Sarah Müller", "type": "user", "role": "owner" }
  ],
  "knowledge": {
    "documents": [
      { "name": "Betriebsvereinbarung_Urlaub_2024.pdf", "size": "1.2 MB",
        "uploaded_at": "2024-05-12", "status": "indexed" }
    ],
    "retrieval": { "chunk_size": 1024, "top_k": 5, "strict_mode": true }
  }
}
```

> **Vorschläge:**
> - **System-Prompt & Retrieval-Settings sind der echte Mehrwert** → im POC in den
>   Katalog schreiben; s.O-GPT-`prompt_builder.py`/`retrieval.py` liest sie per
>   `agent_id` statt der hartcodierten Konstanten. (Kleine, klar umrissene Änderung
>   laut Architektur-Doku 4B.)
> - **Modell-Dropdown ehrlich halten:** s.O GPT spricht heute nur Azure OpenAI
>   (gpt-4o) an. Claude/Mistral sind nicht verdrahtet → im POC entweder ausgrauen
>   oder klar als „geplant" markieren, damit die Demo nichts verspricht, was der
>   Backend nicht kann.
> - CMDB-Felder (Container/CI/ServiceNow) im POC als **reine Strings** speichern
>   (keine echte ServiceNow-Integration nötig) — sie zeigen aber die Governance-Story.
> - Dokument-Upload: im POC Metadaten mocken. Echte Indexierung liefe über die
>   bestehende Ingestion-Function des s.O GPT (Blob-Trigger).

---

### 03 · `03-finops` — FinOps & Kostenkontrolle
**Was es tut:** Kosten-Dashboard über **alle** Agenten. KPIs: Gesamtbudget/Monat
(€12.450, −4,2 %), verbrauchte Token (45,2 M, +12,5 %), Ø Kosten/Anfrage (€0,012).
Kostenverlauf-Chart (30 T.). Tabelle **„Kosten pro Agent"**: Owner, **Verbrauch/
Kontingent** (Progress-Bar), Total Cost, Status (OK/Warning).

**Verbindung:** Sidebar-Nav. Aggregiert Nutzungs-/Kostendaten pro Agent.

**Datenmodell — `finops`/abgeleitet:**
```jsonc
{ "agent_id": "…", "period": "2026-07", "tokens_used": 12500000,
  "quota": 20000000, "cost_eur": 3240, "status": "ok" }  // ok | warning
```

> **Vorschläge (starker POC-Hebel):**
> - **Echte Zahlen sind teilweise schon da!** Der s.O GPT persistiert laut
>   Architektur-Doku (Abschnitt 5) **Token-Usage pro Chat-Turn** im Cosmos-
>   `sessions`-Container. → FinOps kann echte Token pro Agent **aggregieren**
>   (Kosten = Token × Preis/1k). Das macht die Demo glaubwürdig statt rein mock.
> - Budget/Kontingent pro Agent = Config im Katalog (`agent.finops.quota`).
> - Chart-Placeholder durch **inline-SVG/kleine JS-Sparkline** ersetzen (keine
>   externen CDNs im Prod nötig).

---

### 04 · `04-agentops` — AgentOps & Performance
**Was es tut:** Betriebs-/Qualitäts-Dashboard. KPIs: Ø Latenz (840 ms), Adoption
Rate (68 %), QA-Score (94,2), User-Feedback (4,8★). **Alerts & Exceptions**
(API-Timeout, hohe Latenz). Tabelle **„Agenten Performance"**: Status
(Active/Degraded), Calls (24 h), Ø Latenz.

**Verbindung:** Sidebar-Nav. Betriebsmetriken pro Agent.

**Datenmodell — `agentops`/abgeleitet:**
```jsonc
{ "agent_id": "…", "status": "active", "calls_24h": 12450,
  "avg_latency_ms": 450, "qa_score": 94.2, "adoption_rate": 0.68,
  "feedback_avg": 4.8, "alerts": [ { "level": "error", "msg": "API Timeout …",
  "ts": "…" } ] }
```

> **Vorschläge:**
> - **Latenz ist heute nicht erfasst.** Kleiner Zusatz im s.O-GPT-`/chat`:
>   Zeit bis First-Token + Gesamtdauer messen und auf dem Turn-Doc persistieren →
>   dann ist „Ø Latenz" und „Calls (24h)" echt.
> - **QA-Score/Adoption** brauchen eine Eval-/Nutzer-Basis → im POC **mocken** und
>   ehrlich als „simuliert" labeln.
> - Alerts im POC statisch; später aus Latenz-/Fehler-Schwellwerten generieren.

---

### 05 · `05-settings` — Einstellungen (global)
**Was es tut:** Globale Cockpit-Einstellungen mit Sticky-Sub-Nav:
- **Benutzerprofil** (Vor-/Nachname, E-Mail — disabled, kommt aus IdP).
- **API & Governance** — Tabelle mit API-Schlüsseln (Name, erstellt, Status),
  „Neuer Schlüssel anfragen".
- **Organisation** — Abteilungen + Mitgliederzahl, „Bearbeiten".
- **Benachrichtigungen** — Toggles (E-Mail, Browser-Push, kritische Alerts).

**Verbindung:** Sidebar-Nav. Cockpit-weite Config.

**Datenmodell — `settings`/`apikey`/`org_unit`:**
```jsonc
{ "doc_type": "apikey", "name": "Marketing Agent Prod",
  "created_at": "2023-10-12", "status": "active" }
{ "doc_type": "org_unit", "name": "Marketing", "members": 12 }
```

> **Vorschläge:**
> - **API-Schlüssel = APIM-Subscription-Keys.** Die Architektur-Doku nennt
>   „Key-/Subscription-Management in APIM" als offenes To-do — genau das ist diese
>   Seite. POC: mocken; echt: APIM-Subscriptions-API.
> - **Benutzerprofil/E-Mail = Entra ID.** Heute hat der s.O GPT **keine** Identität
>   (Architektur-Doku 3). Diese Seite ist der natürliche Ort, um später Entra-SSO
>   anzudocken. POC: statischer „Max Mustermann".
> - E-Mail-Feld ist bewusst `disabled` → korrekt (kommt aus dem IdP, nicht editierbar).

---

### 06 · `06-agent-chat` — Agent-spezifischer Chat
**Was es tut:** Der eigentliche Chat **mit einem gewählten Agenten** (Beispiel „HR
Vacation Assistant"): Agenten-Identität (Icon, Name, Claim), **agenten-spezifische**
Vorschlags-Prompts, Eingabefeld, „Zum Agent Cockpit"-Backlink. Cockpit-gestyled.

**Verbindung:** aus 01 „Agent starten".

> **✅ Entschieden (Mike, 2026-07-21):**
> Die Agent-Chats laufen **im Cockpit-App**, aber im **s.O-GPT-Chat-Design** (die
> vertraute Optik — Phosphor-Icons, Sidebar `#212121` —, NICHT Stitchs rote
> Cockpit-Variante von Screen 06). Jeder Agent hat **eigenen Namen + reservierte,
> pro-`agent_id` getrennte, ECHTE Chat-Historie**. Antworten sind **echt** (Azure
> OpenAI gpt-4o mit dem agenten-eigenen System-Prompt), Streaming wie s.O GPT.
> → Damit bleibt der **echte s.O GPT komplett unberührt** (bekommt nur den Button);
> es gibt **kein** `?agent_id`-Handoff und **keinen** Umbau an dessen Chat-Logik.
> Screen 06 (Stitch-Version) wird also **nicht** übernommen — stattdessen wird das
> reale s.O-GPT-Chat-Frontend als Vorlage in das Cockpit kopiert und pro Agent
> parametrisiert.

---

## 3. Konsolidiertes Datenmodell (Agent-Katalog)

Ein neuer, **vom s.O GPT getrennter** Cosmos-Container `agents` (Governance-Grenze,
Architektur-Doku 5). Ein `agent`-Dokument ist die Wahrheit; FinOps/AgentOps werden
zur Laufzeit aus dem `sessions`-Container des s.O GPT aggregiert (Token/Latenz) und
mit Katalog-Config (Quota) angereichert.

| doc_type | Zweck | Quelle im POC |
|---|---|---|
| `agent` | Katalog-Eintrag (Config, Prompt, Permissions, Knowledge) | Mock-Seed in Cosmos |
| `apikey` | APIM-Subscription (Settings) | Mock-Seed |
| `org_unit` | Abteilung + Mitglieder | Mock-Seed |
| *(abgeleitet)* `finops` | Kosten/Token pro Agent | aggregiert aus s.O-GPT-`sessions` (+ Mock) |
| *(abgeleitet)* `agentops` | Latenz/Calls/QA pro Agent | teils echt (Latenz-Zusatz), teils Mock |

---

## 4. Verbindung zum bestehenden s.O GPT — die drei Berührungspunkte

1. **Button** im s.O GPT (oben rechts) → Cockpit-URL. *(einzige UI-Änderung am GPT)*
2. **Deep-Link zurück:** „Agent starten" im Cockpit → `s.O GPT /?agent_id=…`.
   Erfordert im s.O GPT: `agent_id` in `ChatRequest`, Katalog-Lookup, `system_prompt`
   + Retrieval-Settings aus dem Katalog statt hartcodiert (Architektur-Doku 4B).
3. **Daten-Read:** FinOps/AgentOps lesen Token/Latenz aus dem s.O-GPT-`sessions`-
   Container (read-only) — kein Schreibzugriff auf die Chat-Daten.

> Punkt 2/3 sind für den **reinen Anschau-POC** optional: Das Cockpit läuft mit
> Mock-Katalog eigenständig. Aber diese drei Punkte sind der Pfad zu „echt".

---

## 5. Zusammenfassung der Änderungsvorschläge (vor dem Bauen)

| # | Screen | Vorschlag | Warum |
|---|---|---|---|
| A | 00 | Nur **Button** ins Live-`index.html`, kein Voll-Reskin | Regressionsrisiko auf Rajs App vermeiden |
| B | 01 | „Agent starten" → **s.O-GPT-Deep-Link `?agent_id`** | Katalog=Autorität, GPT=Engine |
| C | 01 | Status/Modell/Owner aus Katalog, HTML-Grid-Bug fixen | Datengetrieben statt hardcodiert |
| D | 02 | System-Prompt + Retrieval-Settings **in Katalog schreiben**, GPT liest sie | Der eigentliche Governance-Mehrwert |
| E | 02 | Modell-Dropdown auf real Verfügbares beschränken/labeln | Demo verspricht nichts Falsches |
| F | 03 | FinOps = **reine Mock-Daten** (keine Aggregation) | Entscheidung Mike: POC bleibt Mock |
| G | 04 | AgentOps = **reine Mock-Daten**; kein `/chat`-Umbau am s.O GPT | Entscheidung Mike: POC bleibt Mock |
| H | 06 | Agent-Chat **im Cockpit**, im s.O-GPT-Design, **echter LLM-Chat** + echte Historie, pro `agent_id` reserviert | s.O GPT unberührt, vertraute Optik, glaubwürdige Demo |
| I | 05 | API-Keys ↔ APIM-Subscriptions, Profil ↔ Entra (POC: Mock) | Anschluss an offene Architektur-To-dos |

Details zur technischen Umsetzung & zum Deployment: siehe
[`01-architektur-und-plan.md`](01-architektur-und-plan.md).
