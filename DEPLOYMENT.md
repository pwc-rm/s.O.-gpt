# S.O. GPT Showcase — Deployment Guide

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  Ingestion (automatisch)            Runtime (Chat)              │
│                                                                 │
│  Dokument hochladen                 Browser                     │
│       │                                │                        │
│       ▼                                ▼                        │
│  Blob Storage ──Trigger──▶  Azure Function App    App Service   │
│  (documents)               (ingest_on_upload)    (FastAPI)      │
│                                   │                  │          │
│                                   ▼                  ▼          │
│                            Azure AI Search ◀─────────┘          │
│                            (Vektor + BM25 + Semantic)           │
│                                                                 │
│  Alle Secrets in Key Vault — App Service + Function lesen       │
│  automatisch via Managed Identity (kein .env auf Azure)         │
└─────────────────────────────────────────────────────────────────┘
```

**Dokument hochladen → fertig.** Der Blob Trigger startet die Ingestion automatisch.

---

## Voraussetzungen

Tools installieren und prüfen:

```bash
terraform -version       # >= 1.6
az --version             # Azure CLI
func --version           # Azure Functions Core Tools >= 4.x
python3 --version        # >= 3.11
```

Links:
- [Terraform](https://developer.hashicorp.com/terraform/install)
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)

Azure-Login und Subscription setzen:

```bash
az login

# Falls mehrere Subscriptions vorhanden: richtige Subscription aktivieren
az account set --subscription "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
az account show  # Verify: prüfen ob die richtige Subscription aktiv ist
```

---

## Schritt 1 — Terraform ausführen

Erstellt alle Azure Ressourcen und schreibt alle Secrets automatisch in Key Vault.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Öffne `terraform.tfvars`, trage nur die Subscription ID ein:

```hcl
subscription_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
# Azure Portal → Subscriptions → Subscription ID
```

```bash
terraform init
terraform apply
```

Dauert ca. 10–15 Minuten. Danach sind folgende Ressourcen bereit:

| Ressource | Zweck |
|-----------|-------|
| Blob Storage | Dokument-Ablage + Function App State |
| Document Intelligence | PDF-Extraktion (OCR) |
| Azure AI Search (basic + Semantic) | Vektor + BM25 + Semantic Ranking |
| Cosmos DB (Serverless) | Chat-Session Store |
| Azure OpenAI | GPT-4o + text-embedding-3-large |
| Key Vault | Alle Secrets (automatisch befüllt durch Terraform) |
| Function App | Blob Trigger → automatische Ingestion |
| App Service (B1) | FastAPI Backend |

---

## Schritt 1.5 — AI Foundry AI Gateway einrichten (optional, empfohlen)

Terraform erstellt das Azure OpenAI Account direkt. Der AI Gateway davor muss manuell im
Azure AI Foundry Portal konfiguriert werden.  
**Ohne diesen Schritt funktioniert alles** — der Code ruft Azure OpenAI dann direkt an.

### Wann?
Nach `terraform apply`, bevor `.env` befüllt wird.

### Schritte im Portal

1. **[ai.azure.com](https://ai.azure.com) öffnen**

2. **Hub erstellen**  
   → New Hub → Resource Group: `RG-PLAYGROUND` → OpenAI Account `oai-so-gpt-showcase` verknüpfen

3. **Projekt erstellen**  
   → New Project → Name z.B. `so-gpt-project`

4. **Gateway konfigurieren**  
   → Projekt → Settings → AI Gateway → Add Gateway  
   → Rate Limiting: 10 000 TPM  
   → Token Usage Visibility: aktivieren  
   → Models: `gpt-4o-deployment` + `embedding-deployment`

5. **Gateway-Endpunkt kopieren**  
   → Format: `https://<hub-name>.openai.azure.com/`

### Einbinden

```bash
# Key Vault Secret auf Gateway-URL aktualisieren
az keyvault secret set \
  --vault-name kv-so-gpt-showcase \
  --name openai-endpoint \
  --value "https://<hub-name>.openai.azure.com/"
```

**Kein Code-Change nötig** — `config.py` liest `OPENAI_ENDPOINT` unabhängig davon ob
die URL auf den Gateway oder direkt auf OpenAI zeigt.

---

## Schritt 2 — Lokale `.env` befüllen

Nur für lokale Entwicklung, Index-Setup und eventuelle manuelle Ingestion nötig.  
Auf Azure lesen App Service und Function App Secrets direkt aus Key Vault — kein `.env` auf dem Server.

```bash
# .env aus der Vorlage erstellen
cp so-gpt-backend/.env.example so-gpt-backend/.env
```

Dann jeden Wert mit `terraform output` befüllen:

