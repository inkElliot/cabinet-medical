import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import (
    create_tables,
    add_medic, get_medici, delete_medic,
    add_pacient, get_pacienti, delete_pacient,
    add_programare, get_programari_by_medic_data, get_all_programari,
    update_status_programare, delete_programare, is_slot_ocupat,
    add_istoric, get_istoric,
)

create_tables()

# ── Helpers ───────────────────────────────────────────────────────────────────
ORE = [f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30)]

STATUS_COLORS = {
    "Programat":  "🔵",
    "Confirmat":  "🟢",
    "Anulat":     "🔴",
    "Finalizat":  "⚫",
}

def medici_dict():
    return {f"{n} ({s})": mid for mid, n, s in get_medici()}

def pacienti_dict():
    return {f"{n}": pid for pid, n, *_ in get_pacienti()}


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Cabinet Medical", layout="wide")
st.title("🏥 Cabinet Medical")

menu = st.sidebar.selectbox(
    "Meniu",
    ["📅 Calendar programări", "➕ Programare nouă", "👨‍⚕️ Medici", "🧑 Pacienți", "📋 Toate programările", "📂 Istoric"]
)


# ══════════════════════════════════════════════════════════════════════════════
# 📅 CALENDAR PROGRAMĂRI
# ══════════════════════════════════════════════════════════════════════════════
if menu == "📅 Calendar programări":
    st.header("Calendar programări")

    medici = get_medici()
    if not medici:
        st.warning("Nu există medici înregistrați. Adaugă mai întâi un medic.")
        st.stop()

    col_med, col_data = st.columns(2)
    with col_med:
        medic_options = {f"{n} — {s}": mid for mid, n, s in medici}
        medic_selectat = st.selectbox("Medic", list(medic_options.keys()))
        medic_id = medic_options[medic_selectat]

    with col_data:
        data_selectata = st.date_input("Data", value=date.today())

    # Navigare săptămână
    col_prev, col_week, col_next = st.columns([1, 6, 1])
    with col_prev:
        if st.button("◀ Zi anterioară"):
            data_selectata = data_selectata - timedelta(days=1)
    with col_next:
        if st.button("Zi următoare ▶"):
            data_selectata = data_selectata + timedelta(days=1)

    st.markdown(f"### 📆 {data_selectata.strftime('%A, %d %B %Y')}")
    st.divider()

    programari = get_programari_by_medic_data(medic_id, data_selectata)
    prog_by_ora = {p[2]: p for p in programari}

    # Grid ore
    for ora in ORE:
        col_ora, col_info, col_actiuni = st.columns([1, 5, 2])
        col_ora.markdown(f"**{ora}**")

        if ora in prog_by_ora:
            prog = prog_by_ora[ora]
            prog_id, pacient_nume, _, motiv, status = prog
            emoji = STATUS_COLORS.get(status, "🔵")
            col_info.markdown(f"{emoji} **{pacient_nume}** &nbsp;|&nbsp; _{motiv or 'fără motiv'}_  &nbsp;`{status}`")

            with col_actiuni:
                c1, c2, c3 = st.columns(3)
                new_status = c1.selectbox(
                    "", ["Programat", "Confirmat", "Anulat", "Finalizat"],
                    index=["Programat", "Confirmat", "Anulat", "Finalizat"].index(status),
                    key=f"status_{prog_id}",
                    label_visibility="collapsed"
                )
                if new_status != status:
                    update_status_programare(prog_id, new_status)
                    st.rerun()
                if c2.button("🗑", key=f"del_{prog_id}", help="Șterge"):
                    delete_programare(prog_id)
                    st.rerun()
        else:
            col_info.markdown("<span style='color:#aaa'>— liber —</span>", unsafe_allow_html=True)

        st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# ➕ PROGRAMARE NOUĂ
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "➕ Programare nouă":
    st.header("Programare nouă")

    medici = get_medici()
    pacienti = get_pacienti()

    if not medici:
        st.warning("Adaugă mai întâi un medic.")
        st.stop()
    if not pacienti:
        st.warning("Adaugă mai întâi un pacient.")
        st.stop()

    with st.form("form_programare", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            medic_options = {f"{n} — {s}": mid for mid, n, s in medici}
            medic_sel = st.selectbox("Medic", list(medic_options.keys()))
            data = st.date_input("Data", min_value=date.today())
        with col2:
            pacient_options = {f"{n} (tel: {t or '-'})": pid for pid, n, t, *_ in pacienti}
            pacient_sel = st.selectbox("Pacient", list(pacient_options.keys()))
            ora = st.selectbox("Ora", ORE)

        motiv = st.text_input("Motiv consultație (opțional)")
        submitted = st.form_submit_button("Salvează programare", type="primary")

        if submitted:
            mid = medic_options[medic_sel]
            pid = pacient_options[pacient_sel]
            if is_slot_ocupat(mid, data, ora):
                st.error(f"Slotul {ora} este deja ocupat pentru acest medic!")
            else:
                add_programare(pid, mid, data, ora, motiv)
                st.success(f"Programare salvată: {pacient_sel.split('(')[0].strip()} la {ora} pe {data}")


# ══════════════════════════════════════════════════════════════════════════════
# 👨‍⚕️ MEDICI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "👨‍⚕️ Medici":
    st.header("Medici")

    with st.form("form_medic", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nume = st.text_input("Nume medic")
        with col2:
            specialitate = st.text_input("Specialitate")
        if st.form_submit_button("Adaugă medic", type="primary"):
            if nume.strip() and specialitate.strip():
                add_medic(nume.strip(), specialitate.strip())
                st.success(f"Dr. {nume} adăugat!")
            else:
                st.warning("Completați toate câmpurile.")

    st.subheader("Lista medici")
    medici = get_medici()
    if medici:
        for mid, mnume, mspec in medici:
            col1, col2, col3 = st.columns([3, 3, 1])
            col1.write(f"**Dr. {mnume}**")
            col2.write(f"_{mspec}_")
            if col3.button("🗑 Șterge", key=f"del_med_{mid}"):
                delete_medic(mid)
                st.rerun()
    else:
        st.info("Nu există medici înregistrați.")


# ══════════════════════════════════════════════════════════════════════════════
# 🧑 PACIENȚI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🧑 Pacienți":
    st.header("Pacienți")

    with st.form("form_pacient", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            nume = st.text_input("Nume pacient")
        with col2:
            telefon = st.text_input("Telefon")
        with col3:
            email = st.text_input("Email")
        if st.form_submit_button("Adaugă pacient", type="primary"):
            if nume.strip():
                add_pacient(nume.strip(), telefon.strip(), email.strip())
                st.success(f"Pacientul {nume} a fost adăugat!")
            else:
                st.warning("Introduceți numele pacientului.")

    st.subheader("Lista pacienți")
    pacienti = get_pacienti()
    if pacienti:
        df = pd.DataFrame(pacienti, columns=["ID", "Nume", "Telefon", "Email"])
        df = df.set_index("ID")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nu există pacienți înregistrați.")


# ══════════════════════════════════════════════════════════════════════════════
# 📋 TOATE PROGRAMĂRILE
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📋 Toate programările":
    st.header("Toate programările")

    programari = get_all_programari()
    if not programari:
        st.info("Nu există programări.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        medici_filter = ["Toți"] + list({r[2] for r in programari})
        medic_f = st.selectbox("Filtrează medic", medici_filter)
    with col2:
        status_filter = ["Toate", "Programat", "Confirmat", "Anulat", "Finalizat"]
        status_f = st.selectbox("Filtrează status", status_filter)

    rows = programari
    if medic_f != "Toți":
        rows = [r for r in rows if r[2] == medic_f]
    if status_f != "Toate":
        rows = [r for r in rows if r[7] == status_f]

    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Pacient", "Medic", "Specialitate", "Data", "Ora", "Motiv", "Status"])
        df["Status"] = df["Status"].map(lambda s: f"{STATUS_COLORS.get(s, '')} {s}")
        df = df.set_index("ID")
        st.dataframe(df, use_container_width=True)
        st.caption(f"Total: {len(rows)} programări")
    else:
        st.info("Nicio programare găsită cu filtrele selectate.")


# ══════════════════════════════════════════════════════════════════════════════
# 📂 ISTORIC
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📂 Istoric":
    st.header("Istoric consultații")

    medici = get_medici()
    pacienti = get_pacienti()

    with st.expander("➕ Adaugă consultație"):
        if not medici or not pacienti:
            st.warning("Este necesar cel puțin un medic și un pacient.")
        else:
            with st.form("form_istoric", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    medic_options = {f"{n} — {s}": mid for mid, n, s in medici}
                    medic_sel = st.selectbox("Medic", list(medic_options.keys()))
                    data = st.date_input("Data consultației")
                with col2:
                    pacient_options = {n: pid for pid, n, *_ in pacienti}
                    pacient_sel = st.selectbox("Pacient", list(pacient_options.keys()))

                diagnostic = st.text_input("Diagnostic *")
                tratament = st.text_area("Tratament")
                observatii = st.text_area("Observații")

                if st.form_submit_button("Salvează consultație", type="primary"):
                    if diagnostic.strip():
                        add_istoric(
                            pacient_options[pacient_sel],
                            medic_options[medic_sel],
                            data, diagnostic.strip(),
                            tratament.strip(), observatii.strip()
                        )
                        st.success("Consultație salvată!")
                    else:
                        st.warning("Diagnosticul este obligatoriu.")

    st.subheader("Căutare")
    col1, col2 = st.columns(2)
    with col1:
        pacient_filter_options = {"Toți pacienții": None} | {n: pid for pid, n, *_ in pacienti}
        pacient_f = st.selectbox("Pacient", list(pacient_filter_options.keys()))
    with col2:
        medic_filter_options = {"Toți medicii": None} | {f"{n} — {s}": mid for mid, n, s in medici}
        medic_f = st.selectbox("Medic", list(medic_filter_options.keys()))

    consultații = get_istoric(
        pacient_id=pacient_filter_options[pacient_f],
        medic_id=medic_filter_options[medic_f]
    )

    if consultații:
        for row in consultații:
            _, pac, med, spec, dat, diag, trat, obs = row
            with st.container(border=True):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Pacient:** {pac}")
                c2.markdown(f"**Medic:** Dr. {med} _{spec}_")
                st.markdown(f"**Data:** {dat} &nbsp;|&nbsp; **Diagnostic:** {diag}")
                if trat:
                    st.markdown(f"**Tratament:** {trat}")
                if obs:
                    st.markdown(f"**Observații:** {obs}")
        st.caption(f"Total: {len(consultații)} consultații")
    else:
        st.info("Nu există consultații pentru filtrele selectate.")
