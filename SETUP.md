# Setup – Schritt für Schritt

## Schritt 1: Upwork-API-Key beantragen

1. upwork.com/developer öffnen -> API Center -> "Request new API Key".
2. Formular ausfüllen:
   - Title: "Upwork Job Radar"
   - Project type: "Web project"
   - Callback URL: z. B. https://www.patrickschmicker.de/upwork-callback
     (Die Seite muss nicht existieren – nach der OAuth-Autorisierung erscheint der
     Code als ?code=... in der Browser-Adressleiste und wird von dort kopiert.)
   - Project description: ehrlich und konkret formulieren, z. B.:
     "Personal job-search monitoring tool for a single freelance professional (account
     owner). Queries the official GraphQL API (marketplaceJobPostingsSearch) nightly for
     my own job feed using my saved search terms, so I can review relevant postings in
     the morning. Read-only usage for my own account. No scraping, no mass data
     collection, no redistribution of Upwork data, no automated proposals."
   - API Usage: 1-10 · Rotation Period: 12 Months
3. GraphQL-Berechtigungen setzen (Permissions -> GraphQL):
   - "Read marketplace Job Postings" aktiviert lassen
   - "Read public marketplace Job Postings" aktiviert lassen
   - "Common Entities - Read-Only Access" aktivieren
   - Optional: "Job Details Entities - Read-Only Access"
   - Alles andere deaktiviert lassen (insbesondere "Submit Proposal", Write-Scopes,
     Messaging, Payments) – minimale Rechte verbessern die Freigabe-Chance.
4. "I agree to comply with the Upwork API Terms of Use" anhaken -> Submit.
   Hinweis: Keys sind nach dem Absenden zunächst deaktiviert; Upwork prüft die Angaben
   (meist innerhalb weniger Tage).

## Schritt 2: OAuth2-Refresh-Token erzeugen (einmalig, sobald der Key freigegeben ist)

1. Authorize-URL im Browser öffnen (CLIENT_ID einsetzen):

       https://www.upwork.com/ab/account-security/oauth2/authorize/?client_id=CLIENT_ID&response_type=code&redirect_uri=https%3A%2F%2Fwww.patrickschmicker.de%2Fupwork-callback&state=radar

2. Nach dem Login leitet Upwork zur Callback-URL weiter. Aus der Browser-Adressleiste
   den Wert hinter ?code= kopieren.
3. Code gegen Tokens tauschen (curl/Terminal):

       curl -X POST "https://www.upwork.com/ab/account-security/oauth2/token" -d "grant_type=authorization_code" -d "client_id=CLIENT_ID" -d "client_secret=CLIENT_SECRET" -d "code=CODE" -d "redirect_uri=https://www.patrickschmicker.de/upwork-callback"

   Antwort enthält access_token und refresh_token. Wichtig: nur der refresh_token
   ist langfristig gültig (Rotation beachten, siehe Upwork-Doku).

## Schritt 3: GitHub-Secrets hinterlegen

Repo -> Settings -> Secrets and variables -> Actions -> "New repository secret":

- UPWORK_CLIENT_ID
- UPWORK_CLIENT_SECRET
- UPWORK_REFRESH_TOKEN

## Schritt 4: Manueller Testlauf

Repo -> Actions -> "Upwork Job Radar" -> Run workflow. Der Lauf überspringt das
Zeitfenster (RADAR_FORCE=1) und schreibt bei Erfolg neue Jobs in data/<Datum>.json.

## Troubleshooting

- HTTP 429: Rate Limit – das Script wartet automatisch (30/60/90 s) und bricht ggf. ab.
  Bei ~10 Suchbegriffen pro Nacht reicht das Fenster 01:00-06:00 locker aus.
- GraphQL-Fehler "scope missing": Berechtigung im API-Key fehlt -> API Center prüfen.
- Fehler bei searchTerm_eq: Alternativ im Suchbegriff-Eintrag "field" auf
  "titleExpression" oder "skillExpression" stellen.
- Token-Endpoint: Falls /ab/account-security/oauth2/token einen 404 liefert, ist
  alternativ /api/v3/oauth2/token zu verwenden (in scripts/fetch_jobs.py, TOKEN_URL).
