import streamlit as st
import webbrowser

# ----------------- HERO SECTION -----------------
col1, col2 = st.columns(2, gap="small", vertical_alignment="center")

with col1:
    st.image("assets/Logo.png")

with col2:
    st.title("IFCedit", anchor=False)
    st.write(
        """
        Herzlich willkommen 👋

        Dieses Projekt entstand im Rahmen des Moduls **Digital Twin Programmieren (TA.BA_DT_PROGR)** 
        im Bachelorstudiengang **Digital Construction** an der Hochschule Luzern Technik & Architektur.

        Ziel des Moduls ist es, eigenständig ein funktionierendes Software-Werkzeug zu konzipieren, 
        zu entwickeln und zu dokumentieren. Dazu gehören u.a.:

        - Einrichten der Entwicklungsumgebung (venv, Git/GitHub, VS Code)  
        - Einsatz externer Python-Module wie *IfcOpenShell, Pandas, Matplotlib, SQLite*  
        - Aufbau einer benutzerfreundlichen Oberfläche mit Streamlit  
        - Präsentation und Dokumentation der fertigen Anwendung
        """
    )

    if st.button("Zum Bachelor-Studiengang Digital Construction"):
        webbrowser.open_new_tab(
            "https://www.hslu.ch/de-ch/technik-architektur/studium/bachelor/digital-construction/"
        )

    if st.button("Zum GitHub-Repository dieses Projekts"):
        webbrowser.open_new_tab("https://github.com/BN001-ing/test_hs25")

# ----------------- ANWENDUNGEN -----------------
st.divider()
st.title("Anwendungen", anchor=False)

col3, col4 = st.columns(2, gap="small", vertical_alignment="top")

with col3:
    st.image("assets/Logo_KuBeKo.png")
    # Hinweis: die Navigation zwischen Tabs/Seiten passiert über Main.py,
    # hier ist nur eine kurze Beschreibung.
    st.subheader("KuBeKo", anchor=False)
    st.write(
        """
        **KuBeKo** ist ein digitales Werkzeug zur automatisierten Auswertung von IFC-Modellen 
        im Bereich Kosten- und Mengenermittlung.

        - Liest IFC-Daten ein  
        - Analysiert Bauteile, Volumen und Materialien  
        - Verknüpft diese mit Kostenschlüsseln  
        - Liefert eine erste Kostenschätzung und strukturierte Mengenauswertung
        """
    )

with col4:
    st.image("assets/Logo_Rad.png")
    st.subheader("DaReCo", anchor=False)
    st.write(
        """
        **DaReCo** dient zur automatisierten Bereinigung von IFC-Dateien.

        - Entfernt PropertySets, Mengen (Quantities), Layer-Infos, Materialzuweisungen und Bezeichnungen  
        - Behält nur die reine geometrische Struktur des Modells  
        - Ideal, um «aufgeräumte» Modelle für weitere Workflows zu erzeugen
        """
    )
