# terrain.py
import numpy as np
import random
import math
import config
from monstre import Monstre

arbres_caches = {}
monstres_caches = {}
chest_caches = {}

# =============================================================
#  Helpers orientation / terrain
# =============================================================

def get_hauteur_sol(monde_x, monde_z):
    gx = monde_x / config.ECHELLE_GRILLE
    gz = monde_z / config.ECHELLE_GRILLE
    base = np.sin(gx * 0.05) * np.cos(gz * 0.05) * 2.0
    detail = np.sin(gx * 0.15) * np.sin(gz * 0.15) * 0.4
    return -(base + detail) * config.EVAL_HAUTEUR


def _get_normale_sol(monde_x, monde_z, epsilon=0.4):
    """Normale unitaire du sol à (x,z) par différences finies."""
    hL = get_hauteur_sol(monde_x - epsilon, monde_z)
    hR = get_hauteur_sol(monde_x + epsilon, monde_z)
    hD = get_hauteur_sol(monde_x, monde_z - epsilon)
    hU = get_hauteur_sol(monde_x, monde_z + epsilon)
    dx = (hR - hL) / (2.0 * epsilon)
    dz = (hU - hD) / (2.0 * epsilon)
    n = np.array([-dx, 1.0, -dz], dtype=np.float64)
    return n / (np.linalg.norm(n) + 1e-9)


def _matrice_alignement(up, normale, yaw):
    """
    Matrice 3x3 telle que :
      - l'axe local Y soit aligné sur `normale` (la pente du terrain),
      - un yaw (rotation autour de cet axe local) soit appliqué ensuite.
    """
    up = up / (np.linalg.norm(up) + 1e-9)
    normale = normale / (np.linalg.norm(normale) + 1e-9)

    d = float(np.clip(np.dot(up, normale), -1.0, 1.0))
    if d > 0.9999:
        x, y, z, w = 0.0, 0.0, 0.0, 1.0
    elif d < -0.9999:
        axis = np.cross(up, np.array([1.0, 0.0, 0.0]))
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(up, np.array([0.0, 0.0, 1.0]))
        axis /= np.linalg.norm(axis)
        x, y, z, w = float(axis[0]), float(axis[1]), float(axis[2]), 0.0
    else:
        axis = np.cross(up, normale)
        s = math.sqrt((1.0 + d) * 2.0)
        inv = 1.0 / s
        x, y, z, w = float(axis[0] * inv), float(axis[1] * inv), float(axis[2] * inv), s * 0.5

    R_align = np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w),     2*(x*z + y*w)],
        [2*(x*y + z*w),     1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w),     2*(y*z + x*w),     1 - 2*(x*x + y*y)],
    ], dtype=np.float64)

    c, s = math.cos(yaw), math.sin(yaw)
    R_yaw = np.array([[c, 0.0, s],
                      [0.0, 1.0, 0.0],
                      [-s, 0.0, c]], dtype=np.float64)

    return R_align @ R_yaw


# =============================================================
#  Recherche d'emplacement pour un coffre
# =============================================================

def _trouver_position_coffre(rand_gen, cx, cz, arbres, autres_coffres, marge):
    """
    Cherche une position (x,z) dans le chunk pour un coffre.
    Essaie des contraintes de plus en plus permissives.
    """
    taille = config.TAILLE_CHUNKS
    if taille <= 2 * marge:
        gmin, gmax = 0, taille  # chunk minuscule : pas de marge
    else:
        gmin, gmax = marge, taille - marge

    paliers = [
        (0.65, 2.0, 3.0, 24),
        (0.50, 1.5, 2.0, 16),
        (0.30, 1.0, 1.5, 10),
        (0.00, 0.0, 0.0, 6),  # dernier palier : AUCUNE contrainte (sauf normale)
    ]
    for min_dot, d_arbre, d_coffre, essais in paliers:
        for _ in range(essais):
            gx = rand_gen.randint(gmin, gmax)
            gz = rand_gen.randint(gmin, gmax)
            mx = (cx * taille + gx) * config.ECHELLE_GRILLE
            mz = (cz * taille + gz) * config.ECHELLE_GRILLE

            n = _get_normale_sol(mx, mz)
            if n[1] < min_dot:
                continue

            ok = True
            if d_arbre > 0:
                for ax, az in arbres:
                    if math.hypot(mx - ax, mz - az) < d_arbre * config.ECHELLE_GRILLE:
                        ok = False
                        break
            if not ok:
                continue

            if d_coffre > 0:
                for ox, oz in autres_coffres:
                    if math.hypot(mx - ox, mz - oz) < d_coffre * config.ECHELLE_GRILLE:
                        ok = False
                        break
            if not ok:
                continue

            return mx, mz
    return None