```bash
cd infra

terraform output -raw openai_endpoint          # → OPENAI_ENDPOINT
terraform output -raw openai_api_key           # → OPENAI_API_KEY
terraform output -raw search_endpoint          # → SEARCH_ENDPOINT
terraform output -raw search_api_key           # → SEARCH_API_KEY
terraform output -raw cosmos_connection_string # → COSMOS_CONNECTION_STRING
terraform output -raw blob_connection_string   # → BLOB_CONNECTION_STRING
terraform output -raw docintel_endpoint        # → DOCINTEL_ENDPOINT
terraform output -raw docintel_api_key         # → DOCINTEL_API_KEY
terraform output -raw backend_api_key          # → BACKEND_API_KEY
```

> Falls Schritt 1.5 gemacht: `OPENAI_ENDPOINT` auf die Gateway-URL setzen, nicht auf die direkte OpenAI URL.

---

## Schritt 2.5 — Python-Umgebung einrichten

Nötig für Schritt 3 (Index anlegen) und optionale lokale Ingestion:

```bash
cd so-gpt-backend
python3.11 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Testen ob die Verbindungen funktionieren:

```bash
python3 -c "import config; print(config.service_status())"
# Erwartet: {'openai': True, 'search': True, 'cosmos': True, ...}
```

---

## Schritt 3 — AI Search Index anlegen

Einmalig, vor der ersten Ingestion:

```bash
cd so-gpt-backend
python create_index.py
# Erwartet: "Index ready: so-gpt-index — 11 fields, vector dim=3072"
```

Index zurücksetzen (löscht alle Daten):

```bash
python create_index.py --recreate
```

---

## Schritt 4 — Backend + Function App deployen

### FastAPI Backend (App Service)

```bash
cd so-gpt-backend
zip -r ../deploy.zip . -x "venv/*" "*.pyc" "__pycache__/*" ".env"

az webapp deploy \
  --resource-group RG-PLAYGROUND \
  --name app-so-gpt-showcase-backend \
  --src-path ../deploy.zip
```

### Ingestion Function App

```bash
cd so-gpt-backend
func azure functionapp publish func-so-gpt-showcase-ingest --python
```

Function App Name aus Terraform:
```bash
cd infra && terraform output function_app_name
```

### Deployment verifizieren

```bash
# Backend Health Check — sollte {"status":"ok","services":{...}} zurückgeben
curl https://app-so-gpt-showcase-backend.azurewebsites.net/health

# Falls 503: Key Vault Reference noch nicht aufgelöst — 2 Minuten warten, dann nochmal
```

---

## Schritt 5 — Dokumente hochladen (löst Ingestion automatisch aus)

Ab jetzt reicht es, Dateien in den Blob Storage Container `documents` hochzuladen.  
Der Blob Trigger startet die Ingestion automatisch: extract → chunk → embed → index.

### Option A — Azure Portal

1. Azure Portal → Storage Account `stsogptshowcase` → Containers → `documents`
2. Upload → Dateien auswählen

### Option B — Azure CLI

```bash
# Einzelne Datei
az storage blob upload \
  --account-name stsogptshowcase \
  --container-name documents \
  --name "HR_Guidelines_2026.pdf" \
  --file "/lokaler/Pfad/HR_Guidelines_2026.pdf" \
  --auth-mode login

# Ganzen Ordner auf einmal
az storage blob upload-batch \
  --account-name stsogptshowcase \
  --destination documents \
  --source "/lokaler/Ordner/Showcase-Dokumente/" \
  --auth-mode login
```

### Option C — Azure Storage Explorer

Desktop-App (Drag & Drop):  
https://azure.microsoft.com/en-us/products/storage/storage-explorer

### Unterstützte Formate

| Format | Extraktion | OCR-fähig |
|--------|-----------|-----------|
| `.pdf` | Azure Document Intelligence | ✅ |
| `.docx` | markitdown (lokal, kein API-Call) | — |
| `.pptx` | markitdown (lokal, kein API-Call) | — |
| `.xlsx` | markitdown (lokal, kein API-Call) | — |

Andere Formate werden vom Trigger automatisch übersprungen.

### Ingestion-Status prüfen

```bash
# Live-Log der Function App
az functionapp logs tail \
  --resource-group RG-PLAYGROUND \
  --name func-so-gpt-showcase-ingest

# Oder im Portal: Function App → Monitor → Invocations
```

---

## Schritt 6 — Frontend konfigurieren und aufrufen

### API-URL und Key eintragen

Öffne `frontend/index.html`, trage oben im `<script>`-Block ein:

```javascript
const API_URL = 'https://app-so-gpt-showcase-backend.azurewebsites.net/chat';
const API_KEY = '<terraform output -raw backend_api_key>';
```

Werte abrufen:
```bash
cd infra
terraform output app_service_url        # → API_URL
terraform output -raw backend_api_key   # → API_KEY
```

### Frontend lokal aufrufen

> **Wichtig:** `frontend/index.html` direkt im Browser öffnen (`file://`) funktioniert **nicht** —
> Browser blockieren `fetch()` Calls von lokalen Dateien (CORS).

