import sqlite3

DB_PATH = "cabinet_medical.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def migrate():
    """Adaugă coloane lipsă fără să șteargă datele existente."""
    with get_connection() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(pacienti)")}
        if "telefon" not in existing:
            conn.execute("ALTER TABLE pacienti ADD COLUMN telefon TEXT DEFAULT ''")
        if "email" not in existing:
            conn.execute("ALTER TABLE pacienti ADD COLUMN email TEXT DEFAULT ''")


def create_tables():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medici (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nume TEXT NOT NULL,
                specialitate TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pacienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nume TEXT NOT NULL,
                telefon TEXT,
                email TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS programari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pacient_id INTEGER NOT NULL,
                medic_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                ora TEXT NOT NULL,
                motiv TEXT,
                status TEXT DEFAULT 'Programat',
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
                tratament TEXT,
                observatii TEXT,
                FOREIGN KEY (pacient_id) REFERENCES pacienti(id),
                FOREIGN KEY (medic_id) REFERENCES medici(id)
            )
        """)
    migrate()


# ── MEDICI ────────────────────────────────────────────────────────────────────
def add_medic(nume, specialitate):
    with get_connection() as conn:
        conn.execute("INSERT INTO medici (nume, specialitate) VALUES (?, ?)", (nume, specialitate))

def get_medici():
    with get_connection() as conn:
        return conn.execute("SELECT id, nume, specialitate FROM medici ORDER BY nume").fetchall()

def delete_medic(medic_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM medici WHERE id = ?", (medic_id,))


# ── PACIENTI ──────────────────────────────────────────────────────────────────
def add_pacient(nume, telefon="", email=""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO pacienti (nume, telefon, email) VALUES (?, ?, ?)",
            (nume, telefon, email)
        )

def get_pacienti():
    with get_connection() as conn:
        return conn.execute("SELECT id, nume, telefon, email FROM pacienti ORDER BY nume").fetchall()

def delete_pacient(pacient_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM pacienti WHERE id = ?", (pacient_id,))


# ── PROGRAMARI ────────────────────────────────────────────────────────────────
def add_programare(pacient_id, medic_id, data, ora, motiv=""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO programari (pacient_id, medic_id, data, ora, motiv) VALUES (?, ?, ?, ?, ?)",
            (pacient_id, medic_id, str(data), ora, motiv)
        )

def get_programari_by_medic_data(medic_id, data):
    with get_connection() as conn:
        return conn.execute("""
            SELECT pr.id, pa.nume, pr.ora, pr.motiv, pr.status
            FROM programari pr
            JOIN pacienti pa ON pa.id = pr.pacient_id
            WHERE pr.medic_id = ? AND pr.data = ?
            ORDER BY pr.ora
        """, (medic_id, str(data))).fetchall()

def get_all_programari():
    with get_connection() as conn:
        return conn.execute("""
            SELECT pr.id, pa.nume, m.nume, m.specialitate, pr.data, pr.ora, pr.motiv, pr.status
            FROM programari pr
            JOIN pacienti pa ON pa.id = pr.pacient_id
            JOIN medici m ON m.id = pr.medic_id
            ORDER BY pr.data, pr.ora
        """).fetchall()

def update_status_programare(programare_id, status):
    with get_connection() as conn:
        conn.execute("UPDATE programari SET status = ? WHERE id = ?", (status, programare_id))

def delete_programare(programare_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM programari WHERE id = ?", (programare_id,))

def is_slot_ocupat(medic_id, data, ora, exclude_id=None):
    with get_connection() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT id FROM programari WHERE medic_id=? AND data=? AND ora=? AND id!=?",
                (medic_id, str(data), ora, exclude_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM programari WHERE medic_id=? AND data=? AND ora=?",
                (medic_id, str(data), ora)
            ).fetchone()
        return row is not None


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
            SELECT ist.id, pa.nume, m.nume, m.specialitate, ist.data, ist.diagnostic, ist.tratament, ist.observatii
            FROM istoric ist
            JOIN pacienti pa ON pa.id = ist.pacient_id
            JOIN medici m ON m.id = ist.medic_id
            WHERE 1=1
        """
        params = []
        if pacient_id:
            query += " AND ist.pacient_id = ?"
            params.append(pacient_id)
        if medic_id:
            query += " AND ist.medic_id = ?"
            params.append(medic_id)
        query += " ORDER BY ist.data DESC"
        return conn.execute(query, params).fetchall()
