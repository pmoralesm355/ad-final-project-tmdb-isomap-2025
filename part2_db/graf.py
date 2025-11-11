
from pathlib import Path
import sqlite3
import matplotlib.pyplot as plt

def main():
    base = Path(__file__).resolve().parent
    db_path = base / "ad_final.db"

    if not db_path.exists():
        raise SystemExit(f"No se encontró la base de datos: {db_path}")

    plots_dir = base / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Traer categorías con sentencias (en días) mayores a 0
    query = """
        SELECT category, max_prison_days
        FROM v_category_max_prison_days
        WHERE max_prison_days > 0
        ORDER BY max_prison_days DESC;
    """
    rows = cur.execute(query).fetchall()
    con.close()

    if not rows:
        raise SystemExit("La vista v_category_max_prison_days no tiene datos > 0.")

    categories = [r[0] for r in rows]
    values = [r[1] for r in rows]

    plt.figure(figsize=(10, 5))
    y_pos = range(len(categories))

    plt.barh(y_pos, values)
    plt.yticks(y_pos, categories)
    plt.xlabel("Máxima sentencia de prisión (días)")
    plt.title("Categorías con las sentencias de prisión más largas (días)")
    plt.gca().invert_yaxis()
    plt.tight_layout()

    out_path = plots_dir / "max_prison_days_by_category.png"
    plt.savefig(out_path, dpi=300)
    plt.close()

    print(f"Gráfico guardado en: {out_path}")

if __name__ == "__main__":
    main()
