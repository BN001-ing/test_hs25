import streamlit as st
import webbrowser

share_url = "https://dc-dart.streamlit.app"  # ← deine veröffentlichte URL hier eintragen

#---HERO SECTION---
col1, col2 = st.columns(2,gap="small",vertical_alignment="center")

with col1:
    st.image("./assets/Logo.png")

with col2:
    st.title("IFCedit",anchor=False)
    st.write(
        """
        Herzlich wilkommen 

        Dieses Projekt entstand im Rahmen des Moduls Digital Twin Programmieren (TA.BA_DT_PROGR) 
        im Bachelorstudiengang Digital Construction an der Hochschule Luzern Technik & Architektur.
        Ziel des Moduls ist es, eigenständig ein funktionierendes Softwareprogramm zu konzipieren, 
        zu entwickeln und zu dokumentieren. Dabei sollen reale Anwendungsfälle aus den Bereichen Bauwesen, 
        Datenmanagement oder Digital Twin mit Python umgesetzt werden.

        Im Verlauf des Semesters werden die Studierenden schrittweise an die Entwicklung digitaler Werkzeuge herangeführt 
        von der Einrichtung der Entwicklungsumgebung (Venv, Git, GitHub, VS Code) über das Verwenden externer Python-Module 
        wie IfcOpenShell, Pandas, Matplotlib oder SQLite, bis hin zur Erstellung einer Benutzeroberfläche und 
        einer abschließenden Präsentation der Anwendung.
        """
    )
    if st.button("Zum Batchler programm"):
        webbrowser.open_new_tab("https://www.hslu.ch/de-ch/technik-architektur/studium/bachelor/digital-construction/?gclsrc=aw.ds&gad_source=1&gad_campaignid=786139618&gclid=CjwKCAjwu9fHBhAWEiwAzGRC_w5SixDNv5g_WpU6IbAUnRSTt2G_gn4I5jFAcCvOwIyzZwHy1XFbeBoCGuEQAvD_BwE")

    if st.button("Zum github eintrag"):
        webbrowser.open_new_tab("https://github.com/BN001-ing/test_hs25")

#---Share Button---
st.divider()
st.title("Anwendungen",anchor=False)
col3, col4 = st.columns(2,gap="small",vertical_alignment="top")

with col3:
    st.image("./assets/Logo_KuBeKo.png")
    if st.button("KuBeKo",icon="📊" ,width="stretch"):
        st.switch_page("views/auswertung.py")


with col4:
    st.image("./assets/Logo_Rad.png")
    if st.button("Attribut Entferner",icon="🧹" ,width="stretch"):
        st.switch_page("views/attribute entfernen.py")
    st.write(
        """
        Dieses Tool dient zur automatisierten Bereinigung von IFC-Dateien.
        Nach dem Hochladen einer IFC-Datei werden alle nicht geometrischen Zusatzinformationen wie PropertySets, Mengen (Quantities), Layer-Informationen, Materialzuweisungen und Bezeichnungen entfernt.
        Dadurch bleibt nur die reine geometrische Struktur des Modells erhalten, während alle attributiven Daten gelöscht werden.
        """
    )
