import streamlit as st

from epa.branding import DEFAUT_COULEUR, branding_courant, contraste_blanc, couleur_valide
from epa.http import cache_size_mb, clear_cache
from epa.ui import entete

entete(None, "Réglages", "Identité du bureau d'études affichée dans l'application et sur les figures exportées.")
b = branding_courant()
with st.form("branding"):
    nom = st.text_input("Nom du bureau d'études", value=b.nom)
    coul = st.color_picker("Couleur d'accent", value=b.couleur, help="Boutons, liens, étape active et mise en évidence sur les figures.")
    if st.form_submit_button("Enregistrer pour cette session", type="primary"):
        st.session_state["branding"] = {"nom": nom, "couleur": couleur_valide(coul)}
        st.rerun()
if contraste_blanc(b.couleur) < 4.5:
    st.warning(f"La couleur {b.couleur} offre un contraste de {contraste_blanc(b.couleur):.1f}:1 avec le blanc, sous le seuil "
               "de 4,5:1 recommandé (WCAG 2.2, niveau AA) : textes des boutons et liens peu lisibles. Choisissez une teinte plus foncée.")
st.caption("Pour rendre ces réglages permanents, modifiez le fichier branding.toml à la racine de l'application "
           f"(nom, couleur au format #RRGGBB, logo facultatif). Couleur par défaut : {DEFAUT_COULEUR}.")

st.markdown("#### Données en cache")
taille = f"{cache_size_mb():.1f}".replace(".", ",")
st.write(f"Les données téléchargées sont conservées sur le disque pour accélérer les calculs suivants. Taille actuelle : {taille} Mo.")
if st.button("Vider le cache"):
    st.success(f"{clear_cache()} fichiers supprimés.")
