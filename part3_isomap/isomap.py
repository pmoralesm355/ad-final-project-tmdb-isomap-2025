from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def find_isomap_dat(base: Path) -> Path:

    env_path = os.getenv("ISOMAP_DATA_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))

    candidates.extend([
        base / "isomap.dat",
        base.parent / "isomap.dat",
        base.parent.parent / "isomap.dat",
    ])

    for p in candidates:
        if p.is_file():
            return p

    raise SystemExit(

    )


def load_isomap_faces(path: Path, img_h: int = 64, img_w: int = 64) -> np.ndarray:

    if not path.exists():
        raise SystemExit(f"No encuentro archivo de datos: {path}")

    data = np.fromfile(path, dtype=np.uint16)
    pix_per_img = img_h * img_w

    if data.size % pix_per_img != 0:
        raise SystemExit(
            f"Tamaño inesperado en {path.name}: {data.size} valores, "
            f"no divisible entre {pix_per_img} = 64*64."
        )

    n_samples = data.size // pix_per_img
    X = data.reshape((n_samples, pix_per_img)).astype("float64")

    max_val = X.max()
    if max_val > 0:
        X /= max_val

    print(f"[DATA] isomap.dat -> {n_samples} imágenes de {img_h}x{img_w}")
    return X


def pairwise_distances(X: np.ndarray) -> np.ndarray:
    """
    Distancia euclidiana por pares (matriz NxN).
    """
    # ||x||^2
    XX = np.sum(X * X, axis=1, keepdims=True)
    # (x_i - x_j)^2 = ||x_i||^2 + ||x_j||^2 - 2 x_i · x_j
    D2 = XX + XX.T - 2.0 * X.dot(X.T)
    np.maximum(D2, 0.0, out=D2)
    return np.sqrt(D2)


def build_neighborhood_graph(D: np.ndarray,
                             n_neighbors: int = 7,
                             radius: float | None = None) -> np.ndarray:
    """
    Construye el grafo de vecindad:
    - Si radius se da: conecta pares con d <= radius.
    - Si no: k-vecinos más cercanos (simétrico).
    Retorna matriz de pesos
    """
    n = D.shape[0]
    INF = float("inf")
    G = np.full_like(D, INF, dtype=float)
    np.fill_diagonal(G, 0.0)

    if radius is not None:
        for i in range(n):
            for j in range(n):
                if i != j and D[i, j] <= radius:
                    G[i, j] = D[i, j]
    else:
        for i in range(n):
            idx = np.argsort(D[i])
            for j in idx[1:n_neighbors + 1]:
                G[i, j] = D[i, j]

    # grafo no dirigido:  mínima distancia simétrica
    G = np.minimum(G, G.T)
    return G


def check_connectivity(G: np.ndarray) -> bool:
    """
    Verificda si el grafo es conexo usando una búsqueda simple.
    """
    n = G.shape[0]
    INF = float("inf")
    vistos = {0}
    pila = [0]

    while pila:
        i = pila.pop()
        # vecinos con arista finita
        vecinos = np.where(G[i] < INF)[0]
        for j in vecinos:
            if j not in vistos:
                vistos.add(j)
                pila.append(j)

    if len(vistos) == n:
        print("[ISOMAP] Grafo conexo OK.")
        return True
    else:
        print(f"[ISOMAP][WARN] Grafo NO conexo: {len(vistos)}/{n} nodos alcanzables.")
        return False


def floyd_warshall(G: np.ndarray) -> np.ndarray:
    """
    Distancias geodésicas mediante Floyd-Warshall.
    Complejidad O(N^3), pero N ~ 349 -> OK.
    """
    n = G.shape[0]
    D = G.copy()
    for k in range(n):
        # broadcasting: compara con caminos pasando por k
        D = np.minimum(D, D[:, [k]] + D[[k], :])
    return D


def classical_mds(D: np.ndarray, n_components: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """
    MDS clásico sobre matriz de distancias D (NxN).
    Retorna:
      - Y: embedding (N x n_components)
      - vals: autovalores completos (para ver varianza explicada)
    """
    n = D.shape[0]
    D2 = D ** 2

    # Matriz de centrado
    J = np.eye(n) - np.ones((n, n)) / n

    # Matriz de Gram
    B = -0.5 * J.dot(D2).dot(J)

    # Autovalores/autovectores
    vals, vecs = np.linalg.eigh(B)
    idx = np.argsort(vals)[::-1]
    vals = vals[idx]
    vecs = vecs[:, idx]

    # Tomamos componentes con autovalores positivos
    pos = np.clip(vals[:n_components], a_min=0, a_max=None)
    L = np.sqrt(pos)
    Y = vecs[:, :n_components] * L

    return Y, vals


def isomap(X: np.ndarray,
           n_neighbors: int = 7,
           n_components: int = 2,
           radius: float | None = None) -> tuple[np.ndarray, np.ndarray]:

    n, d = X.shape
    print(f"[ISOMAP] n_samples={n}, n_features={d}, k={n_neighbors}, dim={n_components}")

    print("[ISOMAP] Paso 1: distancias euclidianas...")
    D = pairwise_distances(X)

    print("[ISOMAP] Paso 2: grafo de vecindad...")
    G = build_neighborhood_graph(D, n_neighbors=n_neighbors, radius=radius)
    check_connectivity(G)

    print("[ISOMAP] Paso 3: distancias geodésicas (Floyd-Warshall)...")
    D_geo = floyd_warshall(G)

    print("[ISOMAP] Paso 4: MDS clásico...")
    Y, vals = classical_mds(D_geo, n_components=n_components)
    print("[ISOMAP] Autovalores principales:", np.round(vals[:5], 4))

    return Y, vals



if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    plots_dir = base / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    data_path = find_isomap_dat(base)
    X = load_isomap_faces(data_path)

    Y, vals = isomap(X, n_neighbors=7, n_components=2)

    plt.figure(figsize=(8, 6))
    n = Y.shape[0]
    scatter = plt.scatter(
        Y[:, 0],
        Y[:, 1],
        c=np.arange(n),
        cmap="viridis",
        s=18,
        edgecolors="none"
    )
    plt.title("ISOMAP 2D embedding - isomap.dat")
    plt.xlabel("Dimensión 1")
    plt.ylabel("Dimensión 2")
    plt.colorbar(scatter, label="Índice de imagen")
    plt.tight_layout()

    out_path = plots_dir / "isomap_faces_embedding.png"
    plt.savefig(out_path, dpi=300)
    print(f"[ISOMAP] Embedding guardado en: {out_path}")
