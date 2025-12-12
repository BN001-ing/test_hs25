# KuBeKo – Kubaturen, Bewehrung und Kosten

**Semesterprojekt – Digital Twin Programmieren (HS25)**
Bachelorstudiengang Digital Construction, HSLU

Repository: [https://github.com/BN001-ing/test_hs25](https://github.com/BN001-ing/test_hs25)

---

## Projektidee

**KuBeKo (Kubaturen + Bewehrung + Kosten)** ist ein Python-basiertes Auswertungstool zur automatisierten Analyse von IFC-Gebäudemodellen. Ziel ist es, Betonkubaturen, Bewehrungsmengen und daraus abgeleitete Kosten strukturiert, nachvollziehbar und reproduzierbar zu berechnen.

Das Tool richtet sich insbesondere an frühe Projektphasen (Kostenschätzung, Variantenvergleich, Plausibilitätsprüfung) und reduziert manuelle Arbeitsschritte sowie Medienbrüche zwischen BIM-Modell und Auswertung.

---

## Problemstellung

In der Praxis werden Mengen- und Kostenermittlungen häufig manuell aus BIM-Modellen abgeleitet und in Excel weiterverarbeitet. Dieser Prozess ist:

* zeitaufwendig
* fehleranfällig
* wenig transparent

Obwohl IFC-Modelle bereits viele relevante Informationen enthalten, werden diese aufgrund uneinheitlicher Modellierungsweisen und fehlender Automatisierung nur eingeschränkt genutzt.

---

## Zielsetzung

Das Projekt verfolgt folgende Ziele:

* automatisches Einlesen und Aufbereiten von IFC-Modellen
* strukturierte Auswertung von Betonkubaturen nach Gebäude, Geschoss, Bauteil und Material
* Preiszuweisung über eine editierbare Materialdatenbank
* Berechnung von Bewehrungsmengen auf Basis von Kennwerten (kg/m³)
* flexible Aufteilung der Bewehrung nach Normgruppen (z. B. B500B)
* transparente Darstellung der Resultate

---

## Systemarchitektur

### 1. UI-Schicht (Frontend)

* Umsetzung mit **Streamlit**
* Tabs: IFC-Import, Material, Bewehrung, Materialdatenbank, Dashboard (Ausblick), Debug
* Benutzerinteraktion, Visualisierung und Parametereingaben

### 2. Logik-Schicht

* IFC-Logik: Parsing und Modellaufbereitung
* Material-Logik: Volumen- und Kostenberechnung
* Bewehrungs-Logik: Mengenberechnung und Aufteilung

### 3. Daten-Schicht

* IFC-Datei als Input
* SQLite-Datenbank (`preise.db`) für Materialpreise
* Streamlit Session State für temporäre Overrides

---

## Technische Umsetzung

### Entwicklungsumgebung

* **Programmiersprache:** Python 3.x
* **Virtuelle Umgebung:** venv
* **Paketverwaltung:** pip (`requirements.txt`)
* **Editor:** Visual Studio Code
* **Versionskontrolle:** Git & GitHub

### Zentrale Python-Module

* `ifcopenshell` – IFC-Import und Geometrieauswertung
* `pandas`, `numpy` – Datenstrukturierung und Berechnung
* `streamlit` – Benutzeroberfläche
* `plotly` – Visualisierung (Dashboard)
* `sqlite3` – Material- und Preisdatenbank

Alle verwendeten Module und Versionen sind in der Datei **`requirements.txt`** dokumentiert.

---

## Installation

```bash
# Repository klonen
git clone https://github.com/BN001-ing/test_hs25.git
cd test_hs25

# Virtuelle Umgebung erstellen
python -m venv venv

# Umgebung aktivieren (Windows)
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

---

## Anwendung / Workflow

1. IFC-Datei über die Benutzeroberfläche hochladen
2. Automatische Ermittlung der Materialkubaturen
3. Prüfung und Anpassung der Materialpreise
4. Eingabe von Bewehrungskennwerten (kg/m³) pro Bauteil
5. Aufteilung der Bewehrung nach Gruppen und Durchmessern
6. Analyse der Ergebnisse und Weiterverwendung