"""
Mock seed data for the s.Oliver Agent Cockpit (PoC).

Five demo agents derived from the Stitch screens. All governance/FinOps/AgentOps
numbers are fictional. The `source` field models the "Auto-Discovery" story: agents
are discovered from several agent platforms (Azure AI Foundry, Amazon Bedrock,
Custom / In-House) — shown on the dashboard so you can see WHERE each agent lives.

Each agent gets its own `system_prompt` (its persona/scope) and `grundfragen`
(starter questions). The chat itself is REAL (Azure OpenAI gpt-4o) — only the
catalog/metadata is seeded.
"""

# ── Sources (the platforms agents are "discovered" from) ──────────────────────
SOURCES = {
    "azure-ai-foundry": {"label": "Azure AI Foundry", "icon": "cloud", "color": "#0078d4"},
    "amazon-bedrock":   {"label": "Amazon Bedrock",   "icon": "aws",   "color": "#ff9900"},
    "custom-inhouse":   {"label": "Custom / In-House", "icon": "dns",   "color": "#5f5e61"},
}


AGENTS: list[dict] = [
    {
        "id": "hr-vacation-assistant",
        "doc_type": "agent",
        "name": "HR Urlaubsassistent",
        "description": "Automatisiert die Beantragung und Genehmigung von Urlaubsanträgen gemäß s.Oliver Richtlinien.",
        "category": "HR & People",
        "status": "active",
        "source": "azure-ai-foundry",
        "business_owner": "Sarah Müller",
        "org_unit": "HR Dept",
        "model": "gpt-4o",
        "temperature": 0.2,
        "icon": "event_available",
        "system_prompt": (
            "Du bist der HR Urlaubsassistent der s.Oliver Group. Antworte immer auf "
            "Deutsch, professionell und freundlich. Du hilfst Mitarbeitenden bei "
            "Urlaubsanträgen, Resturlaubsabfragen und HR-Richtlinien. Wenn du etwas "
            "nicht sicher weißt, verweise an hr-support@s-oliver.com."
        ),
        "grundfragen": [
            "Wie viele Urlaubstage habe ich dieses Jahr noch übrig?",
            "Was sind die Richtlinien für Sonderurlaub bei s.Oliver?",
            "Kann ich meinen Resturlaub ins nächste Jahr mitnehmen?",
        ],
        "cmdb": {
            "application_container": "HR-Services-Prod",
            "configuration_item": "CI-992834",
            "servicenow_link": "https://service-now.com/nav_to.do?uri=cmdb_ci.do?sys_id=992834",
        },
        "permissions": [
            {"entity": "All_Employees", "type": "ad_group", "role": "user"},
            {"entity": "Sarah Müller", "type": "user", "role": "owner"},
        ],
        "knowledge": {
            "documents": [
                {"name": "Betriebsvereinbarung_Urlaub_2024.pdf", "size": "1.2 MB", "uploaded_at": "2024-05-12", "status": "indexed"},
                {"name": "FAQ_Sonderurlaub.docx", "size": "45 KB", "uploaded_at": "2024-05-15", "status": "indexed"},
            ],
            "retrieval": {"chunk_size": 1024, "top_k": 5, "strict_mode": True},
        },
        "finops": {"tokens_used": 12_500_000, "quota": 20_000_000, "cost_eur": 2640, "trend_pct": 12, "budget_eur": 3500, "alert_threshold_pct": 85},
        "agentops": {"calls_24h": 1240, "avg_latency_ms": 1200, "qa_score": 94, "adoption_rate": 0.68, "feedback_avg": 4.8, "health": "active"},
        "rating": {"up": 142, "down": 8},
    },
    {
        "id": "recruiting-screener",
        "doc_type": "agent",
        "name": "Recruiting Screener",
        "description": "Analysiert Lebensläufe und gleicht sie mit Anforderungsprofilen ab.",
        "category": "HR & People",
        "status": "inactive",
        "source": "amazon-bedrock",
        "business_owner": "Thomas Becker",
        "org_unit": "Recruiting",
        "model": "claude-3-5-sonnet",
        "temperature": 0.3,
        "icon": "person_search",
        "system_prompt": (
            "Du bist der Recruiting Screener der s.Oliver Group. Du analysierst "
            "Lebensläufe sachlich und neutral und gleichst sie mit Anforderungsprofilen "
            "ab. Antworte auf Deutsch, strukturiert und ohne Diskriminierung."
        ),
        "grundfragen": [
            "Fasse die Kernqualifikationen dieses Lebenslaufs zusammen.",
            "Passt dieses Profil zur Stellenausschreibung 'Data Analyst'?",
            "Welche Rückfragen sollte ich im Interview stellen?",
        ],
        "cmdb": {
            "application_container": "HR-Services-Prod",
            "configuration_item": "CI-993110",
            "servicenow_link": "https://service-now.com/nav_to.do?uri=cmdb_ci.do?sys_id=993110",
        },
        "permissions": [
            {"entity": "Recruiting_Team", "type": "ad_group", "role": "user"},
            {"entity": "Thomas Becker", "type": "user", "role": "owner"},
        ],
        "knowledge": {
            "documents": [
                {"name": "Anforderungsprofile_2024.pdf", "size": "820 KB", "uploaded_at": "2024-04-02", "status": "indexed"},
            ],
            "retrieval": {"chunk_size": 1024, "top_k": 4, "strict_mode": False},
        },
        "finops": {"tokens_used": 4_100_000, "quota": 10_000_000, "cost_eur": 980, "trend_pct": -4, "budget_eur": 1500, "alert_threshold_pct": 85},
        "agentops": {"calls_24h": 210, "avg_latency_ms": 890, "qa_score": 91, "adoption_rate": 0.22, "feedback_avg": 4.5, "health": "active"},
        "rating": {"up": 34, "down": 6},
    },
    {
        "id": "it-support-bot",
        "doc_type": "agent",
        "name": "IT Support Bot Level 1",
        "description": "Löst grundlegende Passwort-Resets und Hardware-Anfragen via Teams-Integration.",
        "category": "IT & Infrastructure",
        "status": "inactive",
        "source": "custom-inhouse",
        "business_owner": "IT Helpdesk",
        "org_unit": "IT Services",
        "model": "gpt-4o",
        "temperature": 0.1,
        "icon": "support_agent",
        "system_prompt": (
            "Du bist der IT Support Bot Level 1 der s.Oliver Group. Du hilfst bei "
            "Passwort-Resets, Hardware-Anfragen und einfachen IT-Problemen. Antworte "
            "auf Deutsch, knapp und lösungsorientiert. Eskaliere komplexe Fälle an das "
            "IT Helpdesk (Ticket im ServiceNow)."
        ),
        "grundfragen": [
            "Wie setze ich mein Windows-Passwort zurück?",
            "Mein Laptop verbindet sich nicht mit dem WLAN – was tun?",
            "Wie beantrage ich eine neue Maus über den Helpdesk?",
        ],
        "cmdb": {
            "application_container": "IT-Services-Prod",
            "configuration_item": "CI-778201",
            "servicenow_link": "https://service-now.com/nav_to.do?uri=cmdb_ci.do?sys_id=778201",
        },
        "permissions": [
            {"entity": "All_Employees", "type": "ad_group", "role": "user"},
            {"entity": "IT_Admins", "type": "ad_group", "role": "owner"},
        ],
        "knowledge": {
            "documents": [
                {"name": "IT_Servicekatalog.pdf", "size": "2.1 MB", "uploaded_at": "2024-03-20", "status": "indexed"},
            ],
            "retrieval": {"chunk_size": 512, "top_k": 5, "strict_mode": True},
        },
        "finops": {"tokens_used": 18_200_000, "quota": 20_000_000, "cost_eur": 3200, "trend_pct": 3, "budget_eur": 3000, "alert_threshold_pct": 85},
        "agentops": {"calls_24h": 3120, "avg_latency_ms": 450, "qa_score": 96, "adoption_rate": 0.51, "feedback_avg": 4.6, "health": "degraded"},
        "rating": {"up": 210, "down": 40},
    },
    {
        "id": "sales-forecasting",
        "doc_type": "agent",
        "name": "Sales Forecasting",
        "description": "Analysiert wöchentliche Verkaufsdaten und generiert Prognosen für B2B Key Accounts.",
        "category": "Sales & Marketing",
        "status": "active",
        "source": "azure-ai-foundry",
        "business_owner": "Lisa Schmidt",
        "org_unit": "Sales B2B",
        "model": "gpt-4o",
        "temperature": 0.4,
        "icon": "monitoring",
        "system_prompt": (
            "Du bist der Sales Forecasting Assistent der s.Oliver Group. Du analysierst "
            "Verkaufsdaten und erstellst nachvollziehbare Prognosen für B2B Key Accounts. "
            "Antworte auf Deutsch, datengetrieben und mit klaren Annahmen."
        ),
        "grundfragen": [
            "Wie entwickelt sich der Umsatz für Key Account Nord im Q3?",
            "Welche Accounts zeigen ein Abwärtsrisiko?",
            "Erstelle eine Prognose-Zusammenfassung für das Management.",
        ],
        "cmdb": {
            "application_container": "Sales-Analytics-Prod",
            "configuration_item": "CI-661044",
            "servicenow_link": "https://service-now.com/nav_to.do?uri=cmdb_ci.do?sys_id=661044",
        },
        "permissions": [
            {"entity": "Sales_B2B", "type": "ad_group", "role": "user"},
            {"entity": "Lisa Schmidt", "type": "user", "role": "owner"},
        ],
        "knowledge": {
            "documents": [
                {"name": "Sales_Playbook_2024.pdf", "size": "3.4 MB", "uploaded_at": "2024-02-11", "status": "indexed"},
            ],
            "retrieval": {"chunk_size": 1024, "top_k": 6, "strict_mode": False},
        },
        "finops": {"tokens_used": 9_500_000, "quota": 15_000_000, "cost_eur": 2100, "trend_pct": 8, "budget_eur": 3000, "alert_threshold_pct": 85},
        "agentops": {"calls_24h": 640, "avg_latency_ms": 1100, "qa_score": 89, "adoption_rate": 0.44, "feedback_avg": 4.7, "health": "active"},
        "rating": {"up": 88, "down": 9},
    },
    {
        "id": "social-media-copywriter",
        "doc_type": "agent",
        "name": "Social Media Copywriter",
        "description": "Erstellt Entwürfe für LinkedIn und Instagram basierend auf Kampagnen-Briefings.",
        "category": "Sales & Marketing",
        "status": "inactive",
        "source": "amazon-bedrock",
        "business_owner": "Marketing Team",
        "org_unit": "Marketing",
        "model": "gpt-4o",
        "temperature": 0.8,
        "icon": "edit_note",
        "system_prompt": (
            "Du bist der Social Media Copywriter der s.Oliver Group. Du schreibst "
            "kreative, markengerechte Entwürfe für LinkedIn und Instagram auf Basis von "
            "Kampagnen-Briefings. Antworte auf Deutsch, im modernen s.Oliver-Ton."
        ),
        "grundfragen": [
            "Schreibe einen LinkedIn-Post zur neuen Herbstkollektion.",
            "Erstelle 3 Instagram-Caption-Varianten für ein Denim-Produkt.",
            "Formuliere einen Teaser für unsere Nachhaltigkeits-Kampagne.",
        ],
        "cmdb": {
            "application_container": "Marketing-Content-Prod",
            "configuration_item": "CI-550287",
            "servicenow_link": "https://service-now.com/nav_to.do?uri=cmdb_ci.do?sys_id=550287",
        },
        "permissions": [
            {"entity": "Marketing_Team", "type": "ad_group", "role": "user"},
            {"entity": "Marketing Lead", "type": "user", "role": "owner"},
        ],
        "knowledge": {
            "documents": [
                {"name": "Brand_Voice_Guidelines.pdf", "size": "1.0 MB", "uploaded_at": "2024-01-30", "status": "indexed"},
            ],
            "retrieval": {"chunk_size": 1024, "top_k": 4, "strict_mode": False},
        },
        "finops": {"tokens_used": 3_400_000, "quota": 8_000_000, "cost_eur": 880, "trend_pct": -2, "budget_eur": 1500, "alert_threshold_pct": 85},
        "agentops": {"calls_24h": 95, "avg_latency_ms": 1300, "qa_score": 87, "adoption_rate": 0.18, "feedback_avg": 4.4, "health": "active"},
        "rating": {"up": 45, "down": 12},
    },
]


