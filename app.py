"""Helfer – dein KI-Schreibpartner fürs Bücherschreiben.

Start:  streamlit run app.py
"""

import io
import os

import anthropic
import streamlit as st

import gehirn
import ki

st.set_page_config(page_title="Helfer – Schreibpartner", page_icon="✍️", layout="wide")

# --- Seitenleiste: Schlüssel & Projekt -------------------------------------------

with st.sidebar:
    st.title("✍️ Helfer")
    st.caption("Hört zu · gibt Ideen · baut Figuren · korrigiert · merkt sich alles")

    api_key = st.text_input(
        "Anthropic API-Schlüssel",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Bekommst du unter console.anthropic.com. Wird nicht gespeichert.",
    )

    p = gehirn.projekt()
    with st.expander("📖 Mein Buch & Stil", expanded=False):
        p["titel"] = st.text_input("Titel", p["titel"])
        p["genre"] = st.text_input("Genre", p["genre"])
        p["stil_vorbilder"] = st.text_input("Schreib wie …", p["stil_vorbilder"])
        p["stil_beschreibung"] = st.text_area("So klingt mein Buch", p["stil_beschreibung"], height=200)
        p["pruefung_sprache"] = st.text_input("Sprache für Korrektur", p["pruefung_sprache"])
        if st.button("Speichern", key="projekt_speichern"):
            gehirn.projekt_speichern(p)
            st.success("Gespeichert.")


def verbindung() -> anthropic.Anthropic | None:
    if not api_key:
        st.warning("Bitte links deinen API-Schlüssel eintragen.")
        return None
    return ki.client(api_key)


def ki_fehler(fehler: Exception) -> None:
    if isinstance(fehler, anthropic.AuthenticationError):
        st.error("Der API-Schlüssel stimmt nicht.")
    elif isinstance(fehler, anthropic.RateLimitError):
        st.error("Gerade zu viele Anfragen – bitte kurz warten und nochmal versuchen.")
    elif isinstance(fehler, anthropic.APIConnectionError):
        st.error("Keine Verbindung zum Internet / zu Claude.")
    elif isinstance(fehler, ki.Abgelehnt):
        st.error(str(fehler))
    else:
        st.error(f"Da ist etwas schiefgelaufen: {fehler}")


chat_tab, schreib_tab, figuren_tab, korrektur_tab, gehirn_tab = st.tabs(
    ["💬 Erzähl mir", "✍️ Schreiben", "👤 Figuren", "🔍 Korrektur", "🧠 Gehirn"]
)

# --- 💬 Zuhören & Ideen -------------------------------------------------------------

with chat_tab:
    st.subheader("Erzähl mir, woran du gerade schreibst")
    st.caption("Ich höre zu, frage nach und gebe dir Ideen. Alles wird gespeichert.")

    verlauf = gehirn.chat()
    for n in verlauf:
        with st.chat_message("user" if n["role"] == "user" else "assistant",
                             avatar="🖋️" if n["role"] == "user" else "💡"):
            st.markdown(n["content"])

    spalte1, spalte2 = st.columns([1, 5])
    if spalte1.button("Neues Gespräch"):
        gehirn.chat_speichern([])
        st.rerun()
    if verlauf and spalte2.button("📌 Letzte Idee ins Gehirn"):
        letzte = next(n for n in reversed(verlauf) if n["role"] == "assistant")
        gehirn.eintrag_hinzufuegen("wissen", {
            "titel": f"Idee aus dem Gespräch ({gehirn.jetzt()})",
            "inhalt": letzte["content"], "quelle": "Chat", "datum": gehirn.jetzt(),
        })
        st.success("Im Gehirn gespeichert.")

    if eingabe := st.chat_input("Was beschäftigt dich? Wo hängst du fest?"):
        c = verbindung()
        if c:
            verlauf.append({"role": "user", "content": eingabe})
            with st.chat_message("user", avatar="🖋️"):
                st.markdown(eingabe)
            with st.chat_message("assistant", avatar="💡"):
                try:
                    antwort = st.write_stream(ki.streamen(c, verlauf))
                    verlauf.append({"role": "assistant", "content": antwort})
                    gehirn.chat_speichern(verlauf)
                except Exception as e:  # noqa: BLE001 – Fehler freundlich anzeigen
                    ki_fehler(e)

