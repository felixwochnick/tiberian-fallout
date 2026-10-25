# Command & Conquer: Tiberian Fallout

Fan-Spiel im Browser auf Basis von *Command & Conquer: Tiberian Sun* – Nuxt 4 + Three.js.

Es werden keine Original-Spieldateien mitgeliefert. Auf der Startseite lädt der Browser
die seit 2010 kostenlosen Original-CDs (ZIP-Archive von cnc-comm.com) direkt herunter und
entpackt die Spielarchive noch während des Downloads – ohne Installation, auf jedem
Betriebssystem. Alternativ lässt sich eine vorhandene Installation bzw. ein CD-Image
importieren. Die Dateien landen im Origin Private File System (OPFS) des Browsers.

Weil der Mirror keine CORS-Header sendet, leitet die Server-Route
`server/api/game-data/[disc].get.ts` die Anfragen (inkl. Range-Header) nur durch;
auf dem Server wird nichts gespeichert. Die App braucht deshalb einen Node-Server
(`pnpm build && node .output/server/index.mjs`), ein rein statisches Hosting reicht nicht.

```bash
pnpm install
pnpm dev        # http://localhost:3000
pnpm test       # Unit-Tests der Dateiformate
pnpm typecheck

# optionale Tests mit echten Daten bzw. gegen einen laufenden Dev-Server
TS_DATA=/pfad/zu/mix-dateien pnpm test
E2E_BASE=http://localhost:3000 pnpm test
```

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `app/lib/formats/` | Westwood-Dateiformate: MIX (inkl. Blowfish/RSA-Header), AUD (IMA ADPCM), INI, ISO 9660 (auch als Stream) |
| `app/lib/download/` | Liest einzelne Einträge aus entfernten ZIP-Dateien per HTTP-Range |
| `shared/game-discs.ts` | Katalog der Freeware-CDs und welche Archive daraus übernommen werden |
| `app/lib/storage/` | Persistenter Speicher für importierte Dateien (OPFS, Fallback im Speicher) |
| `app/lib/game/` | Spiellogik auf Basis der Assets (aktuell: Soundtrack aus `SCORES.MIX`) |
| `app/lib/menu/` | Startanimation vor dem Hauptmenü: lädt das Blender-Modell, ergänzt Hologramm, Lichtblitz und Low-Fi-Look, spielt Original-Sound und Menümusik `INTRO.AUD` |
| `blender/` | `startup_menu.py` baut Modelle, prozedurale Shader und Animation der Startanimation auf, backt die Shader in Texturen und exportiert `public/models/startup-menu.glb`; `startup_menu.blend` ist die Arbeitsdatei |
| `blender/GAPILE.py` | GDI-Kaserne: Modell, Tarnmuster-Shader (gebacken), Fahne mit GDI-Logo, Clips `Build` (Aufbau, einmalig) und `Idle` (Fahne im Wind, Blinklichter) → `public/models/GAPILE.glb`. Neu bauen: `Blender -b --factory-startup --python blender/GAPILE.py` (ca. 10 s) |
| `blender/GAPOWR.py` | GDI-Kraftwerk: Kühlturm im Streben-Kranz mit vier Lichtebenen (blinken von unten nach oben, oben rot), drei runde Turbinenplätze mit je vier Löchern (Knoten `TurbineSlot1…3`), Clips `Build` und `Idle` → `public/models/GAPOWR.glb`. Neu bauen: `Blender -b --factory-startup --python blender/GAPOWR.py` |
| `blender/GAPOWRUP.py` | Turbine (Ausbau des Kraftwerks): drei gestufte Ringe mit angestellten Schaufeln, Messingkern mit leuchtenden Fenstern, wird mit `Battlefield.addUpgrade` auf den nächsten freien Platz montiert; Clips `Build` und `Idle` (die ganze Turbine über dem Fuß dreht sich) → `public/models/GAPOWRUP.glb`. Neu bauen: `Blender -b --factory-startup --python blender/GAPOWRUP.py` |
| `blender/DSHP.py` | GDI-Dropship aus zwei Teilen nach `help/buildings/GDI/DSHP/img_1-3.png` (rund 4,8 × 2,5 Felder): oben das Flugzeug (schlanker Rumpf mit tiefer runder Nase, Kanzel, Scheinwerfer, Emblem, Heckausleger; vier Triebwerksgondeln an langen Tragarmen weit vom Rumpf, vorderes und hinteres Paar mit Abstand), darunter eingeklinkt der Frachtbehälter (flach-sechseckiger Querschnitt, Lamellen-Mittelteil, Emblem und „CP 034“, Heckrampe; fasst Fahrzeuge bis MCV-Größe); Tarnmuster; Clips `Fly`, `Land`, `Landed`, `TakeOff`, `Crash`, `Lights` (Flughöhe in den Clips, Knoten `CargoExit`) → `public/models/DSHP.glb`. Neu bauen: `Blender -b --factory-startup --python blender/DSHP.py` |
| `app/lib/game/dropship.ts` | Dropship im Spiel: fliegt ein, landet, entlädt über die Rampe, startet und fliegt ab; `crash()` lässt es abstürzen (`Battlefield.addDropship`); `onSound` meldet Landen, Starten und Aufschlag (Sounds `DROPDWN1`, `DROPUP1`, `EXPNEW09/10/12` in `BattlefieldView`) |
| `blender/MCV.py` | Mobiles Bauhof-Fahrzeug (MCV): Ketten mit Laufrollen, Kabine, Kranausleger; Clips `Idle` und `Walk`, `walkSpeed` als glTF-Extra; `vehicle()` wird vom Bauhof wiederverwendet → `public/models/MCV.glb` |
| `blender/GACNST.py` | Bauhof: Halle, davor das MCV mit grauem Kran, der sich zum Tor dreht und den Greifer herablässt; Querschnitt nach `help/buildings/GDI/GACNST/Frame 1.svg`: Hülle im Tarnmuster (gebacken) mit Hausfarben-Bändern, links gerundet mit Rippen und Wellblech bis zum First (Lampenreihe), rechts abfallende Schräge mit drei Achtspeichen-Lüftern und dem Lüftungsschacht unter grauer Riffelhaube, darunter zwei Stufen mit grauen Kanten, Schornstein mit Antennen, achteckige Betonplatte (Details nach `img_4.png`); `Build` = Aufklappanimation, `Idle`: Lüfter, Lauflicht, `Deliver` (beim Platzieren eines Gebäudes): Kran nimmt eine Kiste aus der Halle und lässt sie in die Luke → `public/models/GACNST.glb`. Neu bauen: `Blender -b --factory-startup --python blender/GACNST.py` |
| `blender/GASAND.py` | Sandsäcke: Mittelstück und vier Arme (`ArmXP/XN/ZP/ZN`) aus versetzt gestapelten Säcken; das Spiel blendet die Arme zu benachbarten Sandsäcken ein (`Battlefield.connectWalls`), so entstehen gerade Wände, Ecken, T-Stücke und Kreuzungen; Clip `Build` → `public/models/GASAND.glb` |
| `blender/TIB.py` | Tiberium (Riparius) auf einem Feld nach `help/tiberium/`: viele kleine, flache, sternförmige Büschel neongrüner Kristallsplitter (leuchtende Spitzen) über die ganze Zelle, dazwischen grauweiße Keime, aus denen in der nächsten Phase Büschel wachsen; drei Wachstumsphasen in je drei Varianten als Knoten `Stage1A` … `Stage3C` → `public/models/TIB.glb`. Den grünen Boden zeichnet das Spiel. Neu bauen: `Blender -b --factory-startup --python blender/TIB.py` |
| `app/lib/game/tiberium.ts` | Tiberium-Felder: `tiberiumField()` erzeugt ein rundliches, lückenhaftes Feld (Mitte reif, Rand jung); `Battlefield.addTiberium` setzt es auf die Karte (je Zelle zufällige Variante und Drehung). Der Boden-Shader färbt den Boden bis 4 Felder um das Feld olivgrün ein (die Bodenstruktur bleibt sichtbar), unter den Kristallen grüner und leicht pulsierend; alle 15 s wächst eine zufällige Zelle eine Phase, Gebäude können nicht auf Tiberium gebaut werden. Im Gefecht liegt ein Feld rechts unterhalb des Startpunkts |
| `blender/E1.py` | Leichte GDI-Infanterie: geriggter Soldat mit Gewehr, Clips `Idle` (stehen), `Walk` (laufen), `GoProne` (hinwerfen, rückwärts = aufstehen), `Prone` (liegen), `Crawl` (robben), alle auf der Stelle, Laufgeschwindigkeit als glTF-Extra `walkSpeed` → `public/models/E1.glb`. Neu bauen: `Blender -b --factory-startup --python blender/E1.py` |
| `app/lib/game/unit.ts` | Einheit auf dem Schlachtfeld: läuft zu einem Ziel, dreht sich dorthin, blendet zwischen Stehen und Laufen über, wirft sich unter Beschuss hin und robbt (`Battlefield.addUnit`) |
| `app/composables/` | `useGameAssets` (Import/Status), `useMusicPlayer` (Web Audio) |
| `app/components/` | Downloader, Importer, Musikplayer, Startanimation + Hauptmenü (`/menu`, im Dev-Modus mit `?t=2.5` einfrierbar) |

Die Formatbeschreibungen orientieren sich an [OpenRA](https://github.com/OpenRA/OpenRA).

## Startanimation in Blender bearbeiten

`blender/startup_menu.blend` öffnen oder die Szene neu erzeugen (Scripting-Tab):

```python
PATH = '/pfad/zum/projekt/blender/startup_menu.py'
ns = {'__file__': PATH}
exec(compile(open(PATH).read(), PATH, 'exec'), ns)
ns['build']()       # Modelle, Shader, Animation (6 s, 30 fps)
ns['bake_all']()    # Shader → Texturen (Cycles, GPU empfohlen)
ns['export_glb']()  # → public/models/startup-menu.glb
```

Oder ohne Blender-Oberfläche (Backen dauert mit GPU ca. 15 min):

```bash
Blender -b --factory-startup --python blender/run_pipeline.py
# nur einzelne Objekte neu backen:
Blender -b blender/startup_menu.blend --python blender/run_pipeline.py -- --rebake Plate,PlateOuter
```
