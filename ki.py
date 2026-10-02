"""Die Verbindung zu Claude: Zuhören, Ideen, Figuren, Korrektur, Gehirn-Aufbau."""

import json
from typing import Iterator

import anthropic

import gehirn

MODELL = "claude-opus-5-5"
# Lehnt Claude eine Anfrage aus Sicherheitsgründen ab, springt serverseitig
# automatisch ein passendes Ersatzmodell ein.
FALLBACK = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

GRUNDHALTUNG = """Du bist die persönliche Schreibpartnerin einer Romanautorin – \
eine erfahrene Lektorin, Ideengeberin und Freundin, die zuhört.

So arbeitest du:
- Du hörst zuerst zu. Wenn sie erzählt, was sie beschäftigt, nimm es ernst, \
frag nach, spiegle ihre Gedanken und hilf ihr, sie zu sortieren.
- Du gibst konkrete, mutige Ideen: Wendungen, Konflikte, Dialogzeilen, \
Kapitelenden, Gesten, kleine Details, die Figuren lebendig machen. Gern \
mehrere Varianten zur Auswahl.
- Du kennst ihr "Gehirn" (Figuren, Orte, Handlung, Notizen, Manuskript) und \
achtest auf Kontinuität: Namen, Augenfarben, Zeitlinie, wer was weiß.
- Wenn du selbst Text schreibst, dann im Stil ihrer Vorbilder (siehe Projekt): \
emotional, sinnlich, mit Humor, Tempo und Herz. Schreibe immer eigene, \
originelle Sätze – übernimm keine Passagen aus veröffentlichten Büchern.
- Du sprichst Deutsch, warm und direkt, ohne Floskeln. Ehrliches Feedback, \
aber immer so, dass sie Lust hat weiterzuschreiben."""


def client(api_key: str | None = None) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def _system() -> list[dict]:
    # Grundhaltung bleibt gleich, das Gehirn ändert sich – getrennt, damit
    # der Cache möglichst oft greift.
    return [
        {"type": "text", "text": GRUNDHALTUNG},
        {
            "type": "text",
            "text": "Das Gehirn – alles, was du über ihr Buch weißt:\n\n" + gehirn.als_text(),
            "cache_control": {"type": "ephemeral"},
        },
    ]


class Abgelehnt(Exception):
    pass


def _text(antwort) -> str:
    if antwort.stop_reason == "refusal":
        raise Abgelehnt("Diese Anfrage wurde leider abgelehnt. Formuliere sie bitte etwas anders.")
    return "".join(b.text for b in antwort.content if b.type == "text")


def streamen(c: anthropic.Anthropic, nachrichten: list[dict], effort: str = "medium") -> Iterator[str]:
    """Antwortet Wort für Wort (für Chat und Szenen)."""
    with c.beta.messages.stream(
        model=MODELL,
        max_tokens=64000,
        system=_system(),
        messages=nachrichten,
        output_config={"effort": effort},
        **FALLBACK,
    ) as stream:
        yield from stream.text_stream
        if stream.get_final_message().stop_reason == "refusal":
            yield "\n\n_(Diese Anfrage wurde leider abgelehnt. Formuliere sie bitte etwas anders.)_"