# ── Global settings (Screen 05) ───────────────────────────────────────────────
API_KEYS = [
    {"id": "key-mkt", "name": "Marketing Agent Prod", "created_at": "2023-10-12", "status": "active"},
    {"id": "key-dev", "name": "Dev Analytics Test", "created_at": "2023-09-05", "status": "inactive"},
]

ORG_UNITS = [
    {"name": "Marketing", "members": 12},
    {"name": "Sales", "members": 8},
    {"name": "Engineering", "members": 24},
]

USER_PROFILE = {"first_name": "Max", "last_name": "Mustermann", "email": "max.mustermann@s-oliver.de"}


def _cost_trend(days: int = 30) -> list[float]:
    """A plausible daily-cost series for the last N days (mock, gentle upward trend)."""
    import math
    return [round(280 + i * 3.2 + 38 * math.sin(i / 2.7), 1) for i in range(days)]


def finops_summary(agents=None) -> dict:
    """Aggregated FinOps KPIs across all agents (mock). Pass the live catalog
    agents so budget edits are reflected; defaults to the static seed."""
    agents = agents if agents is not None else AGENTS
    total_cost = sum(a["finops"]["cost_eur"] for a in agents)
    total_tokens = sum(a["finops"]["tokens_used"] for a in agents)
    total_budget = sum(a["finops"].get("budget_eur", 0) for a in agents)  # per-agent rollup
    trend = _cost_trend(30)

    def _status(f: dict) -> str:
        th = (f.get("alert_threshold_pct", 85)) / 100
        cost_util = f["cost_eur"] / f["budget_eur"] if f.get("budget_eur") else 0
        token_util = f["tokens_used"] / f["quota"] if f.get("quota") else 0
        return "warning" if max(cost_util, token_util) >= th else "ok"

    return {
        "budget_eur": total_budget,
        "budget_trend_pct": -4,
        "tokens_used": total_tokens,
        "tokens_trend_pct": 12,
        "cost_per_request_eur": 0.012,
        "total_cost_eur": total_cost,
        "trend": trend,
        "trend_avg_eur": round(sum(trend) / len(trend)),
        "total_spend_eur": round(sum(trend)),
        "peak_day_eur": round(max(trend)),
        "trend_change_pct": round((trend[-1] - trend[0]) / trend[0] * 100, 1),
        "agents": [
            {"id": a["id"], "name": a["name"], "owner": a["org_unit"],
             "tokens_used": a["finops"]["tokens_used"], "quota": a["finops"]["quota"],
             "cost_eur": a["finops"]["cost_eur"], "budget_eur": a["finops"].get("budget_eur", 0),
             "alert_threshold_pct": a["finops"].get("alert_threshold_pct", 85),
             "status": _status(a["finops"])}
            for a in agents
        ],
    }


def agentops_summary(agents=None) -> dict:
    """Aggregated AgentOps KPIs + alerts (mock)."""
    agents = agents if agents is not None else AGENTS
    return {
        "avg_latency_ms": 840,
        "adoption_rate": 0.68,
        "qa_score": 94.2,
        "feedback_avg": 4.8,
        "alerts": [
            {"level": "error", "title": "API Timeout: Sales Forecasting",
             "message": "Verbindung zum internen Data Warehouse fehlgeschlagen. 3 Retries erfolglos.", "ago": "Vor 12 Minuten"},
            {"level": "warning", "title": "Token Limit nähert sich: HR Urlaubsassistent",
             "message": "Monatliches Kontingent zu 85% ausgeschöpft.", "ago": "Vor 2 Stunden"},
        ],
        "agents": [
            {"id": a["id"], "name": a["name"], "health": a["agentops"]["health"],
             "calls_24h": a["agentops"]["calls_24h"], "avg_latency_ms": a["agentops"]["avg_latency_ms"]}
            for a in agents
        ],
    }
