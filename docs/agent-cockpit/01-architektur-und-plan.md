# s.Oliver Agent Cockpit — Architektur & Deployment-Plan

> Begleitdokument zu [`00-analyse-screens.md`](00-analyse-screens.md).
> Beschreibt **wie** wir die 7 analysierten Screens als eigenständige App bauen und
> deployen — inkl. Terraform, damit ein Deploy reproduzierbar/„one command" ist.

---

## 1. Zielbild in einem Satz

Eine **eigenständige FastAPI-App „s.Oliver Agent Cockpit"** in **derselben Azure-
Sandbox** wie der s.O GPT, mit **eigener URL**, die einen Mock-**Agent-Katalog**
(Cosmos) verwaltet — plus **ein Button** im s.O GPT, der dorthin führt. Kein Umbau
an Rajs Live-App.

---

## 2. Architektur-Überblick

```
                 ┌──────────────────────── RG-PLAYGROUND (bestehende Sandbox) ───────────────────────┐
                 │                                                                                    │
  Browser ──────►│  app-so-gpt-showcase-backend        app-agent-cockpit  (NEU)                       │
                 │  (Rajs Live-App, UNBERÜHRT)          FastAPI + statisches Cockpit-Frontend          │
                 │        ▲                                   │        │                                │
                 │        │ Button „Zum Cockpit"              │        │                                │
                 │        └───────── nur auf Test-App ────────┘        │                                │
                 │  app-so-gpt-showcase-backend-test                   │                                │
                 │  (isolierte Test-Instanz — hier kommt der Button)   │                                │
                 │                                                     ▼                                │
                 │   ACR sogptshowcase        Cosmos cosmos-so-gpt-showcase        kv-so-gpt-showcase   │
                 │   image: agent-cockpit:*   ├─ so-gpt-db/sessions ← Rajs Live-App + s.O-GPT-Test      │
                 │                            │                        (geteilt — bewusst ok)           │
                 │                            └─ agent-cockpit-db (NEU) ← NUR das Cockpit, abgeschottet  │
                 │                               ├─ agents     (Agent-Katalog)                          │
                 │                               └─ agent_chat (reservierte Agent-Chats, Mock)          │
                 └────────────────────────────────────────────────────────────────────────────────────┘
```

**Prinzipien** (aus Deploy-Runbook + Architektur-Doku):
- **Rajs Compute unberührt:** eigener App-Service-Plan/App, eigener Image-Tag
  (`agent-cockpit:*`, niemals Rajs `v*`-Tags). Rajs Live-App läuft auf `v26`.
- **Cockpit-Daten getrennt (Entscheidung Mike):** das **Cockpit** bekommt eine
  **eigene DB `agent-cockpit-db`** (Katalog + Agent-Chats). Der s.O-GPT-Test darf
  weiter in `so-gpt-db/sessions` schreiben (mit Raj geteilt — bewusst ok). Getrennt
  wird also *der Cockpit-Teil*, nicht die s.O-GPT-Chats.
- **s.O GPT unverändert:** keine Config-/DB-Änderung am s.O-GPT-Test außer dem
  Button. Der KV-Secret `cosmos-connection-string` (auch von Raj gelesen) bleibt
  unangetastet.
- **Geteilt:** Cosmos-*Account*, KV, ACR, Compute-Plan (kein Fixkosten-Overhead);
  das **Cockpit** nutzt darin seine **eigene DB**.
- **Secrets** zur Laufzeit via `AZURE_KEYVAULT_URL` + System-Managed-Identity
  (genau wie `config.py` es heute macht) — keine KV-References nötig.
- **`httpsOnly = true`** ist Pflicht (PwC-Policy `az-006` blockt sonst die Erstellung).

---

## 3. Anwendungs-Struktur (neues Verzeichnis)

Spiegelt `so-gpt-backend/`, damit Deploy-/Build-Muster identisch sind:

```
agent-cockpit-backend/
├── Dockerfile                 # identisch zu so-gpt-backend (uvicorn, Port 8000)
├── requirements.txt           # fastapi, uvicorn, azure-cosmos, azure-identity, azure-keyvault-secrets
├── main.py                    # FastAPI: statisches Frontend @ "/" + REST-API
├── config.py                  # KV/Cosmos-Config (aus so-gpt-backend übernommen, gekürzt)
├── catalog_store.py           # CRUD gegen Cosmos-Container „agents" (+ Seed) — Mock
├── mock_seed.py               # Seed: 5 Demo-Agenten, FinOps-/AgentOps-Mockwerte, Chat-Verläufe
└── static/
    ├── index.html             # Cockpit-SPA (Shell + Marktplatz + FinOps + AgentOps + Settings + Detail)
    ├── agent-chat.html        # Agent-Chat im s.O-GPT-Design (aus so-gpt static/ übernommen, pro Agent)
    └── assets/…               # aus Stitch-Export abgeleitetes CSS/JS (Material Symbols inline)
```

