import sqlite3
from datetime import datetime
import math
import os

# SQL-Statements
CREATE_MATERIAL_TABLE = """
CREATE TABLE IF NOT EXISTS material (
    id INTEGER PRIMARY KEY,
    material_name TEXT NOT NULL,
    einheit TEXT,
    preis_chf REAL,
    datum_aktualisiert TEXT
);
"""

INSERT_MATERIAL = """
INSERT INTO material (material_name, einheit, preis_chf, datum_aktualisiert)
VALUES (?, ?, ?, ?);
"""

GET_ALL_MATERIAL = "SELECT * FROM material;"
GET_MATERIAL_BY_NAME = "SELECT * FROM material WHERE material_name = ?;"


def connect():
    """
    Stellt eine Verbindung mit der Datenbak her.
    Args:
        Keine eingebe erforderlich
    Returns:
        Datenbank
    """
    return sqlite3.connect("preise.db")

def create_tables(Connection):
    """
    Erstellt eine Datenbank fals keine vorhanden.
    Args:
        Datenbank
    Return:
        Keiner
    """
    with Connection:
        Connection.execute(CREATE_MATERIAL_TABLE)

def add_material(material_name, einheit, preis_chf):
    """Fügt ein neues Material mit Preis in die Datenbank ein."""
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        INSERT_MATERIAL,
        (material_name, einheit, preis_chf, datetime.now().strftime("%Y-%m-%d")),
    )
    conn.commit()
    conn.close()

def get_all_materials():
    """
    Gibt alle Materialeinträge aus der Datenbank zurück.
    Rückgabe:
        Liste mit Tupeln (id, material_name, einheit, preis_chf, datum_aktualisiert)
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, material_name, einheit, preis_chf, datum_aktualisiert
        FROM material;
    """)
    data = cur.fetchall()
    conn.close()
    return data

def material_exists(material_name):
    """
    Prüft, ob ein Materialname bereits existiert.
    Rückgabe:
        True, wenn vorhanden, sonst False.
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM material WHERE material_name = ?;", (material_name,))
    result = cur.fetchone()[0] > 0
    conn.close()
    return result

def clear_database():
    """
    Löscht alle Materialien aus der Tabelle und führt VACUUM aus.
    Rückgabe:
        Textmeldung ("Resetet")
    """
    conn = connect()
    try:
        # Inhalte löschen
        with conn:
            conn.execute("DELETE FROM material;")

        # VACUUM außerhalb einer Transaktion
        orig = conn.isolation_level
        conn.isolation_level = None
        conn.execute("VACUUM;")
        conn.isolation_level = orig
    finally:
        conn.close()

    return "Resetet"

def update_material(material_id, material_name, einheit, preis_chf):
    conn = connect()
    with conn:
        conn.execute(
            """
            UPDATE material
            SET material_name = ?, einheit = ?, preis_chf = ?, datum_aktualisiert = ?
            WHERE id = ?;
            """,
            (material_name, einheit, preis_chf, datetime.now().strftime("%Y-%m-%d"), material_id),
        )
    conn.close()
