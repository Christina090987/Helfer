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
        p["wortziel"] = st.number_input("Wortziel fürs Buch", 10000, 300000, int(p.get("wortziel", 80000)), 5000)
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


chat_tab, plan_tab, schreib_tab, werkstatt_tab, figuren_tab, korrektur_tab, gehirn_tab = st.tabs(
    ["💬 Erzähl mir", "📋 Plot-Plan", "✍️ Schreiben", "🎨 Überarbeiten", "👤 Figuren", "🔍 Korrektur", "🧠 Gehirn"]
)

def manuskript_docx() -> bytes:
    import docx  # python-docx

    dok = docx.Document()
    dok.add_heading(gehirn.projekt()["titel"], 0)
    for k in gehirn.kapitel_liste():
        dok.add_page_break()
        dok.add_heading(k, 1)
        for absatz in gehirn.kapitel_lesen(k).split("\n"):
            if absatz.strip():
                dok.add_paragraph(absatz.strip())
    puffer = io.BytesIO()
    dok.save(puffer)
    return puffer.getvalue()


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

# --- 📋 Plot-Plan ------------------------------------------------------------------

with plan_tab:
    st.subheader("Dein Buch – Kapitel für Kapitel geplant")
    st.caption("Entlang der Romance-Beats: Meet-Cute, Reibung, erster Kuss, Bruch, Grand Gesture, Happy End …")
    idee = st.text_area("Worum geht's? (leer lassen = ich nutze das Gehirn)", height=100,
                        placeholder="z. B. Sie wird die Nanny des grummeligen Witwers, der ihr Jugendschwarm war …")
    anzahl = st.slider("Wie viele Kapitel?", 10, 60, 30)
    if st.button("✨ Plot planen"):
        c = verbindung()
        if c:
            with st.spinner("Ich plane dein Buch …"):
                try:
                    st.session_state["plan_entwurf"] = ki.plot_planen(c, idee, anzahl)
                except Exception as e:  # noqa: BLE001
                    ki_fehler(e)

    if entwurf_plan := st.session_state.get("plan_entwurf"):
        st.markdown("**Vorschlag:**")
        for k in entwurf_plan:
            st.markdown(f"**{k['kapitel']}. {k['titel']}** · _{k['pov']} · {k['beat']}_  \n{k['inhalt']}")
        a, b = st.columns(2)
        if a.button("💾 Diesen Plan übernehmen"):
            gehirn.liste_speichern("plan", [{"id": gehirn.neue_id(), "erledigt": False, **k} for k in entwurf_plan])
            st.session_state.pop("plan_entwurf")
            st.rerun()
        if b.button("Verwerfen"):
            st.session_state.pop("plan_entwurf")
            st.rerun()

    plan = gehirn.liste("plan")
    if plan:
        st.divider()
        fertig = sum(k.get("erledigt", False) for k in plan)
        st.markdown(f"**Mein Plan** – {fertig} von {len(plan)} Kapiteln geschrieben")
        st.progress(fertig / len(plan))
        for k in plan:
            with st.expander(f"{'✅' if k.get('erledigt') else '⬜'} {k['kapitel']}. {k['titel']} · {k['pov']}"):
                k["titel"] = st.text_input("Titel", k["titel"], key=f"pt_{k['id']}")
                k["pov"] = st.text_input("Sicht", k["pov"], key=f"pp_{k['id']}")
                k["beat"] = st.text_input("Beat", k["beat"], key=f"pb_{k['id']}")
                k["inhalt"] = st.text_area("Was passiert", k["inhalt"], key=f"pi_{k['id']}")
                k["erledigt"] = st.checkbox("Geschrieben", k.get("erledigt", False), key=f"pe_{k['id']}")
                s1, s2 = st.columns(2)
                if s1.button("💾 Speichern", key=f"ps_{k['id']}"):
                    gehirn.liste_speichern("plan", plan)
                    st.rerun()
                if s2.button("✍️ Als Szene schreiben", key=f"pw_{k['id']}"):
                    st.session_state["szene_text"] = (
                        f"Kapitel {k['kapitel']} „{k['titel']}“ ({k['beat']}), Sicht: {k['pov']}. {k['inhalt']}"
                    )
                    st.toast("Übernommen – wechsle zum Reiter ✍️ Schreiben.")
                    st.rerun()

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
            key="szene_text",
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
        st.caption(f"{gehirn.woerter(text):,} Wörter in diesem Kapitel".replace(",", "."))
        if st.button("💾 Kapitel speichern"):
            gehirn.kapitel_speichern(name, text)
            st.session_state.pop("entwurf", None)
            st.success(f"„{name}“ gespeichert.")

    st.divider()
    gesamt = gehirn.manuskript_gesamt()
    ziel = int(gehirn.projekt().get("wortziel", 80000))
    geschafft = sum(gehirn.woerter(gehirn.kapitel_lesen(k)) for k in gehirn.kapitel_liste())
    st.markdown(f"**Fortschritt:** {geschafft:,} von {ziel:,} Wörtern".replace(",", "."))
    st.progress(min(geschafft / ziel, 1.0))
    if gesamt:
        e1, e2 = st.columns(2)
        e1.download_button("⬇️ Manuskript als Word (.docx)", manuskript_docx(),
                           file_name=f"{gehirn.projekt()['titel']}.docx")
        e2.download_button("⬇️ Manuskript als Text (.md)", gesamt,
                           file_name=f"{gehirn.projekt()['titel']}.md")

