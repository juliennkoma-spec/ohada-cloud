import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="OHADA Cloud - Gestion", layout="wide")
TAUX_TVA = 0.1925

# --- URL DE VOTRE FEUILLE (Partagez la feuille en "Éditeur" avec l'email du compte de service) ---
URL_GSHEET = "https://docs.google.com/spreadsheets/d/16oKVFi3XeDlXMMvIWsXtXNHO5Z5GEITHrzi953P9V6k/edit"

# --- BASE DES UTILISATEURS (Hardcoded pour la simplicité) ---
USERS = {
    "admin": {"password": "123", "role": "admin", "label": "Direction Générale"},
    "amina": {"password": "456", "role": "user", "label": "Boutique Amina"},
    "jean": {"password": "789", "role": "user", "label": "Garage Jean"}
}

# --- CONNEXION ---
# Note : Les clés seront configurées dans le "Secrets" de Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

def charger_journal():
    try:
        # Lecture sans cache pour avoir les données en temps réel
        df = conn.read(spreadsheet=URL_GSHEET, worksheet="Journal", ttl=0)
        df = df.dropna(how='all')
        # Conversion des types pour éviter les erreurs de calcul
        for col in ['Quantité', 'Prix_Unitaire', 'Débit', 'Crédit']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return pd.DataFrame(columns=["ID", "Structure", "Date", "Référence", "Libellé", "Compte", "Quantité", "Prix_Unitaire", "Débit", "Crédit"])

def sauvegarder(df):
    try:
        conn.update(spreadsheet=URL_GSHEET, worksheet="Journal", data=df)
        st.success("☁️ Synchronisé avec succès !")
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

# --- LOGIQUE DE CONNEXION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Accès OHADA Cloud")
    with st.form("login_form"):
        u = st.text_input("Identifiant utilisateur")
        p = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            if u in USERS and USERS[u]["password"] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = USERS[u]["role"]
                st.session_state.label = USERS[u]["label"]
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect")
    st.stop()

# --- INTERFACE PRINCIPALE ---
df_global = charger_journal()
user_log = st.session_state.username
role_log = st.session_state.role

st.sidebar.header(f"👤 {st.session_state.label}")
if st.sidebar.button("Se déconnecter"):
    st.session_state.logged_in = False
    st.rerun()

# Filtrage des données selon le rôle
if role_log == "admin":
    menu = st.sidebar.radio("Menu Admin", ["Tableau de bord", "Saisie Opération", "Journal Global"])
    df_vue = df_global
else:
    menu = st.sidebar.radio("Menu Boutique", ["Saisie Opération", "Mes Écritures", "Ma Balance"])
    df_vue = df_global[df_global['Structure'] == user_log]

# --- LOGIQUE DES MENUS ---

if menu == "Saisie Opération":
    st.subheader(f"📝 Nouvelle saisie - {st.session_state.label}")
    with st.form("form_saisie", clear_on_submit=True):
        c1, c2 = st.columns(2)
        date = c1.date_input("Date")
        ref = c2.text_input("Référence (N° Facture)")
        libelle = st.text_input("Libellé de l'opération")
        
        c3, c4, c5 = st.columns(3)
        nature = c3.selectbox("Type", ["Vente de marchandises (701)", "Achat de marchandises (601)", "Services produits (706)", "Fournitures (602)"])
        qte = c4.number_input("Quantité", min_value=1.0, value=1.0)
        pu = c5.number_input("Prix Unitaire HT", min_value=0.0)
        
        c6, c7 = st.columns(2)
        sens = c6.selectbox("Type de flux", ["Recette", "Dépense"])
        moyen = c7.selectbox("Règlement via", ["Caisse (571)", "Banque (521)"])
        
        tva_check = st.checkbox("Appliquer la TVA (19.25%)", value=True)
        
        if st.form_submit_button("Enregistrer l'opération"):
            # Calculs
            montant_ht = qte * pu
            tva = montant_ht * TAUX_TVA if tva_check else 0
            ttc = montant_ht + tva
            op_id = str(int(time.time()))
            compte_ht = nature.split('(')[1].replace(')', '')
            compte_tr = "571" if "Caisse" in moyen else "521"
            
            nouvelles_lignes = []
            if sens == "Recette":
                # Crédit Produit, Crédit TVA, Débit Trésorerie
                nouvelles_lignes.append({"ID": op_id, "Structure": user_log, "Date": str(date), "Référence": ref, "Libellé": libelle, "Compte": compte_ht, "Quantité": qte, "Prix_Unitaire": pu, "Débit": 0, "Crédit": montant_ht})
                if tva > 0: nouvelles_lignes.append({"ID": op_id, "Structure": user_log, "Date": str(date), "Référence": ref, "Libellé": "TVA Collectée", "Compte": "4431", "Quantité": 0, "Prix_Unitaire": 0, "Débit": 0, "Crédit": tva})
                nouvelles_lignes.append({"ID": op_id, "Structure": user_log, "Date": str(date), "Référence": ref, "Libellé": libelle, "Compte": compte_tr, "Quantité": 0, "Prix_Unitaire": 0, "Débit": ttc, "Crédit": 0})
            else:
                # Débit Charge, Débit TVA, Crédit Trésorerie
                nouvelles_lignes.append({"ID": op_id, "Structure": user_log, "Date": str(date), "Référence": ref, "Libellé": libelle, "Compte": compte_ht, "Quantité": qte, "Prix_Unitaire": pu, "Débit": montant_ht, "Crédit": 0})
                if tva > 0: nouvelles_lignes.append({"ID": op_id, "Structure": user_log, "Date": str(date), "Référence": ref, "Libellé": "TVA Récupérable", "Compte": "445", "Quantité": 0, "Prix_Unitaire": 0, "Débit": tva, "Crédit": 0})
                nouvelles_lignes.append({"ID": op_id, "Structure": user_log, "Date": str(date), "Référence": ref, "Libellé": libelle, "Compte": compte_tr, "Quantité": 0, "Prix_Unitaire": 0, "Débit": 0, "Crédit": ttc})
            
            df_global = pd.concat([df_global, pd.DataFrame(nouvelles_lignes)], ignore_index=True)
            sauvegarder(df_global)
            st.rerun()

elif menu == "Mes Écritures" or menu == "Journal Global":
    st.subheader("📜 Historique des écritures")
    st.dataframe(df_vue, use_container_width=True)
    
    if st.checkbox("Activer la suppression (Admin ou Propriétaire)"):
        id_a_suppr = st.text_input("Entrez l'ID de l'opération à supprimer")
        if st.button("❌ Supprimer définitivement"):
            df_global = df_global[df_global['ID'].astype(str) != id_a_suppr]
            sauvegarder(df_global)
            st.rerun()

elif menu == "Tableau de bord":
    st.subheader("📊 Performance Globale (Admin)")
    resumé = df_global.groupby('Structure').apply(lambda x: pd.Series({
        "Ventes (HT)": x[x['Compte'].astype(str).str.startswith('7')]['Crédit'].sum(),
        "Achats (HT)": x[x['Compte'].astype(str).str.startswith('6')]['Débit'].sum(),
        "Solde Caisse/Banque": x[x['Compte'].astype(str).str.startswith('5')]['Débit'].sum() - x[x['Compte'].astype(str).str.startswith('5')]['Crédit'].sum()
    })).reset_index()
    st.table(resumé)

elif menu == "Ma Balance":
    st.subheader(f"⚖️ Situation : {st.session_state.label}")
    balance = df_vue.groupby('Compte')[['Débit', 'Crédit']].sum()
    st.table(balance)