def _json(c: anthropic.Anthropic, auftrag: str, schema: dict, effort: str = "medium") -> dict:
    with c.beta.messages.stream(
        model=MODELL,
        max_tokens=32000,
        system=_system(),
        messages=[{"role": "user", "content": auftrag}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        **FALLBACK,
    ) as stream:
        antwort = stream.get_final_message()
    return json.loads(_text(antwort))


def _objekt(felder: dict) -> dict:
    return {
        "type": "object",
        "properties": felder,
        "required": list(felder),
        "additionalProperties": False,
    }


TXT = {"type": "string"}

FIGUR = _objekt({
    "name": TXT,
    "rolle": TXT,
    "alter": TXT,
    "aussehen": TXT,
    "charakter": TXT,
    "wunde": TXT,
    "ziel": TXT,
    "sprechweise": TXT,
    "notizen": TXT,
})


def figur_erstellen(c: anthropic.Anthropic, wunsch: str) -> dict:
    """Entwirft eine vollständige Figur aus einer kurzen Idee."""
    auftrag = (
        "Entwirf eine Romanfigur für mein Buch, passend zu Genre, Stil und den "
        "bestehenden Figuren. Fülle jedes Feld lebendig und konkret: 'wunde' = "
        "ihre seelische Verletzung aus der Vergangenheit, 'ziel' = was sie will "
        "vs. was sie braucht, 'sprechweise' = wie sie redet (mit 2–3 typischen "
        "Sätzen), 'notizen' = Macken, Geheimnisse, Konfliktpotenzial mit anderen "
        f"Figuren.\n\nMeine Idee: {wunsch}"
    )
    return _json(c, auftrag, FIGUR, effort="high")


KORREKTUR = _objekt({
    "korrigierter_text": TXT,
    "aenderungen": {
        "type": "array",
        "items": _objekt({"vorher": TXT, "nachher": TXT, "grund": TXT}),
    },
    "stil_tipps": {"type": "array", "items": TXT},
})


def korrigieren(c: anthropic.Anthropic, text: str, nur_fehler: bool) -> dict:
    """Rechtschreibung, Grammatik, Zeichensetzung – optional mit Stil-Tipps."""
    sprache = gehirn.projekt()["pruefung_sprache"]
    auftrag = (
        f"Prüfe den folgenden Romantext auf Rechtschreibung, Grammatik und "
        f"Zeichensetzung ({sprache}, inklusive korrekter Zeichensetzung in "
        "wörtlicher Rede). Verändere NICHT ihren Stil, ihre Wortwahl oder "
        "bewusste Umgangssprache in Dialogen – korrigiere nur echte Fehler. "
        "Liste jede Änderung einzeln auf. "
        + ("Lass 'stil_tipps' leer." if nur_fehler else
           "Gib in 'stil_tipps' zusätzlich 3–6 konkrete Vorschläge, wie die "
           "Stelle noch emotionaler, spannender oder flüssiger wird – und "
           "achte dabei auf Widersprüche zum Gehirn (Namen, Fakten, Zeitlinie).")
        + f"\n\nText:\n<<<\n{text}\n>>>"
    )
    return _json(c, auftrag, KORREKTUR, effort="medium")


GEHIRN_AUFBAU = _objekt({
    "handlung": TXT,
    "figuren": {"type": "array", "items": FIGUR},
    "orte": {"type": "array", "items": _objekt({"name": TXT, "beschreibung": TXT})},
    "fakten": {"type": "array", "items": TXT},
    "offene_faeden": {"type": "array", "items": TXT},
})


def gehirn_aufbauen(c: anthropic.Anthropic) -> dict:
    """Liest Manuskript und Material und zieht daraus Figuren, Orte, Fakten."""
    auftrag = (
        "Lies alles, was im Gehirn steht – vor allem das Manuskript und mein "
        "Material – und baue daraus mein Buch-Gedächtnis auf:\n"
        "- 'handlung': aktuelle Zusammenfassung des Plots bis hierhin\n"
        "- 'figuren': jede Figur mit allem, was der Text über sie verrät "
        "(unbekannte Felder leer lassen, nichts erfinden)\n"
        "- 'orte': alle Schauplätze\n"
        "- 'fakten': wichtige Details für die Kontinuität (Augenfarben, Daten, "
        "Beziehungen, wer welches Geheimnis kennt …)\n"
        "- 'offene_faeden': angefangene Handlungsstränge, Versprechen an die "
        "Leserin, Widersprüche, die noch aufgelöst werden müssen"
    )
    return _json(c, auftrag, GEHIRN_AUFBAU, effort="high")
