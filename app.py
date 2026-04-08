import streamlit as st
import pandas as pd
import io
from datetime import date, datetime, timedelta
from database import (
    create_tables,
    verify_user, add_utilizator, get_utilizatori, delete_utilizator, change_password,
    add_medic, get_medici, delete_medic,
    add_pacient, get_pacienti, search_pacienti, delete_pacient,
    add_programare, get_programari_by_medic_data, get_all_programari,
    get_programari_azi, get_stats, get_stats_per_medic,
    update_status_programare, delete_programare, is_slot_ocupat,
    add_istoric, get_istoric,
    MEDIC_COLORS,
)

create_tables()

st.set_page_config(page_title="Cabinet Medical", layout="wide")

# ══════════════════════════════════════════════════════════════════════════════
# AUTENTIFICARE
# ══════════════════════════════════════════════════════════════════════════════
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🏥 Cabinet Medical")
    st.subheader("Autentificare")
    with st.form("login"):
        username = st.text_input("Utilizator")
        password = st.text_input("Parolă", type="password")
        if st.form_submit_button("Intră", type="primary"):
            user = verify_user(username, password)
            if user:
                st.session_state.user = {"id": user[0], "username": user[1], "rol": user[2]}
                st.rerun()
            else:
                st.error("Utilizator sau parolă greșite.")
    st.stop()

# ── Navigare top ─────────────────────────────────────────────────────────────
col_logo, col_user = st.columns([6, 1])
col_logo.title("🏥 Cabinet Medical")
with col_user:
    st.markdown(f"<div style='text-align:right;padding-top:16px'>👤 <b>{st.session_state.user['username']}</b></div>", unsafe_allow_html=True)
    if st.button("🚪 Ieșire", use_container_width=True):
        st.session_state.user = None
        st.rerun()

PAGINI = [
    "🏠 Dashboard",
    "📅 Calendar programări",
    "➕ Programare nouă",
    "👨‍⚕️ Medici",
    "🧑 Pacienți",
    "📋 Toate programările",
    "📂 Istoric",
    "📊 Statistici",
    "⚙️ Setări",
]
menu = st.radio("", PAGINI, horizontal=True, label_visibility="collapsed")
st.divider()

# ── Helpers ───────────────────────────────────────────────────────────────────
DURATE = [15, 20, 30, 45, 60, 90]
INTERVALE = [15, 20, 30]

def get_ore(interval_min=30):
    ore = []
    h, m = 8, 0
    while h < 19:
        ore.append(f"{h:02d}:{m:02d}")
        m += interval_min
        if m >= 60:
            h += m // 60
            m = m % 60
    return ore

STATUS_COLORS = {
    "Programat": "🔵",
    "Confirmat":  "🟢",
    "Anulat":     "🔴",
    "Finalizat":  "⚫",
}

def calc_varsta(data_nasterii_str):
    if not data_nasterii_str:
        return ""
    try:
        dn = datetime.strptime(data_nasterii_str, "%Y-%m-%d").date()
        ani = (date.today() - dn).days // 365
        return f"{ani} ani"
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if menu == "🏠 Dashboard":
    st.title("🏥 Cabinet Medical — Dashboard")
    st.markdown(f"**{date.today().strftime('%A, %d %B %Y')}**")
    st.divider()

    stats = get_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 Pacienți total", stats["total_pacienti"])
    c2.metric("📅 Programări azi", stats["programari_azi"])
    c3.metric("📆 Programări luna", stats["programari_luna"])
    c4.metric("❌ Anulate azi", stats["anulate_azi"])

    st.divider()
    st.subheader("📋 Programări de azi")

    azi_prog = get_programari_azi()
    if azi_prog:
        for row in azi_prog:
            _, pac, med, ora, status, motiv = row
            emoji = STATUS_COLORS.get(status, "🔵")
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.markdown(f"**{ora}** — {pac}")
                col2.markdown(f"Dr. {med}")
                col3.markdown(f"{emoji} {status}")
    else:
        st.info("Nu există programări pentru azi.")


