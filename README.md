# ✍️ Helfer – dein KI-Schreibpartner fürs Bücherschreiben

Ein persönlicher Assistent, der **zuhört**, **Ideen gibt**, **Figuren erschafft**,
**Rechtschreibung prüft** und sich in einem **Gehirn** alles merkt, womit du ihn fütterst.
Er schreibt im Stil deiner Vorbilder (voreingestellt: *T L. Swan, Neja Atalaj* –
emotionale, sinnliche Romance mit Humor und Slow Burn). Stil und Vorbilder kannst
du jederzeit links unter „📖 Mein Buch & Stil“ ändern.

## Was kann er?

| Bereich | Was passiert |
|---|---|
| 💬 **Erzähl mir** | Du erzählst, wo du festhängst – er hört zu, fragt nach, gibt Ideen. Gute Ideen mit einem Klick ins Gehirn. |
| ✍️ **Schreiben** | Szenen entwerfen lassen (Perspektive, Länge, „süß / knisternd / spicy“) und Kapitel speichern. |
| 👤 **Figuren** | Aus einer kurzen Idee entsteht eine ganze Figur: Aussehen, Charakter, Wunde, Ziel, Sprechweise, Geheimnisse. |
| 🔍 **Korrektur** | Rechtschreibung, Grammatik, Zeichensetzung – ohne deinen Stil zu verändern. Jede Änderung wird erklärt, dazu Stil-Tipps. |
| 🧠 **Gehirn** | Notizen, Orte und Dateien (.txt, .md, .docx) hochladen. „Gehirn aufbauen“ liest dein Manuskript und zieht Figuren, Orte, Handlung, Kontinuitäts-Fakten und offene Fäden heraus. |

Alles wird automatisch im Ordner `gehirn_daten/` auf deinem Computer gespeichert
(Chat, Figuren, Orte, Notizen, Kapitel). Der Ordner wird **nicht** zu GitHub hochgeladen –
dein Buch bleibt privat. Sichern: Button „⬇️ Ganzes Gehirn als Textdatei sichern“
oder einfach den Ordner kopieren.

## Starten

1. Python 3.10+ installieren.
2. Einmalig:
   ```bash
   pip install -r requirements.txt
   ```
3. API-Schlüssel holen auf <https://console.anthropic.com> (kostenpflichtig nach Verbrauch).
4. Starten:
   ```bash
   streamlit run app.py
   ```
   Der Browser öffnet sich. Schlüssel links eintragen (oder vorher
   `export ANTHROPIC_API_KEY=...` setzen) – los geht's.
