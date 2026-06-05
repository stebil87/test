import streamlit as st
from datetime import date, datetime, timedelta
import base64, io, zipfile, json
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from pdf_generator import genera_modulo1, genera_modulo1a, genera_modulo1908
from storage import (salva_compilazione, lista_compilazioni, get_pdf,
                     get_allegato, aggiorna_compilazione, elimina_compilazione)
import config

st.set_page_config(
    page_title="1908 Group SA",
    page_icon="1908_Group_Black.png",
    layout="centered"
)

st.markdown("""
<style>
[data-testid="stToolbar"] { display: none !important; }
[data-testid="manage-app-button"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
button[kind="secondary"][data-testid="manage-app-button"] { display: none !important; }
div[data-testid="stBottom"] { display: none !important; }
footer { display: none !important; }
#GithubIcon { visibility: hidden; }
a[href*="github"] { display: none !important; }
.stDeployButton { display: none !important; }
.honeypot { display: none !important; }
.stButton>button {
    width:100%; background:#1a1a2e; color:white;
    border-radius:8px; padding:12px; font-size:15px; margin-top:6px;
}
.sez {
    background:#1a1a2e; color:white;
    padding:7px 14px; border-radius:6px;
    margin:18px 0 8px 0; font-weight:bold; font-size:14px;
}
h1,h2,h3 { color:#1a1a2e; }
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
    function disableAutocomplete() {
        document.querySelectorAll('input').forEach(function(input) {
            input.setAttribute('autocomplete', 'new-password');
        });
    }
    disableAutocomplete();
    new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(n) {
                if (n.querySelectorAll) {
                    n.querySelectorAll('input').forEach(function(i) {
                        i.setAttribute('autocomplete', 'new-password');
                    });
                }
            });
        });
    }).observe(document.body, { childList: true, subtree: true });
});
</script>
""", unsafe_allow_html=True)

try:
    st.image("1908_Group_Black.png", width=180)
except Exception:
    st.markdown("**1908 Group SA**")

def sez(t): st.markdown(f'<div class="sez">{t}</div>', unsafe_allow_html=True)

def bottone_indietro(step_precedente):
    if st.button("Indietro"):
        st.session_state.step = step_precedente
        st.rerun()

