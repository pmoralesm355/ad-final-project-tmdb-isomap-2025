from __future__ import annotations
import sqlite3, csv, os, re
from pathlib import Path

# Paths
BASE = Path(__file__).parent
CSV_DIR = Path(os.getenv("CSV_DIR") or (BASE.parent / "CSVs"))
DB_PATH = BASE / "ad_final.db"

INC = CSV_DIR / "incidents.csv"
DET = CSV_DIR / "details.csv"
OUT = CSV_DIR / "outcomes.csv"

def norm(s: str) -> str:
    """Normaliza headers: minuscula + '_'."""
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")

def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            yield {
                norm(k): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            }

def to_int(x: str | None):
    try:
        return int(x) if x not in (None, "", "NA", "N/A") else None
    except:
        return None

def to_float(x: str | None):
    try:
        return float(x) if x not in (None, "", "NA", "N/A") else None
    except:
        return None

def ensure_tables(cur: sqlite3.Cursor):
    cur.executescript("""
    DROP TABLE IF EXISTS incidents;
    CREATE TABLE incidents(
        report_id TEXT,
        category TEXT,
        date TEXT
    );

    DROP TABLE IF EXISTS details;
    CREATE TABLE details(
        report_id TEXT,
        subject TEXT,
        transport_mode TEXT,
        detection TEXT
    );

    DROP TABLE IF EXISTS outcomes;
    CREATE TABLE outcomes(
        report_id TEXT,
        outcome TEXT,
        num_ppl_fined INTEGER,
        fine REAL,
        num_ppl_arrested INTEGER,
        prison_time REAL,
        prison_time_unit TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_incidents_report ON incidents(report_id);
    CREATE INDEX IF NOT EXISTS idx_details_report   ON details(report_id);
    CREATE INDEX IF NOT EXISTS idx_outcomes_report  ON outcomes(report_id);
    """)

def load_incidents(cur: sqlite3.Cursor) -> int:
    rows = []
    for r in read_csv(INC):
        rows.append((
            r["report_id"],
            r.get("category"),
            r.get("date"),
        ))
    cur.executemany("INSERT INTO incidents VALUES (?,?,?)", rows)
    return len(rows)

def load_details(cur: sqlite3.Cursor) -> int:
    rows = []
    for r in read_csv(DET):
        rows.append((
            r["report_id"],
            r.get("subject"),
            r.get("transport_mode"),
            r.get("detection"),
        ))
    cur.executemany("INSERT INTO details VALUES (?,?,?,?)", rows)
    return len(rows)

def load_outcomes(cur: sqlite3.Cursor) -> int:
    rows = []
    for r in read_csv(OUT):
        rows.append((
            r["report_id"],
            r.get("outcome"),
            to_int(r.get("num_ppl_fined")),
            to_float(r.get("fine")),
            to_int(r.get("num_ppl_arrested")),
            to_float(r.get("prison_time")),
            r.get("prison_time_unit"),
        ))
    cur.executemany("INSERT INTO outcomes VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)

def create_views(cur: sqlite3.Cursor):
    cur.executescript("""
    -- (a) % incidentes 2018-01-01 a 2020-12-31
    CREATE VIEW IF NOT EXISTS v_pct_incidents_2018_2020 AS
    WITH totals AS (SELECT COUNT(*) AS total FROM incidents),
    win AS (
      SELECT COUNT(*) AS in_window
      FROM incidents
      WHERE date BETWEEN '2018-01-01' AND '2020-12-31'
    )
    SELECT in_window AS count_2018_2020,
           total     AS count_all,
           ROUND(100.0 * in_window / total, 2) AS pct_2018_2020
    FROM totals, win;

    -- (b) Top 3 transportes con detection='intelligence'
    CREATE VIEW IF NOT EXISTS v_top3_transport_intelligence AS
    SELECT transport_mode, COUNT(*) AS n
    FROM details
    WHERE LOWER(detection)='intelligence'
    GROUP BY transport_mode
    ORDER BY n DESC
    LIMIT 3;

    -- (c) Métodos de detección con mayor promedio de arrestados
    CREATE VIEW IF NOT EXISTS v_detection_avg_arrested AS
    SELECT d.detection,
           ROUND(AVG(COALESCE(o.num_ppl_arrested,0)),2) AS avg_arrested,
           COUNT(*) AS n_reports
    FROM details d
    LEFT JOIN outcomes o USING(report_id)
    GROUP BY d.detection
    ORDER BY avg_arrested DESC;

    -- (d) Categorías con sentencias más largas (prison_time -> días)
    CREATE VIEW IF NOT EXISTS v_category_max_prison_days AS
    WITH norm AS (
      SELECT report_id,
             CASE
               WHEN LOWER(prison_time_unit) IN ('day','days','día','días')
                    THEN prison_time
               WHEN LOWER(prison_time_unit) IN ('week','weeks','semana','semanas')
                    THEN prison_time*7.0
               WHEN LOWER(prison_time_unit) IN ('month','months','mes','meses')
                    THEN prison_time*30.4375
               WHEN LOWER(prison_time_unit) IN ('year','years','año','años')
                    THEN prison_time*365.25
               ELSE 0
             END AS prison_days
      FROM outcomes
      WHERE prison_time IS NOT NULL
    )
    SELECT i.category,
           ROUND(MAX(n.prison_days),2) AS max_prison_days
    FROM incidents i
    JOIN norm n ON n.report_id=i.report_id
    GROUP BY i.category
    ORDER BY max_prison_days DESC;

    -- (e) Serie anual de multas
    CREATE VIEW IF NOT EXISTS v_yearly_fines AS
    SELECT strftime('%Y', i.date) AS year,
           ROUND(SUM(COALESCE(o.fine,0)),2) AS total_fine
    FROM incidents i
    LEFT JOIN outcomes o ON o.report_id=i.report_id
    GROUP BY year
    ORDER BY year;
    """)

def main():
    if not CSV_DIR.exists():
        raise SystemExit(f"No encuentro carpeta CSVs: {CSV_DIR}")
    for p in (INC, DET, OUT):
        if not p.exists():
            raise SystemExit(f"No encuentro archivo: {p}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    ensure_tables(cur)
    n1 = load_incidents(cur)
    n2 = load_details(cur)
    n3 = load_outcomes(cur)
    create_views(cur)

    con.commit()
    con.close()

    print(f"DB lista: {DB_PATH}")
    print(f"incidents: {n1} filas | details: {n2} | outcomes: {n3}")
    print("Views creadas: v_pct_incidents_2018_2020, v_top3_transport_intelligence, "
          "v_detection_avg_arrested, v_category_max_prison_days, v_yearly_fines")

if __name__ == "__main__":
    main()