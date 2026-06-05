import streamlit as st

AZIENDA = {
    "ragione_sociale": "Nome Azienda SA",
    "indirizzo_1":     "Via Example 1",
    "indirizzo_2":     "",
    "npa_localita":    "0000 Citta",
    "numero_idi":      "CHE-XXX.XXX.XXX",
    "comune_fiscale":  "0000 Citta",
    "numero_controllo":"XXX.XX.XXX.XXX",
}

MANAGER_USERNAME = st.secrets["MANAGER_USERNAME"]
MANAGER_PASSWORD = st.secrets["MANAGER_PASSWORD"]
SUPABASE_URL     = st.secrets["SUPABASE_URL"]
SUPABASE_KEY     = st.secrets["SUPABASE_KEY"]
SUPABASE_BUCKET  = "pdf-compilazioni"