### REST-API (Cockpit-Backend)
| Methode | Route | Zweck | Screen |
|---|---|---|---|
| GET | `/api/agents` | Katalog (Filter: category, status) | 01 |
| GET | `/api/agents/{id}` | ein Agent inkl. Config/Permissions/Knowledge | 02 |
| PUT | `/api/agents/{id}` | Agent speichern (Prompt, Retrieval, CMDB …) | 02 |
| GET | `/api/finops` | KPIs + Kosten-pro-Agent (aggregiert) | 03 |
| GET | `/api/agentops` | KPIs + Alerts + Performance-Tabelle | 04 |
| GET | `/api/settings` | Profil, API-Keys, Orgs, Notifications | 05 |
| GET | `/health` | Service-Status (wie s.O GPT) | — |

| GET | `/agent/{id}/chat` | Agent-Chat-UI im s.O-GPT-Design (reservierte Historie) | 06 |
| POST | `/api/agents/{id}/chat` | Nachricht senden → **echte** SSE-LLM-Antwort, Historie persistiert | 06 |
| GET | `/api/agents/{id}/history` | reservierte Chat-Verläufe dieses Agenten | 06 |

> „Agent starten" öffnet die **Cockpit-interne** Chat-Seite `/agent/{id}/chat`
> (s.O-GPT-Design, Mock). **Kein** Deep-Link in den echten s.O GPT — der bleibt
> unberührt und bekommt nur den Button hierher.

---

## 4. Datenmodell in Cosmos (Container `agents`)

- **Datenbank:** `agent-cockpit-db` (NEU, getrennt von Rajs `so-gpt-db`).
- **Container:** `agents`, **Partition Key `/category`** (globaler, low-write,
  high-read Katalog — nicht session-scoped).
- Ein Doc pro Agent (`doc_type: "agent"`), plus `apikey`/`org_unit`-Docs für Settings.
- Vollständige Feldliste: siehe [`00-analyse-screens.md` §3](00-analyse-screens.md).

**FinOps/AgentOps = reine Mock-Daten** (Entscheidung Mike, POC). Keine Aggregation
aus dem echten `sessions`-Container, kein `/chat`-Umbau am s.O GPT. Die Zahlen der
Screens (Budget, Token, Latenz, QA …) kommen aus `mock_seed.py` und werden im UI
klar als Demo-/Mock-Werte gekennzeichnet.

**Agent-Chats** (im Cockpit, s.O-GPT-Design): **echter LLM-Chat** — Azure OpenAI
(gpt-4o, gleicher KV-Endpoint wie s.O GPT), pro Agent eigener **System-Prompt**
(aus dem Katalog, im Detail editierbar) + **echte, reservierte Historie**
(Container `agent_chat`, PK `/agent_id` — HR-Verläufe nie beim IT-Agent). SSE-
Streaming wie s.O GPT.
```jsonc
{ "doc_type": "agent_chat", "agent_id": "hr-vacation-assistant",
  "chat_id": "…", "title": "Urlaubsantrag Q3",
  "messages": [ { "role": "user", "content": "…" },
                { "role": "assistant", "content": "…", "tokens": 142 } ] }
```
> Grounding: **Variante A** = nur System-Prompt-Scope (schlank). **Variante B**
> (optional) = zusätzlich RAG pro Agent via Azure AI Search; HR-Agent kann den
> bestehenden s.O-GPT-Index wiederverwenden.

---

## 5. Terraform — reproduzierbares Deployment

**Entscheidung:** eigener, **additiver** TF-Root unter `infra/cockpit/`, der die
bestehenden Ressourcen als **data sources** referenziert (RG, Cosmos, KV, ACR) und
nur das **Neue** anlegt (Cosmos-Container `agents`, Plan, Web App, RBAC). So kann
`terraform apply` in `infra/cockpit/` laufen, **ohne** Rajs `infra/main.tf`-State
anzufassen.

> Warum eigener Root und nicht Rajs `main.tf` erweitern? Rajs `main.tf` beschreibt
> teils den *Soll*-Zustand (Python-Stack), die **Realität ist ein Container** (siehe
> Deploy-Runbook). Ein separater Root hält uns aus diesem Drift heraus und lässt sich
> unabhängig zerstören.

