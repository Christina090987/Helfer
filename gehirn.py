"""Das "Gehirn": speichert alles, womit die Autorin den Assistenten füttert.

Alles liegt als JSON bzw. Text im Ordner `gehirn_daten/` – lesbar, kopierbar,
und es geht nichts verloren, wenn die App geschlossen wird.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

DATEN = Path(__file__).parent / "gehirn_daten"
KAPITEL = DATEN / "kapitel"

STANDARD_PROJEKT = {
    "titel": "Mein Roman",
    "genre": "Contemporary Romance",
    "stil_vorbilder": "T L. Swan, Neja Atalaj",
    "stil_beschreibung": (
        "Emotionale, sinnliche Contemporary Romance. Ich-Erzählerin, oft wechselnde "
        "Perspektive (sie / er). Schneller, bissiger Schlagabtausch, viel Humor, "
        "knisternde Spannung und Slow Burn, der irgendwann explodiert. Ein "
        "dominanter, aber verletzlicher Held, eine starke, freche Heldin. Kurze, "
        "pointierte Kapitel mit Cliffhanger. Gefühle werden körperlich spürbar "
        "beschrieben – Herzklopfen, Atem, Gänsehaut. Dialoge tragen die Szene."
    ),
    "pruefung_sprache": "Deutsch (neue Rechtschreibung)",
}


def _lies(datei: Path, standard):
    if datei.exists():
        return json.loads(datei.read_text(encoding="utf-8"))
    return standard


def _schreib(datei: Path, daten) -> None:
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")


def neue_id() -> str:
    return uuid.uuid4().hex[:8]


def jetzt() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


# --- Projekt -----------------------------------------------------------------

def projekt() -> dict:
    return {**STANDARD_PROJEKT, **_lies(DATEN / "projekt.json", {})}


def projekt_speichern(daten: dict) -> None:
    _schreib(DATEN / "projekt.json", daten)


# --- Listen: Figuren, Orte, Wissen ---------------------------------------------
# Figuren:  {id, name, rolle, alter, aussehen, charakter, wunde, ziel, sprechweise, notizen}
# Orte:     {id, name, beschreibung}
# Wissen:   {id, titel, inhalt, quelle, datum}   <- alles, womit gefüttert wird
# Stimme:   {id, titel, inhalt, datum}           <- Textproben im eigenen Stil
# Plan:     {id, kapitel, titel, pov, beat, inhalt, erledigt}

def liste(name: str) -> list:
    return _lies(DATEN / f"{name}.json", [])


def liste_speichern(name: str, eintraege: list) -> None:
    _schreib(DATEN / f"{name}.json", eintraege)


def eintrag_hinzufuegen(name: str, eintrag: dict) -> dict:
    eintraege = liste(name)
    eintrag = {"id": neue_id(), **eintrag}
    eintraege.append(eintrag)
    liste_speichern(name, eintraege)
    return eintrag


def eintrag_loeschen(name: str, eintrag_id: str) -> None:
    liste_speichern(name, [e for e in liste(name) if e["id"] != eintrag_id])


def figur_zusammenfuehren(neu: dict) -> None:
    """Fügt eine Figur hinzu oder ergänzt eine gleichnamige (Gehirn-Aufbau)."""
    figuren = liste("figuren")
    for f in figuren:
        if f["name"].strip().lower() == neu["name"].strip().lower():
            for feld, wert in neu.items():
                if wert and not f.get(feld):
                    f[feld] = wert
                elif wert and feld == "notizen" and wert not in f[feld]:
                    f[feld] += "\n" + wert
            liste_speichern("figuren", figuren)
            return
    eintrag_hinzufuegen("figuren", neu)


# --- Kapitel / Manuskript -------------------------------------------------------

def kapitel_liste() -> list[str]:
    KAPITEL.mkdir(parents=True, exist_ok=True)
    return sorted(p.stem for p in KAPITEL.glob("*.md"))


def kapitel_lesen(name: str) -> str:
    datei = KAPITEL / f"{name}.md"
    return datei.read_text(encoding="utf-8") if datei.exists() else ""


def kapitel_speichern(name: str, text: str) -> None:
    KAPITEL.mkdir(parents=True, exist_ok=True)
    (KAPITEL / f"{name}.md").write_text(text, encoding="utf-8")


def woerter(text: str) -> int:
    return len(text.split())


def manuskript_gesamt() -> str:
    return "\n\n".join(f"# {k}\n\n{kapitel_lesen(k)}" for k in kapitel_liste())


# --- Chat-Verlauf ---------------------------------------------------------------

def chat() -> list:
    return _lies(DATEN / "chat.json", [])


def chat_speichern(nachrichten: list) -> None:
    _schreib(DATEN / "chat.json", nachrichten)


# --- Gesamtbild für die KI ----------------------------------------------------

def als_text() -> str:
    """Fasst das ganze Gehirn als Kontext für den Assistenten zusammen."""
    p = projekt()
    teile = [
        f"# Projekt: {p['titel']}",
        f"Genre: {p['genre']}",
        f"Stil-Vorbilder: {p['stil_vorbilder']}",
        f"Stil: {p['stil_beschreibung']}",
    ]
    if p.get("handlung"):
        teile.append(f"\n## Handlung / Plot\n{p['handlung']}")

    figuren = liste("figuren")
    if figuren:
        teile.append("\n## Figuren")
        for f in figuren:
            details = "; ".join(
                f"{k}: {v}" for k, v in f.items() if k not in ("id", "name") and v
            )
            teile.append(f"- **{f['name']}** – {details}")

    orte = liste("orte")
    if orte:
        teile.append("\n## Orte")
        teile += [f"- **{o['name']}** – {o['beschreibung']}" for o in orte]

    stimme = liste("stimme")
    if stimme:
        teile.append(
            "\n## Stimmproben der Autorin – so klingt SIE. Wenn du für sie schreibst, "
            "triff genau diese Stimme (Satzlänge, Humor, Wortwahl, Rhythmus)."
        )
        teile += [f"### {s['titel']}\n{s['inhalt']}" for s in stimme]

    plan = liste("plan")
    if plan:
        teile.append("\n## Plot-Plan")
        teile += [
            f"- Kapitel {k['kapitel']} „{k['titel']}“ ({k['pov']}, {k['beat']})"
            f"{' ✓ geschrieben' if k.get('erledigt') else ''}: {k['inhalt']}"
            for k in plan
        ]

    wissen = liste("wissen")
    if wissen:
        teile.append("\n## Wissen, Notizen & Material der Autorin")
        teile += [f"### {w['titel']}\n{w['inhalt']}" for w in wissen]

    kapitel = kapitel_liste()
    if kapitel:
        teile.append("\n## Manuskript")
        teile += [f"### {k}\n{kapitel_lesen(k)}" for k in kapitel]

    return "\n".join(teile)
