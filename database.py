import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "keys.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            hwid TEXT,
            uses_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_used TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def create_key(key: str, username: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute("""
            INSERT INTO licenses (key, username, hwid, uses_count, created_at, last_used, is_active)
            VALUES (?, ?, NULL, 0, ?, NULL, 1)
        """, (key, username, now))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_key_info(identifier: str):
    """Busca por key exacta o por nombre de usuario."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM licenses 
        WHERE key = ? OR LOWER(username) = LOWER(?)
    """, (identifier, identifier))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_keys():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM licenses ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def reset_hwid(identifier: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE licenses 
        SET hwid = NULL 
        WHERE key = ? OR LOWER(username) = LOWER(?)
    """, (identifier, identifier))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def revoke_key(identifier: str) -> bool:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE licenses 
        SET is_active = 0 
        WHERE key = ? OR LOWER(username) = LOWER(?)
    """, (identifier, identifier))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def verify_and_consume_key(key: str, client_hwid: str) -> dict:
    """
    Verifica una llave contra el HWID del cliente:
    - Si la key no existe o está desactivada -> error
    - Si la key no tiene HWID -> vincula el HWID actual a la cuenta
    - Si tiene HWID y coincide -> actualiza last_used y suma un uso
    - Si tiene HWID pero no coincide -> mismatch
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM licenses WHERE key = ?", (key,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": "Llave inexistente."}

    license_data = dict(row)
    if not license_data["is_active"]:
        conn.close()
        return {"status": "error", "message": "Esta llave ha sido desactivada/revocada."}

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Si es el primer uso de la llave, vincular su HWID
    if not license_data["hwid"]:
        cursor.execute("""
            UPDATE licenses 
            SET hwid = ?, uses_count = uses_count + 1, last_used = ? 
            WHERE key = ?
        """, (client_hwid, now, key))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": "HWID vinculado exitosamente por primera vez.",
            "username": license_data["username"],
            "uses_count": license_data["uses_count"] + 1,
            "last_used": now
        }

    # Si ya tiene HWID, verificar que sea la misma máquina
    if license_data["hwid"] != client_hwid:
        conn.close()
        return {
            "status": "error",
            "message": "HWID no coincide. Esta llave está asignada a otro equipo."
        }

    # HWID válido: registrar acceso
    cursor.execute("""
        UPDATE licenses 
        SET uses_count = uses_count + 1, last_used = ? 
        WHERE key = ?
    """, (now, key))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Acceso concedido.",
        "username": license_data["username"],
        "uses_count": license_data["uses_count"] + 1,
        "last_used": now
    }