### `infra/cockpit/main.tf` (Kern — gekürzt)
```hcl
terraform {
  required_providers { azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" } }
}
provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
}

# ── Bestehendes referenzieren (nicht anlegen) ────────────────────────────────
data "azurerm_resource_group"   "rg"     { name = var.resource_group_name }        # RG-PLAYGROUND
data "azurerm_cosmosdb_account"  "cosmos" { name = var.cosmos_account_name
                                            resource_group_name = var.resource_group_name }
data "azurerm_key_vault"         "kv"     { name = var.key_vault_name
                                            resource_group_name = var.resource_group_name }
data "azurerm_container_registry" "acr"   { name = var.acr_name
                                            resource_group_name = var.resource_group_name }

# ── NEU: eigene Cockpit-Datenbank (getrennt von Rajs so-gpt-db) ──────────────
resource "azurerm_cosmosdb_sql_database" "cockpit" {
  name                = "agent-cockpit-db"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.cosmos.name
}
resource "azurerm_cosmosdb_sql_container" "agents" {
  name                = "agents"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.cockpit.name
  partition_key_paths = ["/category"]
}
resource "azurerm_cosmosdb_sql_container" "agent_chat" {
  name                = "agent_chat"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.cockpit.name
  partition_key_paths = ["/agent_id"]                   # Chats pro Agent reserviert
}

# ── Bestehenden App-Service-Plan referenzieren (geteilt, Entscheidung Mike) ──
# Cockpit teilt sich den Compute-Plan der s.O-GPT-Test-Instanz; nur App + Daten
# (eigene Web App, eigener Cosmos-Container) sind getrennt.
data "azurerm_service_plan" "shared" {
  name                = var.app_service_plan_name        # plan-so-gpt-showcase-test
  resource_group_name = var.resource_group_name
}

# ── NEU: Cockpit Web App (Container aus ACR, eigene App/URL) ──────────────────
resource "azurerm_linux_web_app" "cockpit" {
  name                = "app-agent-cockpit"
  resource_group_name = var.resource_group_name
  location            = data.azurerm_resource_group.rg.location
  service_plan_id     = data.azurerm_service_plan.shared.id
  https_only          = true                              # PwC-Policy az-006 (Pflicht)

  identity { type = "SystemAssigned" }

  site_config {
    application_stack {
      docker_image_name   = "agent-cockpit:${var.image_tag}"
      docker_registry_url = "https://${data.azurerm_container_registry.acr.login_server}"
    }
    container_registry_use_managed_identity = true
  }

  app_settings = {
    AZURE_KEYVAULT_URL      = data.azurerm_key_vault.kv.vault_uri  # config.py lädt Secrets darüber
    WEBSITES_PORT           = "8000"
    COSMOS_DATABASE         = azurerm_cosmosdb_sql_database.cockpit.name  # agent-cockpit-db (eigene DB)
    COSMOS_AGENTS_CONTAINER    = "agents"
    COSMOS_AGENTCHAT_CONTAINER = "agent_chat"
    SOGPT_URL               = var.sogpt_url                        # für den „Zurück zu s.O GPT"-Link
  }
}

# ── RBAC für die Managed Identity (wie Runbook) ──────────────────────────────
resource "azurerm_role_assignment" "acr_pull" {
  scope                = data.azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.cockpit.identity[0].principal_id
}
resource "azurerm_role_assignment" "kv_reader" {
  scope                = data.azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.cockpit.identity[0].principal_id
}

output "cockpit_url" { value = "https://${azurerm_linux_web_app.cockpit.default_hostname}" }
```

### `infra/cockpit/variables.tf` (Werte aus der Sandbox)
```hcl
variable "subscription_id"     { default = "4155cf68-c489-4a41-be81-ef83a86f8a28" } # PZI-DE-E-SUB001 (verifiziert)
variable "resource_group_name" { default = "RG-PLAYGROUND" }
variable "cosmos_account_name" { default = "cosmos-so-gpt-showcase" }
variable "cosmos_database"     { default = "so-gpt-db" }
variable "key_vault_name"      { default = "kv-so-gpt-showcase" }
variable "acr_name"            { default = "sogptshowcase" }
variable "app_service_plan_name" { default = "plan-so-gpt-showcase-test" } # geteilt mit s.O-GPT-Test
variable "image_tag"           { default = "poc" }
variable "sogpt_url"           { default = "https://app-so-gpt-showcase-backend-test.azurewebsites.net" }
```
> ⚠️ `subscription_id` in der Runbook-Notiz vs. hier bitte gegenprüfen (Tippfehler-Risiko).

