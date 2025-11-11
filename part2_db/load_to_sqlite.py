from __future__ import annotations
import sqlite3
import csv
import os
import re
from pathlib import Path

BASE = Path(__file__).parent
CSV_DIR = Path(os.getenv("CSV_DIR") or (BASE.parent / "CSVs"))
DB_PATH = BASE / "ad_final.db"

INC = CSV_DIR / "incidents.csv"
DET = CSV_DIR / "details.csv"
OUT = CSV_DIR / "outcomes.csv"


def norm(s: str) -> str:
    """Normaliza headers a snake_case minúscula."""
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {
                norm(k): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            }


def to_int(x: str | None):
    try:
        return int(x) if x not in (None, "", "NA", "N/A") else None
    except ValueError:
        return None


def to_float(x: str | None):
    try:
        return float(x) if x not in (None, "", "NA", "N/A") else None
    except ValueError:
        return None


def ensure_tables(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """
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
        """
    )


def load_incidents(cur: sqlite3.Cursor) -> int:
    rows = [
        (
            r["report_id"],
            r.get("category"),
            r.get("date"),
        )
        for r in read_csv(INC)
    ]
    cur.executemany("INSERT INTO incidents VALUES (?,?,?)", rows)
    return len(rows)


def load_details(cur: sqlite3.Cursor) -> int:
    rows = [
        (
            r["report_id"],
            r.get("subject"),
            r.get("transport_mode"),
            r.get("detection"),
        )
        for r in read_csv(DET)
    ]
    cur.executemany("INSERT INTO details VALUES (?,?,?,?)", rows)
    return len(rows)


def load_outcomes(cur: sqlite3.Cursor) -> int:
    rows = [
        (
            r["report_id"],
            r.get("outcome"),
            to_int(r.get("num_ppl_fined")),
            to_float(r.get("fine")),
            to_int(r.get("num_ppl_arrested")),
            to_float(r.get("prison_time")),
            r.get("prison_time_unit"),
        )
        for r in read_csv(OUT)
    ]
    cur.executemany("INSERT INTO outcomes VALUES (?,?,?,?,?,?,?)", rows)
    return len(rows)


def create_views(cur: sqlite3.Cursor) -> None:
    cur.executescript(
        """

        DROP VIEW IF EXISTS v_pct_incidents_2018_2020;
        DROP VIEW IF EXISTS v_top3_transport_intelligence;
        DROP VIEW IF EXISTS v_detection_avg_arrested;
        DROP VIEW IF EXISTS v_category_max_prison_days;
        DROP VIEW IF EXISTS v_yearly_fines;


         (a) porc de incidentes entre 2018-01-01 y 2020-12-31

        CREATE VIEW v_pct_incidents_2018_2020 AS
        WITH totals AS (
            SELECT COUNT(*) AS total FROM incidents
        ),
        win AS (
            SELECT COUNT(*) AS in_window
            FROM incidents
            WHERE date BETWEEN '2018-01-01' AND '2020-12-31'
        )
        SELECT
            in_window AS count_2018_2020,
            total     AS count_all,
            ROUND(100.0 * in_window / total, 2) AS pct_2018_2020
        FROM totals, win;

        -- (b) Top 3 transport modes con detection = 'intelligence'
        --    (solo valores no vacíos)
        CREATE VIEW v_top3_transport_intelligence AS
        SELECT
            transport_mode,
            COUNT(*) AS n
        FROM details
        WHERE
            LOWER(TRIM(detection)) = 'intelligence'
            AND transport_mode IS NOT NULL
            AND TRIM(transport_mode) <> ''
        GROUP BY transport_mode
        ORDER BY n DESC
        LIMIT 3;

        -- (c) Métodos de detección con mayor promedio de arrestados
        CREATE VIEW v_detection_avg_arrested AS
        SELECT
            d.detection,
            ROUND(AVG(COALESCE(o.num_ppl_arrested, 0)), 2) AS avg_arrested,
            COUNT(*) AS n_reports
        FROM details d
        LEFT JOIN outcomes o USING (report_id)
        WHERE
            d.detection IS NOT NULL
            AND TRIM(d.detection) <> ''
        GROUP BY d.detection
        HAVING COUNT(*) > 0
        ORDER BY avg_arrested DESC;

        -- (d) Categorías con sentencias de prisión más largas (en días)
        CREATE VIEW v_category_max_prison_days AS
        WITH norm AS (
            SELECT
                report_id,
                CASE
                    WHEN LOWER(prison_time_unit) IN ('day','days','día','días')
                        THEN prison_time
                    WHEN LOWER(prison_time_unit) IN ('week','weeks','semana','semanas')
                        THEN prison_time * 7.0
                    WHEN LOWER(prison_time_unit) IN ('month','months','mes','meses')
                        THEN prison_time * 30.4375
                    WHEN LOWER(prison_time_unit) IN ('year','years','año','años')
                        THEN prison_time * 365.25
                    ELSE 0
                END AS prison_days
            FROM outcomes
            WHERE prison_time IS NOT NULL
        )
        SELECT
            i.category,
            ROUND(MAX(n.prison_days), 2) AS max_prison_days
        FROM incidents i
        JOIN norm n ON n.report_id = i.report_id
        WHERE
            i.category IS NOT NULL
            AND TRIM(i.category) <> ''
        GROUP BY i.category
        ORDER BY max_prison_days DESC;

        -- (e) Serie anual de multas totales
        CREATE VIEW v_yearly_fines AS
        SELECT
            year,
            total_fine
        FROM (
            SELECT
                strftime('%Y', i.date) AS year,
                ROUND(SUM(COALESCE(o.fine, 0)), 2) AS total_fine
            FROM incidents i
            LEFT JOIN outcomes o ON o.report_id = i.report_id
            WHERE i.date IS NOT NULL AND i.date <> ''
            GROUP BY year
        )
        WHERE year IS NOT NULL
        ORDER BY year;
        """
    )


def main() -> None:
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
    print(
        "Views creadas: "
        "v_pct_incidents_2018_2020, "
        "v_top3_transport_intelligence, "
        "v_detection_avg_arrested, "
        "v_category_max_prison_days, "
        "v_yearly_fines"
    )


if __name__ == "__main__":
    main()
