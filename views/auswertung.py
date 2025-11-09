import streamlit as st
import IFC
import pandas as pd
import time

#---------------Variablen-------------------
#Leerer Panda Dataframe erstellen.
columns = [
    "GlobalID",
    "Grundstück",
    "Gebäude",
    "Geschoss",
    "Namen",
    "IFCClass",
    "Material",
    "Volumen_m3"
]
df_ifc = pd.DataFrame(columns=columns)

text_match = 90

#Optionen
#Optionen
@st.dialog("Optionen")
def show_options(text_match: str):
    st.markdown("**Fuzzymatch optionen**")
    st.write("""
             Hier kann eingestellt werden bis zu welcher abweichung atributtexte kombiniert werden sollen

             Beispiel:
             Wand / wand = 97% Übereinstimmung
             """)
    text_match = st.slider("", 0, 100, 90)
    return(text_match)

#-----------------------------Import------------------
st.title("📊 Kubeko")

if st.button("Optionen"):
    text_match = show_options(text_match)

#Upload knopf
uploaded_file = st.file_uploader(
    "Upload data", accept_multiple_files=False, type="ifc"
)
if not uploaded_file:
    st.stop()


#-----------------Auswertung der IFC Datei (Dataframe erstellen--------------
with st.spinner("Ich mache gerade deinen Job, also lehn dich zurück😉", show_time=True):
    
    #Datei Importieren
    ifc_model = IFC.IMPORT_IFC(uploaded_file)

    #GlobaleID abfüllen für Sämtliche Elemente um sie zuordnen zu können
    df_new = IFC.get_all_global_ids_df(ifc_model)
    df_ifc = df_ifc.merge(
    df_new[["GlobalID", "IFCClass"]],
    on=["GlobalID", "IFCClass"],
    how="outer"
    )
    df_ifc = df_ifc.set_index("GlobalID")

    #Verortung des Bauteils aus dem IFC auslesen (GGrundstück,Gebäude,Geschoss)
    df_temp=IFC.Verortung(ifc_model)
    df_ifc.loc[df_temp.index, "Gebäude"] = df_temp["Gebäude"]
    df_ifc.loc[df_temp.index, "Geschoss"] = df_temp["Geschoss"]
    df_ifc.loc[df_temp.index, "Grundstück"] = df_temp["Grundstück"]

    #bauteil nach Materialien Filtern ()
    df_temp = IFC.material_series_by_element(ifc_model)
    df_ifc.loc[df_temp.index, "Material"] = df_temp["Material"]

    #Nach Namen filtern
    df_temp = IFC.KomponentenName(ifc_model)
    df_ifc.loc[df_temp.index, "Namen"] = df_temp["Name"]

    #Volumen ergänzen
    df_temp = IFC.Volumen_geom(ifc_model)
    df_ifc.loc[df_temp.index, "Volumen_m3"] = df_temp["Volumen_m3"]

#---------------Visuelles--------------------

#Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📄Dashboard", "🧱Material Kubaturen", "Bewehrung","🧑‍💻Dataframe(debug)"])

#Dashboard
with tab1:
    st.write("Dashboard")

#Material Kubaturen
with tab2:
    st.write("Kubaturen")
    edited_df = st.data_editor(
        df_ifc,
        column_config={
            "Bauteil": st.column_config.TextColumn(
                "Bauteil",
                help="Name des Bauteils",
            ),
            "Material": st.column_config.TextColumn(
                "Material",
                help="Zugeordnetes Material",
            ),
            "Volumen_m3": st.column_config.NumberColumn(
                "Kubatur [m³]",
                help="Berechnetes Volumen des Bauteils",
                step=0.01,
                format="%.2f",
            ),
            "Preis": st.column_config.NumberColumn(
                "Preis [CHF/m³]",
                help="Einheitspreis pro m³ (nicht negativ)",
                min_value=0.0,   # ⬅ verhindert negative Eingaben
                step=1.0,
                format="%.2f",
            ),
        },
        disabled=["Bauteil", "Material", "Volumen_m3"],  # nur Preis editierbar
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
    )

    st.write("""
    Alle spalten mit einem Bleistifft im Namen können Bearbeitet werden.
             
    Über das Anwählen der Zeile auf der Linken seite können die Zeiten entfernt werden.
    
    Durch das "+" welches oben links erscheint wenn man auf die Liste geht können Zeilen hinzugefügt werden.
    """)

#Bewehrung
with tab3:
    st.write("Bewehrung")

#Dataframe
with tab4:
    st.write("🧱 IFC-Datenrahmen für Debugging:", df_ifc)