# =============================================================
#  Génération du contenu d'un chunk
# =============================================================

# =============================================================
#  Génération du contenu d'un chunk
# =============================================================

def get_elements_chunk(cx, cz):
    cle = (cx, cz)
    if cle in arbres_caches and cle in monstres_caches and cle in chest_caches:
        return arbres_caches[cle], monstres_caches[cle], chest_caches[cle]

    # RNG séparés par type d'élément → indépendants entre eux
    base_seed = (cx * 73856093) ^ (cz * 19349663)
    rng_arbre   = random.Random(base_seed ^ 0xA1B2C3)
    rng_coffre  = random.Random(base_seed ^ 0xC0FFEE)
    rng_monstre = random.Random(base_seed ^ 0xDEADBE)

    taille = config.TAILLE_CHUNKS
    marge = max(1, min(2, taille // 4))

    # ---------- Arbres ----------
    arbres_chunk = []
    for _ in range(2):
        for _ in range(10):
            ax = (cx * taille + rng_arbre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE
            az = (cz * taille + rng_arbre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE
            if not any(math.hypot(ax - x, az - z) < 3.0 * config.ECHELLE_GRILLE for x, z in arbres_chunk):
                arbres_chunk.append((ax, az))
                break
    arbres_caches[cle] = arbres_chunk

    # ---------- Coffres ----------
    chest_chunk = []
    positions_chests = []
    nb_coffres = rng_coffre.randint(1, 2)

    for _ in range(nb_coffres):
        pos = _trouver_position_coffre(rng_coffre, cx, cz, arbres_chunk, positions_chests, marge)
        if pos is None:
            # Fallback forcé : une position aléatoire quelconque dans le chunk
            gx = rng_coffre.randint(0, taille)
            gz = rng_coffre.randint(0, taille)
            mx = (cx * taille + gx) * config.ECHELLE_GRILLE
            mz = (cz * taille + gz) * config.ECHELLE_GRILLE
            pos = (mx, mz)
        mx, mz = pos
        positions_chests.append((mx, mz))

        # 15% de chance d'avoir un coffre prismatique
        is_prismatic = rng_coffre.random() < 0.15
        type_coffre = "PRISMATIC_CHEST" if is_prismatic else "MODELE_CHEST"

        normale = _get_normale_sol(mx, mz)
        y = float(get_hauteur_sol(mx, mz))
        yaw = rng_coffre.uniform(0.0, 2.0 * math.pi)
        rotation = _matrice_alignement(np.array([0.0, 1.0, 0.0]), normale, yaw)

        chest_chunk.append({
            "x": mx,
            "y": y,
            "z": mz,
            "type": type_coffre,
            "ouvert": False,
            "item_spawned": None,
            "normale": normale,
            "rotation": rotation,
            "yaw": yaw,
        })
    chest_caches[cle] = chest_chunk

    # ---------- Monstres ----------
    monstres_chunk = []
    for _ in range(2):
        for _ in range(12):
            mx = (cx * taille + rng_monstre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE
            mz = (cz * taille + rng_monstre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE

            if math.hypot(mx - config.DEPART_X, mz - config.DEPART_Z) < config.ZONE_SECURITE_DEPART:
                continue
            if any(math.hypot(mx - x, mz - z) < 2.0 * config.ECHELLE_GRILLE for x, z in arbres_chunk):
                continue
            if any(math.hypot(mx - c["x"], mz - c["z"]) < 2.0 * config.ECHELLE_GRILLE for c in chest_chunk):
                continue

            tipo = rng_monstre.randint(0, 1)
            monstres_chunk.append(Monstre(mx, mz, tipo, rng_monstre))
            break
    monstres_caches[cle] = monstres_chunk

    return arbres_caches[cle], monstres_caches[cle], chest_caches[cle]


# =============================================================
#  Géométrie / zone
# =============================================================

_cache_geo_chunks = {}
_zone_cache = {"cle": None, "zone": None}


def _geo_chunk(cx, cz):
    cle = (cx, cz)
    if cle not in _cache_geo_chunks:
        taille = config.TAILLE_CHUNKS * config.ECHELLE_GRILLE
        pas = np.arange(0, config.TAILLE_CHUNKS + 1, config.PAS_GRILLE) * config.ECHELLE_GRILLE
        xs = pas + cx * taille
        zs = pas + cz * taille
        gx, gz = np.meshgrid(xs, zs)
        gx, gz = gx.ravel(), gz.ravel()
        gy = get_hauteur_sol(gx, gz)
        pts = np.column_stack((gx, gy, gz)).astype(np.float32)

        nb = len(xs)
        lz, lx = np.meshgrid(np.arange(nb - 1), np.arange(nb - 1), indexing='ij')
        lz, lx = lz.ravel(), lx.ravel()
        a = lz * nb + lx
        b = lz * nb + lx + 1
        c = (lz + 1) * nb + lx + 1
        d = (lz + 1) * nb + lx
        _cache_geo_chunks[cle] = (pts, a, b, c, d)
    return _cache_geo_chunks[cle]


def get_zone(cam_cx, cam_cz, portee):
    """Retourne la zone autour de la caméra (reconstruite seulement quand on change de chunk)."""
    cle = (cam_cx, cam_cz, portee)
    if _zone_cache["cle"] == cle:
        return _zone_cache["zone"]

    pts_l, A, B, C, D, cles, arbres, chests = [], [], [], [], [], [], [], []
    decalage = 0
    for cx in range(cam_cx - portee, cam_cx + portee + 1):
        for cz in range(cam_cz - portee, cam_cz + portee + 1):
            pts, a, b, c, d = _geo_chunk(cx, cz)
            pts_l.append(pts)
            A.append(a + decalage); B.append(b + decalage)
            C.append(c + decalage); D.append(d + decalage)
            decalage += len(pts)

            arbres_chunk, _, chest_chunk = get_elements_chunk(cx, cz)
            arbres.extend(arbres_chunk)
            chests.extend(chest_chunk)
            cles.append((cx, cz))

    if arbres:
        ax = np.array([p[0] for p in arbres], dtype=np.float64)
        az = np.array([p[1] for p in arbres], dtype=np.float64)
        bases_arbres = np.column_stack((ax, get_hauteur_sol(ax, az), az)).astype(np.float32)
    else:
        bases_arbres = np.empty((0, 3), dtype=np.float32)

    # Préparation des coffres pour le rendu (position + type + rotation sol)
    bases_chests = [{
        "pos":      np.array([c["x"], c["y"], c["z"]], dtype=np.float32),
        "type":     c["type"],
        "ouvert":   c["ouvert"],
        "rotation": c["rotation"],   # matrice 3x3
        "normale":  c["normale"],
    } for c in chests]

    zone = {
        "pts": np.concatenate(pts_l),
        "A": np.concatenate(A), "B": np.concatenate(B),
        "C": np.concatenate(C), "D": np.concatenate(D),
        "cles": cles,
        "arbres": bases_arbres,
        "chests": bases_chests,
    }

    for k in [k for k in _cache_geo_chunks
              if abs(k[0] - cam_cx) > portee + 2 or abs(k[1] - cam_cz) > portee + 2]:
        del _cache_geo_chunks[k]

    _zone_cache["cle"] = cle
    _zone_cache["zone"] = zone
    return zone


def reinitialiser_monde():
    arbres_caches.clear()
    monstres_caches.clear()
    chest_caches.clear()
    _zone_cache["cle"] = None
    _zone_cache["zone"] = None