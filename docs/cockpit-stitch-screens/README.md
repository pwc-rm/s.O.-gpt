# Stitch-Export → Agent Cockpit (Import-Ordner)

Hier landen die aus Google Stitch exportierten Screens für die App
**s.Oliver Agent Cockpit**. Claude Code liest diesen Ordner, analysiert die
Screens und leitet daraus die POC-Logik (mit Mock-Daten) ab.

## Erwartete Struktur

Pro Seite ein Unterordner mit **genau diesen 3 Dateien**:

```
docs/cockpit-stitch-screens/
├── library/
│   ├── screen.png     # Screenshot des Screens
│   ├── DESIGN.md      # Design-/UX-Beschreibung aus Stitch
│   └── code.html      # exportierter HTML/CSS/JS-Code
├── collections/
│   ├── screen.png
│   ├── DESIGN.md
│   └── code.html
├── analytics/
│   ├── screen.png
│   ├── DESIGN.md
│   └── code.html
└── settings/
    ├── screen.png
    ├── DESIGN.md
    └── code.html
```

> Ordnernamen sind Vorschläge — passt gern zu euren echten Screen-Namen.
> Wichtig ist nur: **ein Unterordner pro Seite**, jeweils die 3 Dateien.

## Was danach passiert (Claude Code)

1. Alle Seiten lesen (`DESIGN.md` + `code.html` + Screenshot).
2. Pro Seite: verstehen, **was die Seite fachlich tut**, Datenmodell ableiten.
3. POC-Logik mit Mock-Daten bauen (Cosmos-DB-Muster wie im s.O GPT).
4. Pro Seite **Änderungsvorschläge** dokumentieren, bevor gebaut wird.