# --- ✍️ Szenen schreiben & Manuskript ----------------------------------------------

with schreib_tab:
    st.subheader("Szenen schreiben & Manuskript")
    links, rechts = st.columns(2)

    with links:
        st.markdown("**Lass mich eine Szene entwerfen**")
        szene = st.text_area(
            "Was soll passieren?",
            placeholder="z. B. Sie trifft ihren neuen Chef im Aufzug – sie hat ihn letzte Nacht an der Bar abblitzen lassen …",
            height=140,
        )
        perspektive = st.selectbox("Perspektive", ["Ich – Heldin", "Ich – Held", "Abwechselnd", "Dritte Person"])
        laenge = st.select_slider("Länge", ["kurz", "mittel", "lang"], value="mittel")
        hitze = st.select_slider("Wie heiß?", ["süß", "knisternd", "spicy"], value="knisternd")
        if st.button("✨ Szene schreiben") and szene:
            c = verbindung()
            if c:
                auftrag = (
                    f"Schreib diese Szene für mein Buch, im Stil von {gehirn.projekt()['stil_vorbilder']}. "
                    f"Perspektive: {perspektive}. Länge: {laenge}. Hitzegrad: {hitze}. "
                    "Halte dich an Figuren und Fakten aus dem Gehirn. Nur der Szenentext, "
                    f"keine Vorrede.\n\nSzene: {szene}"
                )
                try:
                    st.session_state["entwurf"] = st.write_stream(
                        ki.streamen(c, [{"role": "user", "content": auftrag}], effort="high"))
                except Exception as e:  # noqa: BLE001
                    ki_fehler(e)

    with rechts:
        st.markdown("**Mein Manuskript**")
        kapitel = gehirn.kapitel_liste()
        auswahl = st.selectbox("Kapitel", ["➕ Neues Kapitel"] + kapitel)
        if auswahl == "➕ Neues Kapitel":
            name = st.text_input("Name", f"Kapitel {len(kapitel) + 1:02d}")
            inhalt = st.session_state.get("entwurf", "")
        else:
            name = auswahl
            inhalt = gehirn.kapitel_lesen(auswahl)
        text = st.text_area("Text", inhalt, height=480, key=f"kapitel_{name}_{hash(inhalt)}")
        if st.button("💾 Kapitel speichern"):
            gehirn.kapitel_speichern(name, text)
            st.session_state.pop("entwurf", None)
            st.success(f"„{name}“ gespeichert.")

# --- 👤 Figuren ---------------------------------------------------------------------

FIGUR_FELDER = {
    "rolle": "Rolle", "alter": "Alter", "aussehen": "Aussehen", "charakter": "Charakter",
    "wunde": "Seelische Wunde", "ziel": "Will / braucht", "sprechweise": "Sprechweise",
    "notizen": "Notizen & Geheimnisse",
}

