# Arbeitsweise für Claude in diesem Projekt

Gilt auf jedem Rechner (diese Datei liegt im Repo). Überblick über Aufbau und Dateiformate: `README.md`.

## Commits

- Gearbeitet wird auf dem Branch `dev-claude-auto`.
- Nach jeder abgeschlossenen, thematisch zusammengehörenden Änderung **selbständig committen**, bevor es
  mit dem nächsten Thema weitergeht (ohne nachzufragen). Ein Commit = ein Thema.
- Fehlt die Git-Identität auf dem Rechner, nicht global konfigurieren, sondern pro Commit:
  `git -c "user.name=Felix Wochnick" -c user.email=felix@wochnick.me commit …`
- Nicht pushen und nicht auf `main` committen, außer es wird ausdrücklich verlangt.

## Testen

- Im Browser wird **in Chromium** getestet, nicht in Firefox – über den MCP-Server `tiberian-fallout`
  (`scripts/mcp/tiberian_fallout.py`):
  1. `pnpm dev` im Hintergrund starten.
  2. `tf_browser_open` (Pfad z. B. `/skirmish`) startet Chromium mit eigenem Profil; auf einem neuen Rechner
     einmal `tf_browser_import` (MIX-Dateien der Steam-Installation, sonst `directory` angeben).
  3. Spielen über das Agent-Relay (`tf_state`, `tf_command`, `tf_wait`, `tf_map`), UI über `tf_browser_click`/
     `_key`/`_screenshot`, Fehler mit `tf_browser_console`.
  4. Nach Codeänderungen den Tab mit `tf_browser_open` neu laden (Hot-Reload kann ein veraltetes Spiel
     verbunden lassen).
- Zum Vergleich mit dem Original: MCP-Server `tiberian-sun` (`scripts/mcp/tiberian_sun.py`) – spielt die
  Steam-Version per Proton in einem eigenen Xwayland-Fenster und liest `rules.ini`/`firestrm.ini`/`art.ini` …
  aus den MIX-Archiven (`ts_rules`, `ts_rules_search`, `ts_file`). Werte und Verhalten für Tiberian Fallout
  dort nachschlagen statt sie zu raten.
- Unit-Tests: `pnpm test`, Typen: `pnpm typecheck`.

## Stil

- Code und Kommentare auf Englisch, Doku (README) und Texte im Spiel auf Deutsch.
- Die MCP-Server sind reines Python ohne Zusatzpakete; so soll es bleiben.
