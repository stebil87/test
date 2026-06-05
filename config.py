import streamlit as st

AZIENDA = {
    "ragione_sociale": "1908 Group SA",
    "indirizzo_1": "Via Cantonale 18",
    "indirizzo_2": "Suglio Business Center",
    "npa_localita": "6928 Manno",
    "numero_idi": "CHE-296.614.693",
    "comune_fiscale": "6928 Manno",
    "numero_controllo": "100.78.021.890",
}

MANAGER_USERNAME = st.secrets["MANAGER_USERNAME"]
MANAGER_PASSWORD = st.secrets["MANAGER_PASSWORD"]
SUPABASE_URL     = st.secrets["SUPABASE_URL"]
SUPABASE_KEY     = st.secrets["SUPABASE_KEY"]
SUPABASE_BUCKET  = "pdf-compilazioni"