### Deploy-Ablauf (zwei Kommandos)
```bash
# 1) Image in Rajs ACR bauen (Cloud-Build, kein lokales Docker) — eigener Tag:
cd agent-cockpit-backend && az acr build --registry sogptshowcase --image agent-cockpit:poc .

# 2) Infra anlegen/aktualisieren:
cd ../infra/cockpit && terraform init && terraform apply
#    → Output: cockpit_url = https://app-agent-cockpit.azurewebsites.net
```
Redeploy nach Code-Fix: Schritt 1 erneut + `az webapp restart -g RG-PLAYGROUND -n app-agent-cockpit`.

> **Schneller Alternativpfad (ohne TF):** exakt wie im Deploy-Runbook per
> ARM-Template + `az cli` — falls TF-State/Provider-Setup Reibung macht. Ergebnis
> identisch. TF ist der reproduzierbare „Haupt"-Weg, den du dir gewünscht hast.

---

## 6. Der Button im s.O GPT (die einzige Änderung am GPT)

- Datei: `so-gpt-backend/static/index.html` (die real ausgelieferte).
- Einfügen: oben rechts im Header ein Button „**Zum Agent Cockpit**" (Phosphor-Icon
  `ph-rocket-launch`, Farbe `#d92b3a`), `href = COCKPIT_URL`.
- **Nur** auf der isolierten **Test-Instanz** deployen (`…-backend-test`), damit
  Rajs Live-App/`main`/`v25` unberührt bleibt.
- Umsetzung minimal-invasiv (siehe Vorschlag A in der Analyse) — **kein** Übernehmen
  von Stitchs komplettem Re-Skin.

---

## 7. Umsetzungs-Reihenfolge (wenn „Go")

1. **Scaffold** `agent-cockpit-backend/` (FastAPI + statisches Frontend-Grundgerüst).
2. **Frontend** aus Stitch-Export zusammenführen: Shell/Sidebar + 5 Views + Detail,
   Material-Symbols inline, `{{DATA:SCREEN}}`-Platzhalter durch echte Routen ersetzen.
3. **Katalog** `catalog_store.py` + `mock_seed.py` (5 Demo-Agenten der Screens).
4. **FinOps/AgentOps** read-only-Aggregation aus `sessions` + Mock-Ergänzung.
5. **Terraform** `infra/cockpit/` + erster Deploy → eigene URL.
6. **Button** in die s.O-GPT-Test-Instanz, `COCKPIT_URL` verdrahten, Test-App redeploy.
7. **Verifikation:** `/health` grün, Katalog lädt, Button springt hin und zurück.

---

## 8. Entscheidungen (Mike, 2026-07-21) & Restpunkte

**Entschieden:**
- ✅ **Monorepo:** Cockpit-Code liegt in **diesem** Repo (`agent-cockpit-backend/`),
  eigene Azure-App/URL. Kein separates Projekt.
- ✅ **s.O GPT bekommt NUR den Button** (oben rechts) — sonst unberührt. Kein
  `?agent_id`-Handoff, kein `/chat`-Umbau.
- ✅ **Agent-Chats im Cockpit**, im **s.O-GPT-Design**, pro Agent **Name + Historie
  reserviert** (`agent_chat`-Docs). Antworten **Mock**.
- ✅ **Reine Mock-Daten** für Katalog/FinOps/AgentOps.

- ✅ **Geteilter Compute-Plan** `plan-so-gpt-showcase-test` (wie s.O GPT); nur
  **App + Daten getrennt** (eigene Web App `app-agent-cockpit`, eigener Cosmos-
  Container `agents`).
- ✅ **Agent-Isolation:** jeder Agent = abgeschottetes „Mini-s.O-GPT" — eigener
  **Name + Daten/Wissen + Grundfragen + Chat-Historie**, ausschließlich für ihn.
  Design/Bedienung wie s.O GPT, aber keine Vermischung zwischen Agenten (Mock).
- ✅ **Cockpit-Daten getrennt:** eigene DB **`agent-cockpit-db`** (Katalog +
  Agent-Chats). s.O-GPT-Test teilt weiter `so-gpt-db/sessions` mit Raj (ok).
  Raj wird nicht angefasst; KV-Secret bleibt unverändert.
- ✅ **Echter Chat, Grounding-Variante A:** Agenten reden echt (Azure OpenAI gpt-4o,
  agenten-eigener System-Prompt, echte Historie), **ohne** RAG/Dokumenten-Grounding.
- ✅ **Subscription verifiziert:** `4155cf68-…-4a41-…` (PZI-DE-E-SUB001), Login aktiv,
  alle geteilten Ressourcen (Plan/Cosmos/KV/ACR/Test-App) existieren.
