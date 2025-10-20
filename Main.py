import streamlit as st
import os

#App Starten
#streamlit run UI.py

#App beenden
#CTRL + C unten im terminal

#Smileys mit Windows + .

#st.title("Titel")
#st.header("This is a header")
#st.subheader("Subheader")
#st.markdown("markdown")
#st.caption("caption")
#st.divider()

#st.image(os.path.join(os.getcwd(),"static","logo.png"))

#---PAGE SETUP---
about_page = st.Page(
    page = "views/abaout.py",
    title = "Abaout",
    icon = "🏠",
    default = True,
)

KuBeKo_page = st.Page(
    page = "views/auswertung.py",
    title = "Auswertung",
    icon = "📊",
)

Löschen_page = st.Page(
    page = "views/attribute entfernen.py",
    title = "Attribut löscher",
    icon = "🧹",
)    


#----Navigation Setup [WITHOUT SECTIONS]---
#pg = st.navigation(pages=[about_page,dart_page,rangliste_page])

pg = st.navigation(
    {
        "Info": [about_page],
        "IFC": [KuBeKo_page,Löschen_page],
    }
)

#---SHARED ON ALL PAGES---
st.logo("assets/Logo.png")
st.sidebar.text("Made with ❤️ by Niels")

#---RUN NAVIGATION---
pg.run()