with figuren_tab:
    st.subheader("Figuren erschaffen")
    idee = st.text_input(
        "Beschreib kurz, wen du brauchst",
        placeholder="z. B. Arroganter Milliardär, Anfang 30, hat seine Schwester verloren, ist der beste Freund ihres Bruders",
    )
    if st.button("✨ Figur entwerfen") and idee:
        c = verbindung()
        if c:
            with st.spinner("Ich erwecke die Figur zum Leben …"):
                try:
                    st.session_state["figur_entwurf"] = ki.figur_erstellen(c, idee)
                except Exception as e:  # noqa: BLE001
                    ki_fehler(e)

    if entwurf := st.session_state.get("figur_entwurf"):
        with st.form("figur_form"):
            st.markdown("**Entwurf – pass an, was du willst:**")
            entwurf["name"] = st.text_input("Name", entwurf["name"])
            for feld, label in FIGUR_FELDER.items():
                entwurf[feld] = st.text_area(label, entwurf.get(feld, ""))
            if st.form_submit_button("💾 Ins Gehirn übernehmen"):
                gehirn.eintrag_hinzufuegen("figuren", entwurf)
                st.session_state.pop("figur_entwurf")
                st.rerun()

    st.divider()
    for f in gehirn.liste("figuren"):
        with st.expander(f"👤 {f['name']} – {f.get('rolle', '')}"):
            for feld, label in FIGUR_FELDER.items():
                if f.get(feld):
                    st.markdown(f"**{label}:** {f[feld]}")
            if st.button("Löschen", key=f"fig_del_{f['id']}"):
                gehirn.eintrag_loeschen("figuren", f["id"])
                st.rerun()

# --- 🔍 Korrektur -------------------------------------------------------------------

with korrektur_tab:
    st.subheader("Rechtschreibung & Grammatik prüfen")
    quelle = st.radio("Was prüfen?", ["Eigenen Text einfügen", "Kapitel aus dem Manuskript"], horizontal=True)
    if quelle == "Kapitel aus dem Manuskript" and gehirn.kapitel_liste():
        kap = st.selectbox("Kapitel", gehirn.kapitel_liste(), key="korr_kap")
        pruef_text = gehirn.kapitel_lesen(kap)
        st.text_area("Inhalt", pruef_text, height=200, disabled=True)
    else:
        kap = None
        pruef_text = st.text_area("Dein Text", height=250)
    nur_fehler = st.checkbox("Nur Fehler – keine Stil-Tipps", value=False)

    if st.button("🔍 Prüfen") and pruef_text.strip():
        c = verbindung()
        if c:
            with st.spinner("Ich lese ganz genau …"):
                try:
                    st.session_state["korrektur"] = (kap, ki.korrigieren(c, pruef_text, nur_fehler))
                except Exception as e:  # noqa: BLE001
                    ki_fehler(e)

    if "korrektur" in st.session_state:
        kap_k, erg = st.session_state["korrektur"]
        if not erg["aenderungen"]:
            st.success("Keine Fehler gefunden. 🎉")
        for a in erg["aenderungen"]:
            st.markdown(f"~~{a['vorher']}~~ → **{a['nachher']}**  \n<small>{a['grund']}</small>",
                        unsafe_allow_html=True)
        if erg["stil_tipps"]:
            st.markdown("**💡 Stil-Tipps**")
            for t in erg["stil_tipps"]:
                st.markdown(f"- {t}")
        st.text_area("Korrigierter Text (zum Kopieren)", erg["korrigierter_text"], height=250)
        if kap_k and st.button(f"✅ Korrektur in „{kap_k}“ übernehmen"):
            gehirn.kapitel_speichern(kap_k, erg["korrigierter_text"])
            st.session_state.pop("korrektur")
            st.success("Übernommen und gespeichert.")

# --- 🧠 Gehirn ----------------------------------------------------------------------


def datei_lesen(datei) -> str:
    if datei.name.lower().endswith(".docx"):
        import docx  # python-docx

        return "\n".join(a.text for a in docx.Document(io.BytesIO(datei.getvalue())).paragraphs)
    return datei.getvalue().decode("utf-8", errors="replace")