Stattdessen einen lokalen Webserver starten:

```bash
cd frontend
python3 -m http.server 3000
# → http://localhost:3000 im Browser öffnen
```

### Frontend auf Azure hosten (empfohlen für Demo)

Azure Static Web Apps — kostenlos, eine Zeile:

```bash
az staticwebapp create \
  --name swa-so-gpt-showcase \
  --resource-group RG-PLAYGROUND \
  --source frontend \
  --location "westeurope" \
  --branch main \
  --app-location "/" \
  --output-location ""
# Hinweis: Azure Static Web Apps ist in germanywestcentral nicht verfügbar.
# westeurope (Amsterdam) ist der nächstgelegene verfügbare Standort.
```

URL aus dem Output kopieren und als `API_URL` in `index.html` eintragen.

> **CORS-Hinweis:** In `so-gpt-backend/main.py` ist aktuell `allow_origins=["*"]` gesetzt.
> Für Produktion auf die konkrete Frontend-URL einschränken.

---

## Gesamtübersicht

| Schritt | Was | Manueller Aufwand |
|---------|-----|-------------------|
| 0 — Voraussetzungen | Tools + `az login` + `az account set` | Einmalig |
| 1 — Terraform | Alle Ressourcen + Key Vault Secrets | Nur `subscription_id` eintragen |
| 1.5 — AI Gateway | AI Foundry Hub + Gateway konfigurieren | Portal, ~10 Min (optional) |
| 2 — `.env` | `.env.example` kopieren + Outputs eintragen | Outputs kopieren |
| 2.5 — venv | Python-Umgebung + `pip install` | Ein Befehl |
| 3 — Index | AI Search Schema anlegen | Ein Befehl |
| 4 — Deploy | Backend + Function App + Health Check | Drei Befehle |
| 5 — Upload | Dokumente hochladen → Ingestion automatisch | Dateien hochladen |
| 6 — Frontend | URL + Key eintragen + hosten | Zwei Zeilen + ein Befehl |

---

## Neue Dokumente nachträglich hinzufügen

```bash
az storage blob upload \
  --account-name stsogptshowcase \
  --container-name documents \
  --name "NeuesDokument.pdf" \
  --file "./NeuesDokument.pdf" \
  --auth-mode login
```

Kein Redeploy, kein manuelles Script — Trigger startet Ingestion automatisch.

---

## Bewusste Abweichungen vom Architekturdokument

| Thema | Architekturdokument | Showcase-Implementierung | Grund |
|-------|--------------------|-----------------------------|-------|
| **Dokumentextraktion** | Document Intelligence für alle Formate | markitdown für Office, Doc Intelligence nur für PDF | Kostenersparnis ~60% |
| **AI Foundry AI Gateway** | Alle OpenAI-Calls über AI Gateway | Direkter Azure OpenAI Aufruf | Manuelles Portal-Setup, nicht via Terraform automatisierbar — Schritt 1.5 |

Beide Punkte für Produktivversion schließen.

---

## Troubleshooting

**`terraform apply` schlägt bei OpenAI fehl**  
→ GPT-4o Quota noch nicht genehmigt für `germanywestcentral`.  
→ Azure Portal → Quotas → Azure OpenAI → Quota-Erhöhung anfragen für `germanywestcentral`.  
→ Alternativ: `openai_location` in `terraform.tfvars` auf `"swedencentral"` oder `"westeurope"` setzen (dort ist Quota oft schneller verfügbar).

**`python3 -c "import config; ..."` zeigt `False` für einen Service**  
→ Den entsprechenden Wert in `.env` prüfen — leer oder falsch gesetzt.

**`create_index.py` schlägt fehl**  
→ `SEARCH_ENDPOINT` und `SEARCH_API_KEY` in `.env` prüfen.

**Health Check gibt 503 zurück**  
→ `az webapp log tail --resource-group RG-PLAYGROUND --name app-so-gpt-showcase-backend`  
→ Key Vault Reference noch nicht aufgelöst — 2 Minuten warten, dann erneut prüfen.

**Ingestion wird nach Upload nicht ausgelöst**  
→ Function App noch nicht deployed (Schritt 4 nachholen).  
→ Log prüfen: `az functionapp logs tail --resource-group RG-PLAYGROUND --name func-so-gpt-showcase-ingest`

**Blob Trigger feuert nicht für bereits vorhandene Dateien**  
→ Trigger reagiert nur auf neue/geänderte Blobs. Für bereits hochgeladene Dateien einmalig:
```bash
cd so-gpt-backend && python ingestion.py
```

**Frontend lädt aber Chat gibt Fehler zurück**  
→ `API_URL` und `API_KEY` in `frontend/index.html` prüfen.  
→ Browser-Konsole öffnen (F12) für den genauen Fehler.
