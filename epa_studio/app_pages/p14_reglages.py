import streamlit as st

from epa.branding import (DEFAUT_COULEUR, POLICES_TEXTE, POLICES_TITRES, branding_courant, contraste_blanc, couleur_valide,
                          enregistrer_marque)
from epa.http import cache_size_mb, clear_cache
from epa.ui import entete

entete(None, "Réglages", "à vos couleurs", "Identité du bureau d'études : interface, figures exportées, rapport Word et diapositives.")
b = branding_courant()
with st.form("branding"):
    c1, c2 = st.columns(2)
    nom = c1.text_input("Nom du bureau d'études", value=b.nom)
    coul = c2.color_picker("Couleur d'accent", value=b.couleur, help="Boutons, liens et mise en évidence sur les figures.")
    p1 = c1.selectbox("Police des titres", POLICES_TITRES, index=POLICES_TITRES.index(b.police_titres))
    p2 = c2.selectbox("Police du texte", POLICES_TEXTE, index=POLICES_TEXTE.index(b.police_texte))
    logo = st.file_uploader("Logo (PNG, JPG ou SVG)", type=["png", "jpg", "jpeg", "svg"])
    g1, g2 = st.columns(2)
    gdocx = g1.file_uploader("Gabarit Word du bureau (.docx, .dotx)", type=["docx", "dotx"],
                             help="Styles, en-têtes et pieds de page repris dans le rapport généré.")
    gpptx = g2.file_uploader("Gabarit PowerPoint du bureau (.pptx, .potx)", type=["pptx", "potx"],
                             help="Masques et format repris dans les diapositives générées.")
    pour_tous = st.toggle("Enregistrer pour tous les utilisateurs de cette instance", value=True)
    if st.form_submit_button("Enregistrer", type="primary"):
        regl = {"nom": nom, "couleur": couleur_valide(coul), "police_titres": p1, "police_texte": p2}
        fichiers = {k: (f.name, f.getvalue()) for k, f in (("logo", logo), ("gabarit_docx", gdocx), ("gabarit_pptx", gpptx)) if f}
        try:
            if pour_tous:
                enregistrer_marque(regl, fichiers)
                st.session_state.pop("branding", None)
            else:
                st.session_state["branding"] = regl
            st.rerun()
        except ValueError as e:
            st.error(str(e))

if contraste_blanc(b.couleur) < 4.5:
    st.warning(f"La couleur {b.couleur} offre un contraste de {contraste_blanc(b.couleur):.1f}:1 avec le blanc, sous le seuil "
               "de 4,5:1 recommandé (WCAG 2.2, niveau AA) : textes des boutons et liens peu lisibles. Choisissez une teinte plus foncée.")
etat = [("Logo", b.logo), ("Gabarit Word", b.gabarit_docx), ("Gabarit PowerPoint", b.gabarit_pptx)]
st.caption(" ; ".join(f"{k} : {'enregistré' if v else 'aucun'}" for k, v in etat) + f". Couleur par défaut : {DEFAUT_COULEUR}.")

st.markdown("#### Données en cache")
taille = f"{cache_size_mb():.1f}".replace(".", ",")
st.write(f"Les données téléchargées sont conservées sur le disque pour accélérer les calculs suivants. Taille actuelle : {taille} Mo.")
if st.button("Vider le cache"):
    st.success(f"{clear_cache()} fichiers supprimés.")
