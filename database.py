import sqlite3
import hashlib
import os

DB_PATH = "cabinet_medical.db"

MEDIC_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
    "#9b59b6", "#1abc9c", "#e67e22", "#34495e"
]


def get_connection():
    return sqlite3.connect(DB_PATH)


def migrate():
    with get_connection() as conn:
        # pacienti
        cols = {row[1] for row in conn.execute("PRAGMA table_info(pacienti)")}
        if "telefon" not in cols:
            conn.execute("ALTER TABLE pacienti ADD COLUMN telefon TEXT DEFAULT ''")
        if "email" not in cols:
            conn.execute("ALTER TABLE pacienti ADD COLUMN email TEXT DEFAULT ''")
        if "data_nasterii" not in cols:
            conn.execute("ALTER TABLE pacienti ADD COLUMN data_nasterii TEXT DEFAULT ''")

        # programari
        cols = {row[1] for row in conn.execute("PRAGMA table_info(programari)")}
        if "durata" not in cols:
            conn.execute("ALTER TABLE programari ADD COLUMN durata INTEGER DEFAULT 30")
        if "nota_anulare" not in cols:
            conn.execute("ALTER TABLE programari ADD COLUMN nota_anulare TEXT DEFAULT ''")

        # medici
        cols = {row[1] for row in conn.execute("PRAGMA table_info(medici)")}
        if "culoare" not in cols:
            conn.execute("ALTER TABLE medici ADD COLUMN culoare TEXT DEFAULT '#3498db'")


