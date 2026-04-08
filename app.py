import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="OHADA Cloud", layout="wide")

# --- CONNEXION (AVEC CORRECTEUR DE CLÉ) ---
def get_connection():
    # Cette astuce permet de corriger les problèmes de sauts de ligne (\n)
    creds = st.secrets["connections"]["gsheets"]
    if "\\n" in creds["private_key"]:
        creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_connection()

# --- CHARGEMENT DES DONNÉES ---
def charger_journal():
    try:
        # Remplacez par l'URL de votre feuille directement ici pour être sûr
        url = "https://docs.google.com/spreadsheets/d/16oKVFi3XeDlXMMvIWsXtXNHO5Z5GEITHrzi953P9V6k/edit"
        df = conn.read(spreadsheet=url, worksheet="Journal", ttl=0)
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erreur : {e}")
        return pd.DataFrame()

# --- LE RESTE DE VOTRE LOGIQUE (CONNEXION UTILISATEUR) ---
USERS = {
    "admin": {"password": "123", "role": "admin", "label": "Direction Générale"},
    "amina": {"password": "456", "role": "user", "label": "Boutique Amina"},
    "jean": {"password": "789", "role": "user", "label": "Garage Jean"}
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Accès OHADA Cloud")
    with st.form("login_form"):
        u = st.text_input("Identifiant")
        p = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            if u in USERS and USERS[u]["password"] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.label = USERS[u]["label"]
                st.rerun()
            else:
                st.error("Identifiant/Mot de passe incorrect")
    st.stop()

# Si connecté, afficher le journal
st.success(f"Bienvenue {st.session_state.label}")
df = charger_journal()
st.dataframe(df)