defaults = {
    "step": 0, "dati": {}, "vf": None, "manager": False,
    "mostra_login": False, "tipo_lavoratore": None,
    "login_tentativi": 0, "login_bloccato_fino": None,
    "submit_count": 0, "submit_prima": None,
    "conferma_elimina": {},
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def check_rate_limit():
    ora = datetime.now()
    if st.session_state.submit_prima is None:
        st.session_state.submit_prima = ora
        st.session_state.submit_count = 0
    diff = (ora - st.session_state.submit_prima).seconds
    if diff > 3600:
        st.session_state.submit_prima = ora
        st.session_state.submit_count = 0
    return st.session_state.submit_count < 10

PERMESSI_FRONTALIERE = ["G (Frontaliere)", "Solo notifica",
                        "No, svizzero/a", "Nessun permesso"]
PERMESSI_DIMORANTE   = ["B (Dimora)", "L (Dimora breve durata)",
                        "No, svizzero/a", "Nessun permesso"]
PERMESSI_CON_UPLOAD  = {"G (Frontaliere)", "Solo notifica",
                        "B (Dimora)", "L (Dimora breve durata)"}
PERMESSI_CON_DATE    = {"G (Frontaliere)", "Solo notifica",
                        "B (Dimora)", "L (Dimora breve durata)"}

# ════════════════════════════════════════════════════════
# PANNELLO MANAGER
# ════════════════════════════════════════════════════════
if st.session_state.manager:
    st.title("Pannello Manager – 1908 Group SA")
    st.markdown("---")

    if st.button("Esci dal pannello manager"):
        st.session_state.manager = False
        st.session_state.mostra_login = False
        st.rerun()

    rows = lista_compilazioni()
    if not rows:
        st.info("Nessuna compilazione ricevuta finora.")
    else:
        st.subheader(f"Compilazioni ricevute ({len(rows)})")
        for row in rows:
            rid        = row["id"]
            nome       = row["nome"]
            cognome    = row["cognome"]
            data_ora   = row["data_ora"][:16].replace("T", " ")
            percorso   = row["percorso"]
            vf         = row["vf"]
            modificato = row.get("modificato", False)
            dati_json  = row.get("dati_json", "{}")
            doc_paths  = row.get("doc_identita_paths", []) or []
            perm_paths = row.get("permesso_paths", []) or []

            label = f"{nome} {cognome}  —  {data_ora}"
            if modificato:
                label += "  (modificato)"

            with st.expander(label):
                tab1, tab2, tab3, tab4 = st.tabs(
                    ["Documenti", "Allegati", "Modifica", "Elimina"])

                with tab1:
                    moduli_orig = ["Modulo1_ImposteAllaFonte.pdf",
                                   "Modulo1908_DatiPersonali.pdf"]
                    if vf:
                        moduli_orig.insert(1, "Modulo1A_VecchioFrontaliere.pdf")

                    st.markdown("**Versione originale:**")
                    for nome_file in moduli_orig:
                        pb = get_pdf(percorso, nome_file)
                        if pb:
                            st.download_button(
                                label=f"Scarica {nome_file}",
                                data=pb,
                                file_name=f"{cognome}_{nome}_{nome_file}",
                                mime="application/pdf",
                                key=f"{rid}_orig_{nome_file}"
                            )

                    if modificato:
                        st.markdown("**Versione modificata:**")
                        for nome_file in moduli_orig:
                            pb2 = get_pdf(percorso, f"mod_{nome_file}")
                            if pb2:
                                st.download_button(
                                    label=f"Scarica mod_{nome_file}",
                                    data=pb2,
                                    file_name=f"{cognome}_{nome}_mod_{nome_file}",
                                    mime="application/pdf",
                                    key=f"{rid}_mod_{nome_file}"
                                )

                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w") as zf:
                        for nome_file in moduli_orig:
                            pb = get_pdf(percorso, nome_file)
                            if pb:
                                zf.writestr(f"originale/{cognome}_{nome}_{nome_file}", pb)
                            if modificato:
                                pb2 = get_pdf(percorso, f"mod_{nome_file}")
                                if pb2:
                                    zf.writestr(
                                        f"modificato/{cognome}_{nome}_mod_{nome_file}", pb2)
                    zip_buf.seek(0)
                    st.download_button(
                        label="Scarica tutti (ZIP)",
                        data=zip_buf,
                        file_name=f"{cognome}_{nome}_documenti.zip",
                        mime="application/zip",
                        key=f"{rid}_zip"
                    )

                with tab2:
                    if doc_paths:
                        st.markdown("**Documento d'identita:**")
                        for i, path in enumerate(doc_paths):
                            allegato = get_allegato(path)
                            if allegato:
                                ext = path.split(".")[-1].lower()
                                mime = "application/pdf" if ext == "pdf" else f"image/{ext}"
                                st.download_button(
                                    label=f"Identita {i+1}",
                                    data=allegato,
                                    file_name=f"{cognome}_{nome}_identita_{i+1}.{ext}",
                                    mime=mime,
                                    key=f"{rid}_id_{i}"
                                )
                    else:
                        st.info("Nessun documento d'identita allegato.")

                    if perm_paths:
                        st.markdown("**Permesso:**")
                        for i, path in enumerate(perm_paths):
                            allegato = get_allegato(path)
                            if allegato:
                                ext = path.split(".")[-1].lower()
                                mime = "application/pdf" if ext == "pdf" else f"image/{ext}"
                                st.download_button(
                                    label=f"Permesso {i+1}",
                                    data=allegato,
                                    file_name=f"{cognome}_{nome}_permesso_{i+1}.{ext}",
                                    mime=mime,
                                    key=f"{rid}_perm_{i}"
                                )
                    else:
                        st.info("Nessun permesso allegato.")

                with tab3:
                    try:
                        dati_attuali = json.loads(dati_json) if dati_json else {}
                    except Exception:
                        dati_attuali = {}

                    if not dati_attuali:
                        st.warning("Dati originali non disponibili.")
                    else:
                        with st.form(f"form_modifica_{rid}"):
                            st.markdown("**Modifica i dati e rigenera i PDF:**")
                            c1, c2 = st.columns(2)
                            with c1:
                                m_cognome         = st.text_input("Cognome", value=dati_attuali.get("cognome",""))
                                m_nome            = st.text_input("Nome", value=dati_attuali.get("nome",""))
                                m_data_nascita    = st.text_input("Data di nascita", value=dati_attuali.get("data_nascita",""))
                                m_luogo_nascita   = st.text_input("Luogo di nascita", value=dati_attuali.get("luogo_nascita",""))
                                m_nazione_nascita = st.text_input("Nazione di nascita", value=dati_attuali.get("nazione_nascita",""))
                                m_codice_fiscale  = st.text_input("Codice fiscale", value=dati_attuali.get("codice_fiscale",""))
                                m_numero_avs      = st.text_input("Numero AVS", value=dati_attuali.get("numero_avs",""))
                                m_cellulare       = st.text_input("Cellulare", value=dati_attuali.get("cellulare",""))
                                m_email           = st.text_input("E-mail privata", value=dati_attuali.get("email_privata",""))
                            with c2:
                                m_via             = st.text_input("Via", value=dati_attuali.get("domicilio_via",""))
                                m_cap             = st.text_input("CAP", value=dati_attuali.get("domicilio_cap",""))
                                m_localita        = st.text_input("Localita", value=dati_attuali.get("domicilio_localita",""))
                                m_permesso        = st.text_input("Permesso", value=dati_attuali.get("permesso",""))
                                m_stato_civile    = st.text_input("Stato civile", value=dati_attuali.get("stato_civile",""))
                                m_qualifica       = st.text_input("Qualifica", value=dati_attuali.get("qualifica",""))
                                m_iban            = st.text_input("IBAN", value=dati_attuali.get("iban",""))
                                m_data_inizio     = st.text_input("Data inizio attivita", value=dati_attuali.get("data_inizio",""))
                            submit_mod = st.form_submit_button("Salva e rigenera PDF")

                        if submit_mod:
                            dati_modificati = dict(dati_attuali)
                            dati_modificati.update(dict(
                                cognome=m_cognome, nome=m_nome,
                                data_nascita=m_data_nascita,
                                luogo_nascita=m_luogo_nascita,
                                nazione_nascita=m_nazione_nascita,
                                codice_fiscale=m_codice_fiscale,
                                numero_avs=m_numero_avs,
                                cellulare=m_cellulare,
                                email_privata=m_email,
                                domicilio_via=m_via,
                                domicilio_cap=m_cap,
                                domicilio_localita=m_localita,
                                permesso=m_permesso,
                                stato_civile=m_stato_civile,
                                qualifica=m_qualifica,
                                iban=m_iban,
                                data_inizio=m_data_inizio,
                            ))
                            with st.spinner("Rigenerazione PDF in corso..."):
                                pdfs = {}
                                pdfs["Modulo1_ImposteAllaFonte.pdf"] = genera_modulo1(dati_modificati, "")
                                if vf:
                                    pdfs["Modulo1A_VecchioFrontaliere.pdf"] = genera_modulo1a(dati_modificati, "")
                                pdfs["Modulo1908_DatiPersonali.pdf"] = genera_modulo1908(dati_modificati, "")
                                errore = aggiorna_compilazione(rid, dati_modificati, pdfs, percorso)
                            if errore is None:
                                st.success("PDF rigenerati e salvati.")
                                st.rerun()
                            else:
                                st.error(f"Errore: {errore}")

                with tab4:
                    st.warning(f"Stai per eliminare la compilazione di **{nome} {cognome}** del {data_ora}. Questa azione e' irreversibile e cancellera' anche tutti i file allegati.")

                    conferma_key = f"conferma_{rid}"
                    if st.session_state.conferma_elimina.get(rid):
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Conferma eliminazione", key=f"conf_{rid}"):
                                errore = elimina_compilazione(rid, percorso)
                                if errore is None:
                                    st.session_state.conferma_elimina.pop(rid, None)
                                    st.success("Compilazione eliminata.")
                                    st.rerun()
                                else:
                                    st.error(f"Errore: {errore}")
                        with c2:
                            if st.button("Annulla", key=f"ann_{rid}"):
                                st.session_state.conferma_elimina.pop(rid, None)
                                st.rerun()
                    else:
                        if st.button("Elimina questa compilazione", key=f"eli_{rid}"):
                            st.session_state.conferma_elimina[rid] = True
                            st.rerun()

    st.stop()

# ── LOGIN MANAGER ──
if st.session_state.mostra_login and not st.session_state.manager:
    st.markdown("---")
    st.markdown("### Accesso Manager")
    bloccato = False
    if st.session_state.login_bloccato_fino:
        if datetime.now() < st.session_state.login_bloccato_fino:
            minuti = int((st.session_state.login_bloccato_fino -
                          datetime.now()).seconds / 60) + 1
            st.error(f"Troppi tentativi. Riprova tra {minuti} minuti.")
            bloccato = True
        else:
            st.session_state.login_tentativi = 0
            st.session_state.login_bloccato_fino = None

    if not bloccato:
        with st.form("form_login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Entra")
        if login_submit:
            if u == config.MANAGER_USERNAME and p == config.MANAGER_PASSWORD:
                st.session_state.manager = True
                st.session_state.login_tentativi = 0
                st.session_state.mostra_login = False
                st.rerun()
            else:
                st.session_state.login_tentativi += 1
                rimasti = 5 - st.session_state.login_tentativi
                if st.session_state.login_tentativi >= 5:
                    st.session_state.login_bloccato_fino = (
                        datetime.now() + timedelta(minutes=15))
                    st.error("Troppi tentativi. Bloccato per 15 minuti.")
                else:
                    st.error(f"Credenziali errate. Tentativi rimasti: {rimasti}")
    st.stop()

# ════════════════════════════════════════════════════════
# FORM DIPENDENTE
# ════════════════════════════════════════════════════════

if st.session_state.step == 0:
    st.header("Anagrafica del personale")
    st.markdown("Benvenuta/o. Avrai bisogno di circa 10 minuti.")
    st.divider()
    
    # Centra "Prima di iniziare" sopra i bottoni
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("<h3 style='padding-left: 80px;'>Prima di iniziare</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sono frontaliere", use_container_width=True, type="primary"):
            st.session_state.tipo_lavoratore = "frontaliere"
            st.session_state.step = 1
            st.rerun()
    with col2:
        if st.button("Sono dimorante", use_container_width=True, type="primary"):
            st.session_state.tipo_lavoratore = "dimorante"
            st.session_state.vf = False
            st.session_state.step = 2
            st.rerun()
    
    # Area Manager centrato separatamente
    st.divider()
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button("Area Manager", use_container_width=True, type="secondary"):
            st.session_state.mostra_login = True
            st.rerun()

elif st.session_state.step == 1:
    st.progress(0.05)
    bottone_indietro(0)
    st.markdown("### Hai lavorato in Svizzera prima del 18 luglio 2023?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Si, ho lavorato prima del 18/07/2023"):
            st.session_state.vf = True
            st.session_state.step = 2
            st.rerun()
    with c2:
        if st.button("No, non ho lavorato prima"):
            st.session_state.vf = False
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    tipo = st.session_state.tipo_lavoratore
    n_moduli = 3 if (tipo == "frontaliere" and st.session_state.vf) else 2
    st.info(f"Compilerai {n_moduli} formulari in questa sessione.")
    st.progress(0.15)
    bottone_indietro(1 if tipo == "frontaliere" else 0)

    permessi_lista = (PERMESSI_FRONTALIERE if tipo == "frontaliere"
                      else PERMESSI_DIMORANTE)

    with st.form("form_step2"):
        sez("Dati anagrafici")
        c1, c2 = st.columns(2)
        with c1:
            cognome         = st.text_input("Cognome *",
                                value=st.session_state.dati.get("cognome",""))
            data_nascita    = st.date_input("Data di nascita *",
                                min_value=date(1940,1,1),
                                max_value=date.today(),
                                format="DD/MM/YYYY")
            luogo_nascita   = st.text_input("Luogo di nascita *",
                                value=st.session_state.dati.get("luogo_nascita",""))
            nazione_nascita = st.text_input("Nazione di nascita *",
                                value=st.session_state.dati.get("nazione_nascita",""))
            numero_avs      = st.text_input("Numero AVS",
                                placeholder="756.XXXX.XXXX.XX",
                                value=st.session_state.dati.get("numero_avs",""))
        with c2:
            nome           = st.text_input("Nome *",
                                value=st.session_state.dati.get("nome",""))
            sesso          = st.selectbox("Sesso *", ["Maschile", "Femminile"])
            nazionalita    = st.text_input("Nazionalita *",
                                value=st.session_state.dati.get("nazionalita",""))
            codice_fiscale = st.text_input("Codice fiscale * (16 caratteri)",
                                max_chars=16,
                                value=st.session_state.dati.get("codice_fiscale",""))
            cellulare      = st.text_input("Cellulare *",
                                value=st.session_state.dati.get("cellulare",""))

        email_privata = st.text_input("E-mail privata *",
                            value=st.session_state.dati.get("email_privata",""))
        honeypot = st.text_input("Leave this empty", value="",
                                  key="honeypot", label_visibility="collapsed")

        sez("Domicilio / Residenza")
        c1, c2 = st.columns(2)
        with c1:
            domicilio_via      = st.text_input("Via e numero civico *",
                                    value=st.session_state.dati.get("domicilio_via",""))
            domicilio_cap      = st.text_input("CAP *",
                                    value=st.session_state.dati.get("domicilio_cap",""))
        with c2:
            domicilio_localita = st.text_input("Localita *",
                                    value=st.session_state.dati.get("domicilio_localita",""))
            domicilio_nazione  = st.selectbox("Nazione residenza *",
                ["Italia", "Italia (Comuni di Frontiera)",
                 "Germania", "Austria", "Francia", "Svizzera", "Altra"])

        sez("Permesso e stato civile")
        c1, c2 = st.columns(2)
        with c1:
            permesso = st.selectbox("Tipo di permesso *", permessi_lista)
            permesso_rilascio = permesso_scadenza = ""
            if permesso in PERMESSI_CON_DATE:
                permesso_rilascio = str(st.date_input(
                    "Data di rilascio permesso *",
                    value=None, max_value=date.today(),
                    format="DD/MM/YYYY"))
                permesso_scadenza = str(st.date_input(
                    "Data di scadenza permesso *",
                    value=None, max_value=date(2040,1,1),
                    format="DD/MM/YYYY"))
        with c2:
            stato_civile = st.selectbox("Stato civile *",
                ["Celibe/Nubile", "Coniugato/Partner registrato",
                 "Vedovo", "Separato/Separato di fatto", "Divorziato"])

        data_matrimonio = data_divorzio = ""
        if stato_civile == "Coniugato/Partner registrato":
            data_matrimonio = str(st.date_input("Data del matrimonio *",
                                   max_value=date.today(), format="DD/MM/YYYY"))
        if stato_civile in ["Divorziato", "Separato/Separato di fatto"]:
            data_divorzio = str(st.date_input("Data divorzio/separazione *",
                                 max_value=date.today(), format="DD/MM/YYYY"))

        frontaliere_con = rientro = indirizzo_settimanale = ""
        if permesso == "G (Frontaliere)":
            c1, c2 = st.columns(2)
            with c1:
                frontaliere_con = st.selectbox("Frontaliere con *",
                    ["Italia", "Italia (Comuni di Frontiera)",
                     "Germania", "Austria", "Francia"])
            with c2:
                rientro = st.selectbox("Rientro *",
                    ["Rientro giornaliero", "Rientro settimanale"])
            if rientro == "Rientro settimanale":
                indirizzo_settimanale = st.text_input(
                    "Indirizzo di residenza settimanale in Svizzera *",
                    value=st.session_state.dati.get("indirizzo_settimanale",""))

        convivenza = st.checkbox("Vive in regime di convivenza")
        autorita_parentale = ""
        reddito_maggiore = figli_convivenza = False
        if convivenza:
            autorita_parentale = st.selectbox("Autorita parentale?",
                ["Si", "Si congiunta", "No"])
            reddito_maggiore = st.checkbox(
                "Percepisce reddito maggiore del/la convivente?")
            figli_convivenza = st.checkbox("Figli a carico in convivenza?")

        patente   = st.checkbox("Patente di guida B")
        religione = st.text_input("Religione (opzionale)",
                        value=st.session_state.dati.get("religione",""))

        submitted2 = st.form_submit_button("Avanti")

    if submitted2:
        if honeypot:
            st.error("Errore di validazione. Riprova.")
            st.stop()
        errori = []
        if not cognome:            errori.append("Cognome")
        if not nome:               errori.append("Nome")
        if not luogo_nascita:      errori.append("Luogo di nascita")
        if not nazione_nascita:    errori.append("Nazione di nascita")
        if not nazionalita:        errori.append("Nazionalita")
        if not codice_fiscale:     errori.append("Codice fiscale")
        if not cellulare:          errori.append("Cellulare")
        if not email_privata:      errori.append("E-mail privata")
        if not domicilio_via:      errori.append("Via e numero civico")
        if not domicilio_cap:      errori.append("CAP")
        if not domicilio_localita: errori.append("Localita")
        if permesso in PERMESSI_CON_DATE:
            if not permesso_rilascio or permesso_rilascio == "None":
                errori.append("Data di rilascio permesso")
            if not permesso_scadenza or permesso_scadenza == "None":
                errori.append("Data di scadenza permesso")
        if rientro == "Rientro settimanale" and not indirizzo_settimanale:
            errori.append("Indirizzo settimanale in Svizzera")
        if errori:
            st.error("Campi obbligatori mancanti: **" + ", ".join(errori) + "**")
        else:
            st.session_state.dati.update(dict(
                cognome=cognome, nome=nome,
                data_nascita=str(data_nascita), sesso=sesso,
                luogo_nascita=luogo_nascita, nazione_nascita=nazione_nascita,
                nazionalita=nazionalita, codice_fiscale=codice_fiscale,
                numero_avs=numero_avs, cellulare=cellulare,
                email_privata=email_privata,
                domicilio_via=domicilio_via, domicilio_cap=domicilio_cap,
                domicilio_localita=domicilio_localita,
                domicilio_nazione=domicilio_nazione,
                permesso=permesso,
                permesso_rilascio=permesso_rilascio,
                permesso_scadenza=permesso_scadenza,
                stato_civile=stato_civile,
                data_matrimonio=data_matrimonio,
                data_divorzio=data_divorzio,
                frontaliere_con=frontaliere_con,
                rientro=rientro,
                indirizzo_settimanale=indirizzo_settimanale,
                convivenza=convivenza,
                autorita_parentale=autorita_parentale,
                reddito_maggiore=reddito_maggiore,
                figli_convivenza=figli_convivenza,
                patente=patente, religione=religione,
            ))
            st.session_state.step = 3
            st.rerun()

elif st.session_state.step == 3:
    st.progress(0.35)
    bottone_indietro(2)

    with st.form("form_step3"):
        sez("Dati coniuge / partner")
        coniuge_cognome = coniuge_nome = coniuge_nascita = ""
        coniuge_avs = ""
        coniuge_nazionalita = coniuge_luogo_nascita = ""
        coniuge_nazione = "Italia"
        coniuge_lavora = "No"
        coniuge_lavora_ch = "No"
        coniuge_res_est = False
        coniuge_dove = ""

        if st.session_state.dati.get("stato_civile") == "Coniugato/Partner registrato":
            c1, c2 = st.columns(2)
            with c1:
                coniuge_cognome     = st.text_input("Cognome coniuge *",
                    value=st.session_state.dati.get("coniuge_cognome",""))
                coniuge_nascita     = str(st.date_input(
                    "Data di nascita coniuge *",
                    min_value=date(1940,1,1),
                    max_value=date.today(), format="DD/MM/YYYY"))
                coniuge_nazionalita = st.text_input("Nazionalita coniuge",
                    value=st.session_state.dati.get("coniuge_nazionalita",""))
                coniuge_avs         = st.text_input("Numero AVS coniuge",
                    placeholder="756.XXXX.XXXX.XX",
                    value=st.session_state.dati.get("coniuge_avs",""))
            with c2:
                coniuge_nome          = st.text_input("Nome coniuge *",
                    value=st.session_state.dati.get("coniuge_nome",""))
                coniuge_luogo_nascita = st.text_input("Luogo di nascita coniuge",
                    value=st.session_state.dati.get("coniuge_luogo_nascita",""))
                coniuge_nazione       = st.selectbox("Nazione residenza coniuge",
                    ["Italia", "Svizzera", "Germania", "Francia", "Altra"])
            coniuge_res_est = st.checkbox("Residenza estera?")
            coniuge_dove    = st.text_input("Dove?",
                value=st.session_state.dati.get("coniuge_dove","")) \
                if coniuge_res_est else ""
            coniuge_lavora  = st.selectbox(
                "Il coniuge lavora o percepisce un reddito?", ["No", "Si"])
            coniuge_lavora_ch = "No"
            if coniuge_lavora == "Si":
                coniuge_lavora_ch = st.selectbox("Lavora in Svizzera?", ["No", "Si"])
        else:
            st.info("Sezione non applicabile.")

        sez("Figli a carico")
        st.caption("I figli sono deducibili fino a 18 anni di eta. "
                   "Nome e cognome di ogni figlio e obbligatorio.")

        n_figli = st.number_input("Numero di figli a carico",
                                   min_value=0, max_value=10, value=0)
        figli = []

        if n_figli > 0:
            st.markdown("---")
            for i in range(int(n_figli)):
                st.markdown(f"**Figlio/a {i+1}**")
                c1, c2 = st.columns(2)
                with c1:
                    fn = st.text_input(
                        f"Nome e cognome figlio/a {i+1} *",
                        key=f"fn{i}",
                        placeholder="es. Mario Rossi")
                    fd = st.date_input(
                        "Data di nascita *",
                        key=f"fd{i}",
                        min_value=date(1990, 1, 1),
                        max_value=date.today(),
                        format="DD/MM/YYYY")
                with c2:
                    fi = st.date_input(
                        "Inizio diritto assegno familiare",
                        key=f"fi{i}",
                        value=None,
                        format="DD/MM/YYYY")
                    ff = st.date_input(
                        "Fine diritto assegno familiare",
                        key=f"ff{i}",
                        value=None,
                        max_value=date(2040,1,1),
                        format="DD/MM/YYYY")
                figli.append(dict(
                    nome=fn,
                    nascita=str(fd),
                    inizio=str(fi) if fi else "",
                    fine=str(ff) if ff else ""
                ))
                if i < n_figli - 1:
                    st.markdown("---")

        assegni = st.checkbox("Ha diritto agli assegni famigliari?")

        sez("Genitori")
        c1, c2 = st.columns(2)
        with c1:
            padre_cognome = st.text_input("Cognome del padre",
                value=st.session_state.dati.get("padre_cognome",""))
            padre_nome    = st.text_input("Nome del padre",
                value=st.session_state.dati.get("padre_nome",""))
            padre_nascita = str(st.date_input("Data di nascita padre",
                                 value=None, min_value=date(1920,1,1),
                                 max_value=date.today(), format="DD/MM/YYYY"))
        with c2:
            madre_cognome = st.text_input("Cognome da nubile della madre",
                value=st.session_state.dati.get("madre_cognome",""))
            madre_nome    = st.text_input("Nome della madre",
                value=st.session_state.dati.get("madre_nome",""))
            madre_nascita = str(st.date_input("Data di nascita madre",
                                 value=None, min_value=date(1920,1,1),
                                 max_value=date.today(), format="DD/MM/YYYY"))

        submitted3 = st.form_submit_button("Avanti")

    if submitted3:
        errori = []
        if st.session_state.dati.get("stato_civile") == "Coniugato/Partner registrato":
            if not coniuge_cognome: errori.append("Cognome coniuge")
            if not coniuge_nome:    errori.append("Nome coniuge")
        eta_max = date.today() - timedelta(days=18*365)
        for i, f in enumerate(figli):
            if not f.get("nome","").strip():
                errori.append(f"Nome e cognome figlio/a {i+1}")
            try:
                if date.fromisoformat(f.get("nascita","")) < eta_max:
                    errori.append(f"Figlio/a {i+1}: eta superiore a 18 anni")
            except Exception:
                pass
        if errori:
            st.error("Campi obbligatori mancanti o errati: **" + ", ".join(errori) + "**")
        else:
            st.session_state.dati.update(dict(
                coniuge_cognome=coniuge_cognome, coniuge_nome=coniuge_nome,
                coniuge_nascita=coniuge_nascita, coniuge_avs=coniuge_avs,
                coniuge_nazionalita=coniuge_nazionalita,
                coniuge_luogo_nascita=coniuge_luogo_nascita,
                coniuge_nazione=coniuge_nazione,
                coniuge_residenza_estera=coniuge_res_est,
                coniuge_dove=coniuge_dove,
                coniuge_lavora=coniuge_lavora,
                coniuge_lavora_ch=coniuge_lavora_ch,
                figli=figli, assegni_famigliari=assegni,
                padre_cognome=padre_cognome, padre_nome=padre_nome,
                padre_nascita=padre_nascita,
                madre_cognome=madre_cognome, madre_nome=madre_nome,
                madre_nascita=madre_nascita,
            ))
            st.session_state.step = 4
            st.rerun()

elif st.session_state.step == 4:
    st.progress(0.55)
    bottone_indietro(3)

    with st.form("form_step4"):
        sez("Dati professionali")
        c1, c2 = st.columns(2)
        with c1:
            qualifica   = st.text_input("Qualifica – mansione *",
                value=st.session_state.dati.get("qualifica",""))
            data_inizio = str(st.date_input("Data inizio attivita *",
                               min_value=date(2000,1,1),
                               max_value=date(2030,1,1),
                               format="DD/MM/YYYY"))
        with c2:
            grado          = st.slider("Grado di occupazione (%) *", 10, 100, 100, 5)
            altre_attivita = st.checkbox("Ha altre attivita / rendite / pensioni?")

        sez("Dati bancari")
        c1, c2 = st.columns(2)
        with c1:
            banca_nome     = st.text_input("Nome della banca *",
                value=st.session_state.dati.get("banca_nome",""))
            banca_titolare = st.text_input("Titolare del conto *",
                value=st.session_state.dati.get("banca_titolare",""))
            iban           = st.text_input("IBAN *",
                value=st.session_state.dati.get("iban",""))
        with c2:
            banca_citta = st.text_input("Citta della banca *",
                value=st.session_state.dati.get("banca_citta",""))
            swift       = st.text_input("SWIFT/BIC *",
                value=st.session_state.dati.get("swift",""))

        sez("Sicurezza sul lavoro")
        videosorveglianza = st.checkbox(
            "Acconsento alla videosorveglianza dei luoghi di lavoro "
            "(non riprende spogliatoi/servizi; accesso riservato al management)")
        formazione_ccnl   = st.selectbox(
            "Possiedo una formazione professionale secondo il CCNL Alberghiero Svizzero?",
            ["No", "Si"])
        formazione_quale  = ""
        if formazione_ccnl == "Si":
            formazione_quale = st.text_input("Se si, quale?",
                value=st.session_state.dati.get("formazione_quale",""))
        consenso_dati = st.checkbox(
            "Acconsento al trattamento dei miei dati personali "
            "secondo la legge sulla protezione dei dati *")

        submitted4 = st.form_submit_button("Avanti")

    if submitted4:
        errori = []
        if not qualifica:      errori.append("Qualifica – mansione")
        if not banca_nome:     errori.append("Nome della banca")
        if not banca_titolare: errori.append("Titolare del conto")
        if not iban:           errori.append("IBAN")
        if not swift:          errori.append("SWIFT/BIC")
        if not consenso_dati:  errori.append("Consenso trattamento dati (obbligatorio)")
        if errori:
            st.error("Campi obbligatori mancanti: **" + ", ".join(errori) + "**")
        else:
            st.session_state.dati.update(dict(
                qualifica=qualifica, data_inizio=data_inizio,
                grado_occupazione=grado, altre_attivita=altre_attivita,
                banca_nome=banca_nome, banca_citta=banca_citta,
                banca_titolare=banca_titolare, iban=iban, swift=swift,
                videosorveglianza=videosorveglianza,
                formazione_ccnl=formazione_ccnl,
                formazione_quale=formazione_quale,
                consenso_dati=consenso_dati,
            ))
            st.session_state.step = 5
            st.rerun()

elif st.session_state.step == 5:
    if st.session_state.vf and st.session_state.tipo_lavoratore == "frontaliere":
        st.progress(0.75)
        bottone_indietro(4)

        with st.form("form_step5"):
            sez("Modulo 1A – Attestazione vecchio frontaliere")
            st.info("Poiche hai lavorato in Svizzera prima del 18/07/2023, "
                    "devi compilare anche il Modulo 1A.")
            c1, c2 = st.columns(2)
            with c1:
                prev_datore = st.text_input(
                    "Nome precedente datore di lavoro in CH *",
                    value=st.session_state.dati.get("prev_datore",""))
                prev_datore_indirizzo = st.text_input(
                    "Indirizzo precedente datore di lavoro *",
                    value=st.session_state.dati.get("prev_datore_indirizzo",""))
                prev_dal    = str(st.date_input(
                    "Periodo attivita – dal *",
                    min_value=date(2000,1,1),
                    max_value=date(2023,7,17),
                    format="DD/MM/YYYY"))
                comune_residenza_frontiera = st.text_input(
                    "Comune italiano di residenza (area di frontiera) *",
                    value=st.session_state.dati.get("comune_residenza_frontiera",""))
            with c2:
                prev_al = str(st.date_input(
                    "Periodo attivita – al *",
                    min_value=date(2023,7,17),
                    max_value=date.today(),
                    format="DD/MM/YYYY"))
                npa_residenza = st.text_input(
                    "CAP del comune di residenza *",
                    value=st.session_state.dati.get("npa_residenza",""))
            submitted5 = st.form_submit_button("Avanti")

        if submitted5:
            errori = []
            if not prev_datore:                errori.append("Nome precedente datore di lavoro")
            if not prev_datore_indirizzo:      errori.append("Indirizzo precedente datore di lavoro")
            if not comune_residenza_frontiera: errori.append("Comune di residenza")
            if not npa_residenza:              errori.append("CAP di residenza")
            if errori:
                st.error("Campi obbligatori mancanti: **" + ", ".join(errori) + "**")
            else:
                st.session_state.dati.update(dict(
                    prev_datore=prev_datore,
                    prev_datore_indirizzo=prev_datore_indirizzo,
                    prev_dal=prev_dal, prev_al=prev_al,
                    comune_residenza_frontiera=comune_residenza_frontiera,
                    npa_residenza=npa_residenza,
                ))
                st.session_state.step = 6
                st.rerun()
    else:
        st.session_state.step = 6
        st.rerun()

elif st.session_state.step == 6:
    st.progress(0.85)
    step_prec = 5 if (st.session_state.vf and
                      st.session_state.tipo_lavoratore == "frontaliere") else 4
    bottone_indietro(step_prec)

    sez("Caricamento documenti")
    st.markdown("**Documento d'identita** (carta d'identita o passaporto, fronte e retro) *")
    st.caption("Puoi caricare una o piu foto oppure un PDF.")
    doc_files = st.file_uploader(
        "Carica documento d'identita *",
        type=["jpg","jpeg","png","pdf","heic"],
        accept_multiple_files=True,
        key="doc_identita"
    )

    permesso_files_up = []
    permesso_corrente = st.session_state.dati.get("permesso","")
    if permesso_corrente in PERMESSI_CON_UPLOAD:
        st.markdown(f"**{permesso_corrente}** (fronte e retro) *")
        st.caption("Puoi caricare una o piu foto oppure un PDF.")
        permesso_files_up = st.file_uploader(
            "Carica permesso *",
            type=["jpg","jpeg","png","pdf","heic"],
            accept_multiple_files=True,
            key="permesso_doc"
        )

    sez("Firma digitale")
    st.caption("Firma nel riquadro con il dito (mobile) o il mouse (PC).")
    canvas_result = st_canvas(
        stroke_width=3, stroke_color="#000000", background_color="#ffffff",
        height=150, drawing_mode="freedraw", key="canvas_firma",
    )
    data_firma = st.date_input("Data *", value=date.today(),
                                max_value=date.today(), format="DD/MM/YYYY")

    st.markdown("---")
    st.markdown("### Dichiarazione di responsabilita")
    dichiarazione = st.checkbox(
        "Il/La sottoscritto/a dichiara sotto la propria responsabilita che tutti "
        "i dati inseriti sono veritieri e completi, ai sensi delle disposizioni "
        "in materia di sottrazione d'imposta (art. 258 segg. LT) e di frode "
        "fiscale (art. 269 LT)."
    )

    if st.button("Invia documenti"):
        if not check_rate_limit():
            st.error("Troppi invii. Riprova tra un'ora.")
            st.stop()

        errori = []
        if not dichiarazione:
            errori.append("Dichiarazione di responsabilita")
        if not doc_files:
            errori.append("Documento d'identita (obbligatorio)")
        if permesso_corrente in PERMESSI_CON_UPLOAD and not permesso_files_up:
            errori.append(f"Permesso {permesso_corrente} (obbligatorio)")
        if canvas_result.image_data is None:
            errori.append("Firma digitale")
        else:
            if canvas_result.image_data[:,:,3].sum() == 0:
                errori.append("Firma digitale (canvas vuoto)")

        if errori:
            st.error("Manca: **" + ", ".join(errori) + "**")
        else:
            TIPI_VALIDI = {"image/jpeg", "image/png", "image/heic", "application/pdf"}
            for f in list(doc_files) + list(permesso_files_up or []):
                if f.type not in TIPI_VALIDI:
                    st.error(f"Tipo file non valido: {f.name}")
                    st.stop()
                if f.size > 10 * 1024 * 1024:
                    st.error(f"File troppo grande (max 10MB): {f.name}")
                    st.stop()

            arr = canvas_result.image_data
            img = Image.fromarray(arr.astype("uint8"), "RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            firma_b64 = "data:image/png;base64," + base64.b64encode(
                buf.getvalue()).decode()

            dati = st.session_state.dati
            dati["data_firma"] = str(data_firma)
            dati["tipo_lavoratore"] = st.session_state.tipo_lavoratore

            doc_list  = [(f.name, f.read(), f.type or "application/octet-stream")
                         for f in doc_files]
            perm_list = [(f.name, f.read(), f.type or "application/octet-stream")
                         for f in (permesso_files_up or [])]

            with st.spinner("Generazione documenti in corso..."):
                pdfs = {}
                pdfs["Modulo1_ImposteAllaFonte.pdf"] = genera_modulo1(dati, firma_b64)
                if st.session_state.vf and st.session_state.tipo_lavoratore == "frontaliere":
                    pdfs["Modulo1A_VecchioFrontaliere.pdf"] = genera_modulo1a(dati, firma_b64)
                pdfs["Modulo1908_DatiPersonali.pdf"] = genera_modulo1908(dati, firma_b64)
                st.session_state.submit_count += 1
                errore = salva_compilazione(
                    dati["nome"], dati["cognome"],
                    st.session_state.vf, pdfs, dati,
                    doc_identita=doc_list,
                    permesso_files=perm_list
                )

            if errore is None:
                st.session_state.step = 7
                st.rerun()
            else:
                st.error(f"Errore dettagliato: {errore}")

elif st.session_state.step == 7:
    st.success("### Compilazione completata!")
    st.markdown("I tuoi documenti sono stati ricevuti da 1908 Group SA.")
    st.markdown("Puoi chiudere questa pagina.")