def create_tables():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS utilizatori (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                rol TEXT DEFAULT 'receptionist'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medici (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nume TEXT NOT NULL,
                specialitate TEXT NOT NULL,
                culoare TEXT DEFAULT '#3498db'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pacienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nume TEXT NOT NULL,
                telefon TEXT DEFAULT '',
                email TEXT DEFAULT '',
                data_nasterii TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS programari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacient_id INTEGER NOT NULL,
                medic_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                ora TEXT NOT NULL,
                durata INTEGER DEFAULT 30,
                motiv TEXT DEFAULT '',
                status TEXT DEFAULT 'Programat',
                nota_anulare TEXT DEFAULT '',
                FOREIGN KEY (pacient_id) REFERENCES pacienti(id),
                FOREIGN KEY (medic_id) REFERENCES medici(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS istoric (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacient_id INTEGER NOT NULL,
                medic_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                diagnostic TEXT NOT NULL,
                tratament TEXT DEFAULT '',
                observatii TEXT DEFAULT '',
                FOREIGN KEY (pacient_id) REFERENCES pacienti(id),
                FOREIGN KEY (medic_id) REFERENCES medici(id)
            )
        """)
    migrate()
    _create_admin_default()


def _create_admin_default():
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM utilizatori WHERE username='admin'").fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO utilizatori (username, password_hash, rol) VALUES (?, ?, ?)",
                ("admin", _hash("admin123"), "admin")
            )


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── AUTENTIFICARE ─────────────────────────────────────────────────────────────
def verify_user(username, password):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, rol FROM utilizatori WHERE username=? AND password_hash=?",
            (username, _hash(password))
        ).fetchone()
        return row

def add_utilizator(username, password, rol="receptionist"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO utilizatori (username, password_hash, rol) VALUES (?, ?, ?)",
            (username, _hash(password), rol)
        )

def get_utilizatori():
    with get_connection() as conn:
        return conn.execute("SELECT id, username, rol FROM utilizatori ORDER BY username").fetchall()

def delete_utilizator(uid):
    with get_connection() as conn:
        conn.execute("DELETE FROM utilizatori WHERE id=? AND username!='admin'", (uid,))

def change_password(username, new_password):
    with get_connection() as conn:
        conn.execute(
            "UPDATE utilizatori SET password_hash=? WHERE username=?",
            (_hash(new_password), username)
        )


# ── MEDICI ────────────────────────────────────────────────────────────────────
def add_medic(nume, specialitate, culoare="#3498db"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO medici (nume, specialitate, culoare) VALUES (?, ?, ?)",
            (nume, specialitate, culoare)
        )

def get_medici():
    with get_connection() as conn:
        return conn.execute("SELECT id, nume, specialitate, culoare FROM medici ORDER BY nume").fetchall()

def delete_medic(medic_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM medici WHERE id=?", (medic_id,))


# ── PACIENTI ──────────────────────────────────────────────────────────────────
def add_pacient(nume, telefon="", email="", data_nasterii=""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO pacienti (nume, telefon, email, data_nasterii) VALUES (?, ?, ?, ?)",
            (nume, telefon, email, data_nasterii)
        )

def get_pacienti():
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, nume, telefon, email, data_nasterii FROM pacienti ORDER BY nume"
        ).fetchall()

def search_pacienti(query):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, nume, telefon, email, data_nasterii FROM pacienti WHERE nume LIKE ? ORDER BY nume",
            (f"%{query}%",)
        ).fetchall()

def delete_pacient(pacient_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM pacienti WHERE id=?", (pacient_id,))


# ── PROGRAMARI ────────────────────────────────────────────────────────────────
def add_programare(pacient_id, medic_id, data, ora, motiv="", durata=30):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO programari (pacient_id, medic_id, data, ora, motiv, durata) VALUES (?, ?, ?, ?, ?, ?)",
            (pacient_id, medic_id, str(data), ora, motiv, durata)
        )

def get_programari_by_medic_data(medic_id, data):
    with get_connection() as conn:
        return conn.execute("""
            SELECT pr.id, pa.nume, pr.ora, pr.motiv, pr.status, pr.durata, pa.telefon
            FROM programari pr
            JOIN pacienti pa ON pa.id = pr.pacient_id
            WHERE pr.medic_id=? AND pr.data=?
            ORDER BY pr.ora
        """, (medic_id, str(data))).fetchall()

def get_all_programari():
    with get_connection() as conn:
        return conn.execute("""
            SELECT pr.id, pa.nume, m.nume, m.specialitate, pr.data, pr.ora, pr.motiv, pr.status, pr.durata
            FROM programari pr
            JOIN pacienti pa ON pa.id = pr.pacient_id
            JOIN medici m ON m.id = pr.medic_id
            ORDER BY pr.data, pr.ora
        """).fetchall()

def get_programari_azi():
    from datetime import date
    azi = str(date.today())
    with get_connection() as conn:
        return conn.execute("""
            SELECT pr.id, pa.nume, m.nume, pr.ora, pr.status, pr.motiv
            FROM programari pr
            JOIN pacienti pa ON pa.id = pr.pacient_id
            JOIN medici m ON m.id = pr.medic_id
            WHERE pr.data=?
            ORDER BY pr.ora
        """, (azi,)).fetchall()

def get_stats():
    with get_connection() as conn:
        from datetime import date
        azi = str(date.today())
        total_pacienti = conn.execute("SELECT COUNT(*) FROM pacienti").fetchone()[0]
        total_medici = conn.execute("SELECT COUNT(*) FROM medici").fetchone()[0]
        programari_azi = conn.execute("SELECT COUNT(*) FROM programari WHERE data=?", (azi,)).fetchone()[0]
        programari_luna = conn.execute(
            "SELECT COUNT(*) FROM programari WHERE data LIKE ?", (azi[:7] + "%",)
        ).fetchone()[0]
        anulate = conn.execute(
            "SELECT COUNT(*) FROM programari WHERE status='Anulat' AND data=?", (azi,)
        ).fetchone()[0]
        return {
            "total_pacienti": total_pacienti,
            "total_medici": total_medici,
            "programari_azi": programari_azi,
            "programari_luna": programari_luna,
            "anulate_azi": anulate,
        }

def get_stats_per_medic():
    with get_connection() as conn:
        return conn.execute("""
            SELECT m.nume, m.specialitate, COUNT(pr.id) as total,
                   SUM(CASE WHEN pr.status='Finalizat' THEN 1 ELSE 0 END) as finalizate,
                   SUM(CASE WHEN pr.status='Anulat' THEN 1 ELSE 0 END) as anulate
            FROM medici m
            LEFT JOIN programari pr ON pr.medic_id = m.id
            GROUP BY m.id
            ORDER BY total DESC
        """).fetchall()

def update_status_programare(programare_id, status, nota_anulare=""):
    with get_connection() as conn:
        conn.execute(
            "UPDATE programari SET status=?, nota_anulare=? WHERE id=?",
            (status, nota_anulare, programare_id)
        )

def delete_programare(programare_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM programari WHERE id=?", (programare_id,))

def is_slot_ocupat(medic_id, data, ora, durata=30, exclude_id=None):
    with get_connection() as conn:
        query = "SELECT id FROM programari WHERE medic_id=? AND data=? AND ora=?"
        params = [medic_id, str(data), ora]
        if exclude_id:
            query += " AND id!=?"
            params.append(exclude_id)
        return conn.execute(query, params).fetchone() is not None


# ── ISTORIC ───────────────────────────────────────────────────────────────────
def add_istoric(pacient_id, medic_id, data, diagnostic, tratament="", observatii=""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO istoric (pacient_id, medic_id, data, diagnostic, tratament, observatii) VALUES (?, ?, ?, ?, ?, ?)",
            (pacient_id, medic_id, str(data), diagnostic, tratament, observatii)
        )

def get_istoric(pacient_id=None, medic_id=None):
    with get_connection() as conn:
        query = """
            SELECT ist.id, pa.nume, m.nume, m.specialitate, ist.data,
                   ist.diagnostic, ist.tratament, ist.observatii
            FROM istoric ist
            JOIN pacienti pa ON pa.id = ist.pacient_id
            JOIN medici m ON m.id = ist.medic_id
            WHERE 1=1
        """
        params = []
        if pacient_id:
            query += " AND ist.pacient_id=?"
            params.append(pacient_id)
        if medic_id:
            query += " AND ist.medic_id=?"
            params.append(medic_id)
        query += " ORDER BY ist.data DESC"
        return conn.execute(query, params).fetchall()