with gehirn_tab:
    st.subheader("🧠 Das Gehirn – alles, was ich über dein Buch weiß")

    st.markdown("**Füttere mich**")
    dateien = st.file_uploader("Notizen, Recherche, alte Kapitel (.txt, .md, .docx)",
                               type=["txt", "md", "docx"], accept_multiple_files=True)
    if dateien and st.button("📥 Dateien speichern"):
        for d in dateien:
            gehirn.eintrag_hinzufuegen("wissen", {
                "titel": d.name, "inhalt": datei_lesen(d), "quelle": "Datei", "datum": gehirn.jetzt(),
            })
        st.success(f"{len(dateien)} Datei(en) gespeichert.")

    with st.form("notiz", clear_on_submit=True):
        titel = st.text_input("Notiz-Titel", placeholder="z. B. Weltregeln, Recherche Hamburg, Playlist …")
        inhalt = st.text_area("Inhalt")
        if st.form_submit_button("💾 Notiz speichern") and inhalt:
            gehirn.eintrag_hinzufuegen("wissen", {
                "titel": titel or "Notiz", "inhalt": inhalt, "quelle": "Notiz", "datum": gehirn.jetzt(),
            })
            st.success("Gespeichert.")

    with st.form("ort", clear_on_submit=True):
        ort_name = st.text_input("Neuer Ort")
        ort_text = st.text_area("Beschreibung", height=80)
        if st.form_submit_button("💾 Ort speichern") and ort_name:
            gehirn.eintrag_hinzufuegen("orte", {"name": ort_name, "beschreibung": ort_text})
            st.success("Gespeichert.")

    st.divider()
    st.markdown("**Gehirn aufbauen** – ich lese Manuskript und Material und ziehe Figuren, "
                "Orte, Handlung, Fakten und offene Fäden heraus.")
    if st.button("🧠 Gehirn aufbauen / aktualisieren"):
        c = verbindung()
        if c:
            with st.spinner("Ich lese alles und sortiere meine Gedanken …"):
                try:
                    erg = ki.gehirn_aufbauen(c)
                    proj = gehirn.projekt()
                    proj["handlung"] = erg["handlung"]
                    gehirn.projekt_speichern(proj)
                    for f in erg["figuren"]:
                        gehirn.figur_zusammenfuehren(f)
                    bekannte_orte = {o["name"].lower() for o in gehirn.liste("orte")}
                    for o in erg["orte"]:
                        if o["name"].lower() not in bekannte_orte:
                            gehirn.eintrag_hinzufuegen("orte", o)
                    for titel, punkte in (("Kontinuitäts-Fakten", erg["fakten"]),
                                          ("Offene Fäden", erg["offene_faeden"])):
                        alte = [w for w in gehirn.liste("wissen") if w["titel"] == titel]
                        for w in alte:
                            gehirn.eintrag_loeschen("wissen", w["id"])
                        if punkte:
                            gehirn.eintrag_hinzufuegen("wissen", {
                                "titel": titel, "inhalt": "\n".join(f"- {x}" for x in punkte),
                                "quelle": "Gehirn-Aufbau", "datum": gehirn.jetzt(),
                            })
                    st.success("Gehirn aktualisiert! ✨")
                except Exception as e:  # noqa: BLE001
                    ki_fehler(e)

    st.divider()
    proj = gehirn.projekt()
    if proj.get("handlung"):
        with st.expander("📜 Handlung bisher", expanded=True):
            st.markdown(proj["handlung"])
    for o in gehirn.liste("orte"):
        with st.expander(f"📍 {o['name']}"):
            st.markdown(o["beschreibung"])
            if st.button("Löschen", key=f"ort_del_{o['id']}"):
                gehirn.eintrag_loeschen("orte", o["id"])
                st.rerun()
    for w in gehirn.liste("wissen"):
        with st.expander(f"📎 {w['titel']}  ·  {w.get('quelle', '')} {w.get('datum', '')}"):
            st.markdown(w["inhalt"])
            if st.button("Löschen", key=f"wis_del_{w['id']}"):
                gehirn.eintrag_loeschen("wissen", w["id"])
                st.rerun()

    st.download_button("⬇️ Ganzes Gehirn als Textdatei sichern", gehirn.als_text(),
                       file_name="gehirn.md")
