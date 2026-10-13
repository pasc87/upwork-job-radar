# Upwork Job Radar

Persönliches Monitoring-Tool: ruft nächtlich (01:00-06:00 Uhr Europe/Berlin) aktuelle
Upwork-Jobpostings über die offizielle Upwork-GraphQL-API ab und sammelt sie dedupliziert
in Tages-Dateien. Morgens um 07:30 Uhr bewertet ein Vibe-Report jeden Job mit Patricks
5-Parameter-Score (Skill-Fit, Budget & Rate, Dauer, Kundenqualität, Erfolgsaussicht)
und liefert den sortierten Stack im Chat und per E-Mail – inklusive automatisch
entworfener Bewerbungsschreiben für die Top-Jobs.

## Architektur

- scripts/fetch_jobs.py – Fetch-Script (OAuth2-Refresh-Token -> GraphQL marketplaceJobPostingsSearch)
- config/search_terms.json – Suchbegriffe (jederzeit editierbar)
- state/seen.json – Deduplizierung über Job-IDs (14 Tage Aufbewahrung)
- data/YYYY-MM-DD.json – Tages-Ergebnisse (Basis für den Morgenreport)
- data/last_run.json – Status des letzten Laufs
- applications/YYYY-MM-DD/ – Bewertungs- und Bewerbungsentwürfe (Status: draft/approved/submitted/outcome)
- .github/workflows/nightly-radar.yml – stündlicher Nacht-Timer, DST-sicher

## Details

- Rate-Limit-freundlich: max. 2 Seiten pro Suchbegriff, 2,5 s Pause zwischen Abfragen,
  Retry mit Backoff bei HTTP 429.
- Manueller Testlauf: Repo -> Actions -> "Upwork Job Radar" -> Run workflow
  (überspringt das Zeitfenster; ohne Secrets bricht der Lauf kontrolliert ab).
- Setup-Anleitung: siehe SETUP.md
- Für den Live-Betrieb werden drei GitHub-Secrets benötigt:
  UPWORK_CLIENT_ID, UPWORK_CLIENT_SECRET, UPWORK_REFRESH_TOKEN.

Nur für den privaten Gebrauch des Account-Inhabers. Kein Scraping, keine Massenextraktion,
keine Weitergabe von Upwork-Daten.
