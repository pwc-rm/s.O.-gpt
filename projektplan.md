# S.Oliver GPT – High-Level Projektplan (MVP)

> **Format bewusst grob** (Wunsch aus dem Call: Milestones / Big Buckets, keine atomaren Tasks, 75%-Version).
> Ziel: Vertikaler Durchstich – Chat-UI → Backend → Retrieval (Azure AI Search) → Antwort (AI Foundry), gefüttert aus einer PDF-Ingestion-Pipeline. Demo für den Pitch.

## Leitplanken

- **Geschwindigkeit vor Schönheit** – aber Frontend „nice & shiny" und die Urlaubs-Frage **muss** sitzen.
- Azure-Komponenten nutzen, wo sinnvoll; nicht komplett lokal abkürzen.
- 1 User → Session-Handling einfach (Cosmos DB, austauschbar gehalten).
- Deployment via Resource Group „Playground" (Arno legt an).

## Rollen

- **Raj** – Entwicklung (Lead): App/Backend/Frontend, Ingestion- & Retrieval-Implementierung.
- **Mike** – Testing (Softwaretests) + Unterstützung der Entwicklung (Code Review, Terraform schreiben/Infra-Deployment).

> **Stand: Do 25.06.2026.** Zieltermin Demo (pitch-fertig): **Fr 03.07.2026** (Ende nächster Woche).

## Timeline auf einen Blick

| Milestone    | Inhalt                        | Zieltermin          | in Tagen* |
| ------------ | ----------------------------- | ------------------- | --------- |
| **M0** | Setup, Zugriff & Infra        | **Fr 26.06.** | +1        |
| **M1** | Ingestion Pipeline            | **Mo 29.06.** | +4        |
| **M2** | Retrieval & Generation (Core) | **Mi 01.07.** | +6        |
| **M3** | Frontend & Session            | **Do 02.07.** | +7        |
| **M4** | Politur & Demo-Härtung       | **Fr 03.07.** | +8        |

\*Kalendertage ab heute (25.06.), inkl. Wochenende. M2 und M3 laufen teils **parallel** (Backend/Ingestion ↔ Frontend).

---

## Milestones

### M0 – Setup, Zugriff & Infra  ·  **Zieltermin: Fr 26.06.** *(+1 Tag)*

- ✅ **Resource Group „Playground" verfügbar – Zugriff steht (dank Arno, 25.06.).**
- Repo + Terraform-Grundgerüst, Azure-Ressourcen provisionierbar.
- **Done = `terraform apply` deployt eine leere, lauffähige Infrastruktur.**

### M1 – Ingestion Pipeline  ·  **Zieltermin: Mo 29.06.** *(+4 Tage)*

- PDF → Markdown (Library/LLM statt Document Intelligence) inkl. Tabellen.
- Chunking + Embeddings + Indizierung in Azure AI Search inkl. Metadaten.
- HR-/IT-/Code-of-Conduct-Dokumente hochgeladen.
- **Done = Dokumente sind durchsuchbar im AI Search Index.**

### M2 – Retrieval & Generation (Core)  ·  **Zieltermin: Mi 01.07.** *(+6 Tage)*

- Backend-REST-API: Orchestrator, Query Rewriting, Prompt-Bau.
- Hybride Suche (Vector + BM25) → Semantic Reranking.
- Anbindung Azure AI Foundry → quellenbasierte Antwort mit Quellenangabe.
- **Done = API beantwortet die Urlaubs-Frage korrekt mit Quelle (Postman/curl).**

### M3 – Frontend & Session  ·  **Zieltermin: Do 02.07.** *(+7 Tage, teils parallel zu M2)*

- Chat-UI (nice & shiny) mit Multiturn / Session-Management.
- Session Store (Cosmos DB), Session-Reranking (Boost genutzter Dokumente).
- AI Gateway davor.
- **Done = klickbare Chat-Demo end-to-end im Browser.**

### M4 – Politur & Demo-Härtung  ·  **Zieltermin: Fr 03.07.** *(+8 Tage)*

- Antwortqualität für die Kernfragen absichern (Notfall: Urlaubs-Antwort hart hinterlegen).
- UI-Feinschliff, kleine Bugs, Demo-Skript.
- **Done = pitch-fertige Demo.**

---

## Realismus-Check

M0 (Azure-Zugriff) **steht bereits** → kritischer Pfad ist die **Ingestion-Pipeline (M1)**. Die Demo bis **Fr 03.07.** ist machbar, solange M1 bis **Mo 29.06.** steht. Puffer ist knapp (heute schon Do) → M2/M3 bewusst **parallelisieren** (Mike: Backend/Ingestion, Raj: Frontend). Wenn M1 rutscht, rutscht alles → das ist der Punkt, den wir Freitag im Touchpoint ehrlich bewerten.

## Offene Punkte

- PDF-to-Markdown-Library evaluieren (Mike) → blockiert M1, daher **vor/am 26.06.** klären.
- AI Gateway in AI Foundry verfügbar? (Franks Hypothese bestätigen) → relevant für M3.
- Touchpoints: **Fr 26.06. früh**, danach erneut Mitte nächster Woche.