# ══════════════════════════════════════════════════════════════════════════════
# 📅 CALENDAR PROGRAMĂRI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📅 Calendar programări":
    st.header("Calendar programări")

    medici = get_medici()
    if not medici:
        st.warning("Nu există medici înregistrați. Adaugă mai întâi un medic.")
        st.stop()

    col_med, col_data = st.columns(2)
    with col_med:
        medic_options = {f"{n} — {s}": (mid, c, iv) for mid, n, s, c, iv in medici}
        medic_selectat = st.selectbox("Medic", list(medic_options.keys()))
        medic_id, medic_culoare, medic_interval = medic_options.get(medic_selectat, (None, "#3498db", 30))
        ORE_MEDIC = get_ore(medic_interval)

    with col_data:
        data_selectata = st.date_input("Data", value=date.today())

    col_prev, _, col_next = st.columns([1, 6, 1])
    with col_prev:
        if st.button("◀ Zi anterioară"):
            data_selectata = data_selectata - timedelta(days=1)
    with col_next:
        if st.button("Zi următoare ▶"):
            data_selectata = data_selectata + timedelta(days=1)

    st.markdown(f"### 📆 {data_selectata.strftime('%A, %d %B %Y')}")
    st.divider()

    if not medic_id:
        st.stop()

    programari = get_programari_by_medic_data(medic_id, data_selectata)
    prog_by_ora = {p[2]: p for p in programari}

    ocupate = sum(1 for o in ORE_MEDIC if o in prog_by_ora)
    libere = len(ORE_MEDIC) - ocupate
    st.caption(f"🟢 {libere} sloturi libere &nbsp;|&nbsp; 🔵 {ocupate} ocupate &nbsp;|&nbsp; ⏱ interval {medic_interval} min")

    for ora in ORE_MEDIC:
        col_ora, col_info, col_actiuni = st.columns([1, 5, 3])
        col_ora.markdown(f"**{ora}**")

        if ora in prog_by_ora:
            prog = prog_by_ora[ora]
            prog_id, pacient_nume, _, motiv, status, durata, telefon = prog
            emoji = STATUS_COLORS.get(status, "🔵")

            bg = medic_culoare + "22"
            col_info.markdown(
                f"<div style='background:{bg};padding:6px;border-radius:6px;border-left:4px solid {medic_culoare}'>"
                f"{emoji} <b>{pacient_nume}</b> &nbsp;·&nbsp; {durata} min"
                f"{'&nbsp;·&nbsp;' + motiv if motiv else ''}"
                f"{'&nbsp;·&nbsp;📞 ' + telefon if telefon else ''}"
                f"</div>",
                unsafe_allow_html=True
            )

            with col_actiuni:
                c1, c2 = st.columns([3, 1])
                new_status = c1.selectbox(
                    "", ["Programat", "Confirmat", "Anulat", "Finalizat"],
                    index=["Programat", "Confirmat", "Anulat", "Finalizat"].index(status),
                    key=f"status_{prog_id}",
                    label_visibility="collapsed"
                )
                if new_status != status:
                    if new_status == "Anulat":
                        st.session_state[f"confirm_anulare_{prog_id}"] = True
                    else:
                        update_status_programare(prog_id, new_status)
                        st.rerun()

                if st.session_state.get(f"confirm_anulare_{prog_id}"):
                    nota = st.text_input("Motiv anulare", key=f"nota_{prog_id}")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Confirmă", key=f"ok_anulare_{prog_id}"):
                        update_status_programare(prog_id, "Anulat", nota)
                        del st.session_state[f"confirm_anulare_{prog_id}"]
                        st.rerun()
                    if cc2.button("↩ Renunță", key=f"cancel_anulare_{prog_id}"):
                        del st.session_state[f"confirm_anulare_{prog_id}"]
                        st.rerun()

                if c2.button("🗑", key=f"del_{prog_id}", help="Șterge"):
                    st.session_state[f"confirm_del_{prog_id}"] = True

                if st.session_state.get(f"confirm_del_{prog_id}"):
                    st.warning(f"Ștergi programarea lui {pacient_nume}?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Da, șterge", key=f"ok_del_{prog_id}"):
                        delete_programare(prog_id)
                        del st.session_state[f"confirm_del_{prog_id}"]
                        st.rerun()
                    if cc2.button("↩ Anulează", key=f"cancel_del_{prog_id}"):
                        del st.session_state[f"confirm_del_{prog_id}"]
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
    if not medici:
        st.warning("Adaugă mai întâi un medic.")
        st.stop()

    # ── Pacient: caută sau adaugă nou ─────────────────────────────────────────
    pacient_nou = st.toggle("➕ Pacient nou (nu există în listă)")

    pid_selectat = None

    if pacient_nou:
        with st.container(border=True):
            st.markdown("**Date pacient nou**")
            c1, c2, c3 = st.columns(3)
            with c1:
                np_nume = st.text_input("Nume *", key="np_nume")
                np_tel = st.text_input("Telefon", key="np_tel")
            with c2:
                np_email = st.text_input("Email", key="np_email")
                np_dn = st.date_input("Data nașterii", value=None,
                                      min_value=date(1900,1,1), max_value=date.today(),
                                      key="np_dn")
    else:
        toti_pacientii = get_pacienti()
        if toti_pacientii:
            # Format: "Nume · Telefon" — utilizatorul poate tasta direct în selectbox pentru filtrare
            pacient_options = {
                f"{n}{'  ·  📞 ' + t if t else ''}": pid
                for pid, n, t, *_ in toti_pacientii
            }
            st.caption("💡 Tastează direct în câmp pentru a filtra după nume sau telefon")
            pacient_sel = st.selectbox(
                "🔍 Selectează pacient",
                list(pacient_options.keys()),
                index=0,
                placeholder="Scrie pentru a căuta..."
            )
            pid_selectat = pacient_options.get(pacient_sel)
            # Afișează detalii pacient selectat
            if pid_selectat:
                pac_info = next((p for p in toti_pacientii if p[0] == pid_selectat), None)
                if pac_info:
                    _, pn, pt, pe, pdn = pac_info
                    varsta = calc_varsta(pdn)
                    st.info(
                        f"**{pn}**"
                        + (f"  |  📞 {pt}" if pt else "")
                        + (f"  |  ✉️ {pe}" if pe else "")
                        + (f"  |  🎂 {varsta}" if varsta else "")
                    )
        else:
            st.info("Niciun pacient găsit. Activează 'Pacient nou' pentru a adăuga.")

    st.divider()

    # ── Detalii programare ────────────────────────────────────────────────────
    with st.form("form_programare", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            medic_options = {f"{n} — {s}": (mid, iv) for mid, n, s, c, iv in medici}
            medic_sel = st.selectbox("Medic", list(medic_options.keys()))
            mid_form, interval_form = medic_options.get(medic_sel, (None, 30))
            ore_form = get_ore(interval_form)
            data = st.date_input("Data", min_value=date.today())
            durata = st.selectbox("Durată (minute)", DURATE,
                                  index=DURATE.index(interval_form) if interval_form in DURATE else 2)
        with col2:
            ora = st.selectbox("Ora", ore_form)
            motiv = st.text_input("Motiv consultație (opțional)")

        submitted = st.form_submit_button("💾 Salvează programare", type="primary")

        if submitted:
            mid, _ = medic_options[medic_sel]

            # Dacă e pacient nou, îl adăugăm automat
            if pacient_nou:
                if not st.session_state.get("np_nume", "").strip():
                    st.error("Introduceți numele pacientului.")
                    st.stop()
                add_pacient(
                    st.session_state["np_nume"].strip(),
                    st.session_state.get("np_tel", "").strip(),
                    st.session_state.get("np_email", "").strip(),
                    str(st.session_state["np_dn"]) if st.session_state.get("np_dn") else ""
                )
                pacienti_noi = search_pacienti(st.session_state["np_nume"].strip())
                pid_selectat = pacienti_noi[0][0] if pacienti_noi else None

            if not pid_selectat:
                st.error("Selectați sau adăugați un pacient.")
            elif is_slot_ocupat(mid, data, ora):
                st.error(f"Slotul {ora} este deja ocupat pentru acest medic!")
            else:
                add_programare(pid_selectat, mid, data, ora, motiv, durata)
                st.success(f"✅ Programare salvată pentru {ora} pe {data}")


# ══════════════════════════════════════════════════════════════════════════════
# 👨‍⚕️ MEDICI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "👨‍⚕️ Medici":
    st.header("Medici")

    with st.form("form_medic", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([3, 3, 1, 1])
        with col1:
            nume = st.text_input("Nume medic")
        with col2:
            specialitate = st.text_input("Specialitate")
        with col3:
            culoare = st.color_picker("Culoare", "#3498db")
        with col4:
            interval = st.selectbox("Interval", INTERVALE, index=2, format_func=lambda x: f"{x} min")
        if st.form_submit_button("Adaugă medic", type="primary"):
            if nume.strip() and specialitate.strip():
                add_medic(nume.strip(), specialitate.strip(), culoare, interval)
                st.success(f"Dr. {nume} adăugat! (interval {interval} min)")
                st.rerun()
            else:
                st.warning("Completați toate câmpurile.")

    st.subheader("Lista medici")
    medici = get_medici()
    if medici:
        for mid, mnume, mspec, mculoare, minterval in medici:
            col1, col2, col3, col4, col5 = st.columns([3, 3, 1, 1, 1])
            col1.markdown(
                f"<span style='color:{mculoare}'>■</span> **Dr. {mnume}**",
                unsafe_allow_html=True
            )
            col2.write(f"_{mspec}_")
            col3.write(f"⏱ {minterval} min")
            col4.markdown(f"<div style='width:24px;height:24px;background:{mculoare};border-radius:4px'></div>", unsafe_allow_html=True)
            if col5.button("🗑", key=f"del_med_{mid}", help="Șterge"):
                st.session_state[f"confirm_del_med_{mid}"] = True

            if st.session_state.get(f"confirm_del_med_{mid}"):
                st.warning(f"Ștergi Dr. {mnume}? Toate programările asociate vor fi pierdute.")
                cc1, cc2 = st.columns(2)
                if cc1.button("✅ Da", key=f"ok_med_{mid}"):
                    delete_medic(mid)
                    del st.session_state[f"confirm_del_med_{mid}"]
                    st.rerun()
                if cc2.button("↩ Nu", key=f"cancel_med_{mid}"):
                    del st.session_state[f"confirm_del_med_{mid}"]
                    st.rerun()
    else:
        st.info("Nu există medici înregistrați.")


# ══════════════════════════════════════════════════════════════════════════════
# 🧑 PACIENȚI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "🧑 Pacienți":
    st.header("Pacienți")

    with st.form("form_pacient", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nume = st.text_input("Nume pacient *")
            telefon = st.text_input("Telefon")
        with col2:
            email = st.text_input("Email")
            data_nasterii = st.date_input(
                "Data nașterii",
                value=None,
                min_value=date(1900, 1, 1),
                max_value=date.today()
            )
        if st.form_submit_button("Adaugă pacient", type="primary"):
            if nume.strip():
                add_pacient(
                    nume.strip(), telefon.strip(), email.strip(),
                    str(data_nasterii) if data_nasterii else ""
                )
                st.success(f"Pacientul {nume} a fost adăugat!")
                st.rerun()
            else:
                st.warning("Introduceți numele pacientului.")

    st.subheader("Căutare pacienți")
    cautare = st.text_input("Caută după nume", placeholder="minim 2 caractere")
    pacienti = search_pacienti(cautare) if len(cautare) >= 2 else get_pacienti()

    if pacienti:
        for pid, pnume, ptel, pemail, pdn in pacienti:
            varsta = calc_varsta(pdn)
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.markdown(f"**{pnume}**" + (f"  ·  {varsta}" if varsta else ""))
                c2.write(f"📞 {ptel or '—'}")
                c3.write(f"✉️ {pemail or '—'}")
                if c4.button("🗑", key=f"del_pac_{pid}"):
                    st.session_state[f"confirm_del_pac_{pid}"] = True

                if st.session_state.get(f"confirm_del_pac_{pid}"):
                    st.warning(f"Ștergi pacientul {pnume}?")
                    cc1, cc2 = st.columns(2)
                    if cc1.button("✅ Da", key=f"ok_pac_{pid}"):
                        delete_pacient(pid)
                        del st.session_state[f"confirm_del_pac_{pid}"]
                        st.rerun()
                    if cc2.button("↩ Nu", key=f"cancel_pac_{pid}"):
                        del st.session_state[f"confirm_del_pac_{pid}"]
                        st.rerun()
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

    col1, col2, col3 = st.columns(3)
    with col1:
        medici_filter = ["Toți"] + sorted({r[2] for r in programari})
        medic_f = st.selectbox("Medic", medici_filter)
    with col2:
        status_filter = ["Toate", "Programat", "Confirmat", "Anulat", "Finalizat"]
        status_f = st.selectbox("Status", status_filter)
    with col3:
        data_f = st.date_input("De la data", value=None)

    rows = programari
    if medic_f != "Toți":
        rows = [r for r in rows if r[2] == medic_f]
    if status_f != "Toate":
        rows = [r for r in rows if r[7] == status_f]
    if data_f:
        rows = [r for r in rows if r[4] >= str(data_f)]

    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Pacient", "Medic", "Specialitate", "Data", "Ora", "Motiv", "Status", "Durata"])
        df["Status"] = df["Status"].map(lambda s: f"{STATUS_COLORS.get(s, '')} {s}")
        df["Durata"] = df["Durata"].map(lambda d: f"{d} min")
        df = df.set_index("ID")
        st.dataframe(df, use_container_width=True)
        st.caption(f"Total: {len(rows)} programări")

        # Export Excel
        buffer = io.BytesIO()
        df_export = df.copy()
        df_export["Status"] = df_export["Status"].str.replace(r"[^\w\s]", "", regex=True).str.strip()
        df_export.to_excel(buffer, index=True)
        buffer.seek(0)
        st.download_button(
            "📥 Export Excel",
            data=buffer,
            file_name=f"programari_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
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
                    medic_options = {f"{n} — {s}": mid for mid, n, s, c, iv in medici}
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

    col1, col2 = st.columns(2)
    with col1:
        pacient_filter_options = {"Toți pacienții": None} | {n: pid for pid, n, *_ in pacienti}
        pacient_f = st.selectbox("Pacient", list(pacient_filter_options.keys()))
    with col2:
        medic_filter_options = {"Toți medicii": None} | {f"{n} — {s}": mid for mid, n, s, c, iv in medici}
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
                c2.markdown(f"**Medic:** Dr. {med} — _{spec}_")
                st.markdown(f"**Data:** {dat} &nbsp;|&nbsp; **Diagnostic:** {diag}")
                if trat:
                    st.markdown(f"**Tratament:** {trat}")
                if obs:
                    st.markdown(f"**Observații:** {obs}")
        st.caption(f"Total: {len(consultații)} consultații")
    else:
        st.info("Nu există consultații pentru filtrele selectate.")


# ══════════════════════════════════════════════════════════════════════════════
# 📊 STATISTICI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "📊 Statistici":
    st.header("Statistici")

    stats = get_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 Pacienți", stats["total_pacienti"])
    c2.metric("👨‍⚕️ Medici", stats["total_medici"])
    c3.metric("📅 Programări azi", stats["programari_azi"])
    c4.metric("📆 Programări luna", stats["programari_luna"])

    st.divider()
    st.subheader("Per medic")

    stats_medici = get_stats_per_medic()
    if stats_medici:
        df = pd.DataFrame(
            stats_medici,
            columns=["Medic", "Specialitate", "Total programări", "Finalizate", "Anulate"]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.bar_chart(df.set_index("Medic")["Total programări"])
    else:
        st.info("Nu există date de afișat.")


# ══════════════════════════════════════════════════════════════════════════════
# ⚙️ SETĂRI
# ══════════════════════════════════════════════════════════════════════════════
elif menu == "⚙️ Setări":
    st.header("Setări")

    if st.session_state.user["rol"] != "admin":
        st.warning("Doar administratorii pot accesa setările.")
        st.stop()

    st.subheader("Utilizatori")
    with st.form("form_utilizator", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_user = st.text_input("Username")
        with col2:
            new_pass = st.text_input("Parolă", type="password")
        with col3:
            new_rol = st.selectbox("Rol", ["receptionist", "admin"])
        if st.form_submit_button("Adaugă utilizator", type="primary"):
            if new_user.strip() and new_pass.strip():
                try:
                    add_utilizator(new_user.strip(), new_pass, new_rol)
                    st.success(f"Utilizatorul {new_user} adăugat!")
                    st.rerun()
                except Exception:
                    st.error("Username-ul există deja.")
            else:
                st.warning("Completați toate câmpurile.")

    utilizatori = get_utilizatori()
    for uid, uname, urol in utilizatori:
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.write(f"**{uname}**")
        col2.write(f"`{urol}`")
        if uname != "admin":
            if col3.button("🗑", key=f"del_u_{uid}"):
                delete_utilizator(uid)
                st.rerun()

    st.divider()
    st.subheader("Schimbă parola")
    with st.form("form_parola", clear_on_submit=True):
        old_pass = st.text_input("Parola actuală", type="password")
        new_pass1 = st.text_input("Parola nouă", type="password")
        new_pass2 = st.text_input("Confirmă parola nouă", type="password")
        if st.form_submit_button("Schimbă parola", type="primary"):
            user = verify_user(st.session_state.user["username"], old_pass)
            if not user:
                st.error("Parola actuală este greșită.")
            elif new_pass1 != new_pass2:
                st.error("Parolele noi nu coincid.")
            elif len(new_pass1) < 6:
                st.error("Parola trebuie să aibă minim 6 caractere.")
            else:
                change_password(st.session_state.user["username"], new_pass1)
                st.success("Parola a fost schimbată!")