# --- 🎨 Überarbeiten ----------------------------------------------------------------

with werkstatt_tab:
    st.subheader("Überarbeiten – eine Stelle besser machen")
    passage = st.text_area("Füg die Stelle ein, die noch nicht sitzt", height=220)
    art = st.radio("Was soll besser werden?", list(ki.UEBERARBEITUNGEN), horizontal=True)
    extra = st.text_input("Noch ein Wunsch? (optional)", placeholder="z. B. Er soll am Ende nicht nachgeben")
    if st.button("🎨 Überarbeiten") and passage.strip():
        c = verbindung()
        if c:
            l, r = st.columns(2)
            l.markdown("**Vorher**")
            l.markdown(passage)
            with r:
                st.markdown("**Nachher**")
                try:
                    st.session_state["ueberarbeitet"] = st.write_stream(ki.ueberarbeiten(c, passage, art, extra))
                except Exception as e:  # noqa: BLE001
                    ki_fehler(e)
    if st.session_state.get("ueberarbeitet"):
        st.text_area("Zum Kopieren", st.session_state["ueberarbeitet"], height=200)

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

    with st.form("stimme", clear_on_submit=True):
        st.markdown("**🎙️ Meine Stimme** – füg Texte ein, die du selbst geschrieben hast und die "
                    "so klingen, wie du klingen willst. Ich lerne daraus deinen Stil.")
        st_titel = st.text_input("Titel der Probe", placeholder="z. B. Lieblingsszene Kapitel 3")
        st_text = st.text_area("Deine Textprobe", height=150)
        if st.form_submit_button("💾 Stimmprobe speichern") and st_text:
            gehirn.eintrag_hinzufuegen("stimme", {"titel": st_titel or "Stimmprobe", "inhalt": st_text,
                                                   "datum": gehirn.jetzt()})
            st.success("Gespeichert – ab jetzt schreibe ich mehr wie du.")

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
    for s_probe in gehirn.liste("stimme"):
        with st.expander(f"🎙️ {s_probe['titel']}  ·  Stimmprobe {s_probe.get('datum', '')}"):
            st.markdown(s_probe["inhalt"])
            if st.button("Löschen", key=f"sti_del_{s_probe['id']}"):
                gehirn.eintrag_loeschen("stimme", s_probe["id"])
                st.rerun()
    for w in gehirn.liste("wissen"):
        with st.expander(f"📎 {w['titel']}  ·  {w.get('quelle', '')} {w.get('datum', '')}"):
            st.markdown(w["inhalt"])
            if st.button("Löschen", key=f"wis_del_{w['id']}"):
                gehirn.eintrag_loeschen("wissen", w["id"])
                st.rerun()

    st.download_button("⬇️ Ganzes Gehirn als Textdatei sichern", gehirn.als_text(),
                       file_name="gehirn.md")
