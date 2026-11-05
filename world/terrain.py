# world/terrain.py
import numpy as np
import random
import math
from data import config
from data.biomes import (BIOMES, COUCHES, NB_COUCHES, COUCHE_LARGEUR_REGIONS,
                         JITTER_FRONTIERE, CHANCE_VARIANTE, RAYON_COUCHE_0)
from .monstre import Monstre

arbres_caches = {}
monstres_caches = {}
chest_caches = {}

TAILLE_REGION = 6          # en chunks
LARGEUR_FONDU = 0.15       # demi-largeur de la zone de fondu (fraction de région)
_CLES_BIOMES = list(BIOMES.keys())
_IDX_BIOME = {k: i for i, k in enumerate(_CLES_BIOMES)}

# --- Seed du monde : change à chaque nouvelle partie -------------------------
_graine_monde = random.randrange(1 << 30)
_cache_regions = {}        # (rx, rz) -> (couche, cle_biome)


def _taille_region_monde():
    return TAILLE_REGION * config.TAILLE_CHUNKS * config.ECHELLE_GRILLE


def _rng_region(rx, rz, sel):
    return random.Random(_graine_monde ^ (int(rx) * 73856093) ^ (int(rz) * 19349663) ^ (sel * 83492791))


def _infos_region(rx, rz):
    """(couche, cle_biome) d'une région. Déterministe pour une seed donnée."""
    cle = (int(rx), int(rz))
    r = _cache_regions.get(cle)
    if r is not None:
        return r

    R = _taille_region_monde()
    # distance (en régions) entre le centre de la région et le point de départ
    d = math.hypot((cle[0] + 0.5) - config.DEPART_X / R, (cle[1] + 0.5) - config.DEPART_Z / R)

    if d <= RAYON_COUCHE_0:                      # zone de départ : toujours le Noyau
        r = (0, COUCHES[0])
    else:
        rng = _rng_region(cle[0], cle[1], 1)
        d_eff = d + rng.uniform(-JITTER_FRONTIERE, JITTER_FRONTIERE)
        couche = max(0, min(NB_COUCHES - 1, int(d_eff / COUCHE_LARGEUR_REGIONS)))
        biome_couche = couche
        if rng.random() < CHANCE_VARIANTE:       # hasard : biome d'une couche voisine
            voisines = [c for c in (couche - 1, couche + 1) if 0 <= c < NB_COUCHES]
            biome_couche = rng.choice(voisines)
        r = (couche, COUCHES[biome_couche])
    _cache_regions[cle] = r
    return r


def _biome_region(rx, rz):
    return BIOMES[_infos_region(rx, rz)[1]]


def get_biome_actuel(cx, cz):
    """Biome d'un chunk (couleurs, monstres, coffres...)."""
    return _biome_region(cx // TAILLE_REGION, cz // TAILLE_REGION)


def get_couche(cx, cz):
    """Numéro de couche (0..NB_COUCHES-1) d'un chunk : sert à la progression / aux boss."""
    return _infos_region(cx // TAILLE_REGION, cz // TAILLE_REGION)[0]


def get_couche_monde(monde_x, monde_z):
    t = config.TAILLE_CHUNKS * config.ECHELLE_GRILLE
    return get_couche(int(math.floor(monde_x / t)), int(math.floor(monde_z / t)))


# =============================================================
#  Helpers orientation / terrain unifié et styles de relief
# =============================================================

def _hauteur_brute(gx, gz, biome):
    """Hauteur du sol d'UN biome, sans fondu (gx/gz en unités de grille)."""
    e1 = biome["echelle_bruit_1"]
    e2 = biome["echelle_bruit_2"]
    base = np.sin(gx * e1) * np.cos(gz * e1) * 15.0
    detail = np.sin(gx * e2 * 2.0) * np.cos(gz * e2 * 2.0) * 5.0
    vague = np.sin(gx * 0.01) * np.sin(gz * 0.01) * 25.0
    total = base + detail + vague
    if biome.get("type_relief") == "abrupte":
        total = np.round(total / 4.0) * 4.0
    return -total * (biome["eval_hauteur"] * 0.5)


def _poids_fondu(f):
    """f dans [0,1[ entre deux centres de région -> poids du voisin (0 au centre, 1 de l'autre côté).
    La frontière est à f=0.5 ; le fondu se fait sur +-LARGEUR_FONDU autour, avec un smoothstep (C1)."""
    t = np.clip((f - (0.5 - LARGEUR_FONDU)) / (2.0 * LARGEUR_FONDU), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def get_hauteur_sol(monde_x, monde_z, biome=None):
    """Hauteur du sol, CONTINUE à travers les frontières de biomes.
    Interpolation bilinéaire (poids lissés) entre les biomes des 4 régions les plus proches.
    Marche avec des scalaires et des tableaux NumPy. `biome` est ignoré (compat)."""
    gx = np.asarray(monde_x, dtype=np.float64) / config.ECHELLE_GRILLE
    gz = np.asarray(monde_z, dtype=np.float64) / config.ECHELLE_GRILLE

    taille_region = TAILLE_REGION * config.TAILLE_CHUNKS * config.ECHELLE_GRILLE
    u = np.asarray(monde_x, dtype=np.float64) / taille_region - 0.5
    v = np.asarray(monde_z, dtype=np.float64) / taille_region - 0.5
    i0 = np.floor(u).astype(np.int64)
    j0 = np.floor(v).astype(np.int64)
    wx = _poids_fondu(u - i0)
    wz = _poids_fondu(v - j0)

    h = 0.0
    corners = ((0, 0, (1 - wx) * (1 - wz)), (1, 0, wx * (1 - wz)),
               (0, 1, (1 - wx) * wz),       (1, 1, wx * wz))
    if np.ndim(gx) == 0:
        for di, dj, w in corners:
            if w > 0.0:
                h = h + w * _hauteur_brute(gx, gz, _biome_region(i0 + di, j0 + dj))
    else:
        for di, dj, w in corners:
            ii = (i0 + di).ravel()
            jj = (j0 + dj).ravel()
            uniq, inv = np.unique(np.stack((ii, jj), axis=1), axis=0, return_inverse=True)
            ids_u = np.array([_IDX_BIOME[_infos_region(a_, b_)[1]] for a_, b_ in uniq])
            ids = ids_u[inv.reshape(-1)].reshape(gx.shape)
            actif = w > 0.0
            for k in np.unique(ids[actif]):
                m = actif & (ids == k)
                h = h + np.where(m, w * _hauteur_brute(gx, gz, BIOMES[_CLES_BIOMES[k]]), 0.0)
    h = h if isinstance(h, np.ndarray) else np.float64(h)
    return h if np.ndim(h) else float(h)


def _get_normale_sol(monde_x, monde_z, biome=None, epsilon=0.4):
    """Normale unitaire du sol à (x,z) par différences finies."""
    hL = get_hauteur_sol(monde_x - epsilon, monde_z, biome)
    hR = get_hauteur_sol(monde_x + epsilon, monde_z, biome)
    hD = get_hauteur_sol(monde_x, monde_z - epsilon, biome)
    hU = get_hauteur_sol(monde_x, monde_z + epsilon, biome)
    dx = (hR - hL) / (2.0 * epsilon)
    dz = (hU - hD) / (2.0 * epsilon)
    n = np.array([-dx, 1.0, -dz], dtype=np.float64)
    return n / (np.linalg.norm(n) + 1e-9)


def _matrice_alignement(up, normale, yaw):
    """
    Matrice 3x3 telle que :
      - l'axe local Y soit aligné sur `normale` (pente du terrain),
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

def _trouver_position_coffre(rand_gen, cx, cz, arbres, autres_coffres, marge, biome):
    taille = config.TAILLE_CHUNKS
    if taille <= 2 * marge:
        gmin, gmax = 0, taille
    else:
        gmin, gmax = marge, taille - marge

    paliers = [
        (0.65, 2.0, 3.0, 24),
        (0.50, 1.5, 2.0, 16),
        (0.30, 1.0, 1.5, 10),
        (0.00, 0.0, 0.0, 6),
    ]
    for min_dot, d_arbre, d_coffre, essais in paliers:
        for _ in range(essais):
            gx = rand_gen.randint(gmin, gmax)
            gz = rand_gen.randint(gmin, gmax)
            mx = (cx * taille + gx) * config.ECHELLE_GRILLE
            mz = (cz * taille + gz) * config.ECHELLE_GRILLE

            n = _get_normale_sol(mx, mz, biome)
            if n[1] < min_dot:
                continue

            ok = True
            if d_arbre > 0:
                for ax, _, az in arbres:
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
#  Génération du contenu d'un chunk (Arbres, Coffres, Monstres)
# =============================================================

def get_elements_chunk(cx, cz):
    cle = (cx, cz)
    if cle in arbres_caches and cle in monstres_caches and cle in chest_caches:
        return arbres_caches[cle], monstres_caches[cle], chest_caches[cle]

    biome = get_biome_actuel(cx, cz)

    base_seed = (cx * 73856093) ^ (cz * 19349663)
    rng_arbre   = random.Random(base_seed ^ 0xA1B2C3)
    rng_coffre  = random.Random(base_seed ^ 0xC0FFEE)
    rng_monstre = random.Random(base_seed ^ 0xDEADBE)

    taille = config.TAILLE_CHUNKS
    marge = max(1, min(2, taille // 4))

    # ---------- Arbres (hauteur fixe par chunk) ----------
    arbres_chunk = []
    nb_arbres_max = biome["densite_arbres_max"]
    if nb_arbres_max > 0:
        for _ in range(nb_arbres_max):
            for _ in range(10):
                ax = (cx * taille + rng_arbre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE
                az = (cz * taille + rng_arbre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE
                if not any(math.hypot(ax - x, az - z) < 3.0 * config.ECHELLE_GRILLE for x, _, z in arbres_chunk):
                    ay = float(get_hauteur_sol(ax, az, biome))
                    arbres_chunk.append((ax, ay, az))
                    break
    arbres_caches[cle] = arbres_chunk

    # ---------- Coffres ----------
    chest_chunk = []
    positions_chests = []
    nb_coffres = rng_coffre.randint(1, 2)

    for _ in range(nb_coffres):
        pos = _trouver_position_coffre(rng_coffre, cx, cz, arbres_chunk, positions_chests, marge, biome)
        if pos is None:
            gx = rng_coffre.randint(0, taille)
            gz = rng_coffre.randint(0, taille)
            mx = (cx * taille + gx) * config.ECHELLE_GRILLE
            mz = (cz * taille + gz) * config.ECHELLE_GRILLE
            pos = (mx, mz)
        mx, mz = pos
        positions_chests.append((mx, mz))

        is_prismatic = rng_coffre.random() < biome["chances_coffre_prismatique"]
        type_coffre = "PRISMATIC_CHEST" if is_prismatic else "MODELE_CHEST"

        normale = _get_normale_sol(mx, mz, biome)
        y = float(get_hauteur_sol(mx, mz, biome))
        yaw = rng_coffre.uniform(0.0, 2.0 * math.pi)
        rotation = _matrice_alignement(np.array([0.0, 1.0, 0.0]), normale, yaw)

        chest_chunk.append({
            "x": mx, "y": y, "z": mz,
            "type": type_coffre,
            "ouvert": False, "item_spawned": None,
            "normale": normale, "rotation": rotation, "yaw": yaw,
        })
    chest_caches[cle] = chest_chunk

    # ---------- Monstres ----------
    monstres_chunk = []
    liste_monstres_biome = biome["monstres_spawn"]
    
    if liste_monstres_biome:
        for _ in range(2):
            for _ in range(12):
                mx = (cx * taille + rng_monstre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE
                mz = (cz * taille + rng_monstre.randint(marge, taille - marge)) * config.ECHELLE_GRILLE

                if math.hypot(mx - config.DEPART_X, mz - config.DEPART_Z) < config.ZONE_SECURITE_DEPART:
                    continue
                if any(math.hypot(mx - x, mz - z) < 2.0 * config.ECHELLE_GRILLE for x, _, z in arbres_chunk):
                    continue
                if any(math.hypot(mx - c["x"], mz - c["z"]) < 2.0 * config.ECHELLE_GRILLE for c in chest_chunk):
                    continue

                type_cle = rng_monstre.choice(liste_monstres_biome)
                monstres_chunk.append(Monstre(mx, mz, type_cle, rng_monstre))
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
        biome = get_biome_actuel(cx, cz)

        taille = config.TAILLE_CHUNKS * config.ECHELLE_GRILLE
        pas = np.arange(0, config.TAILLE_CHUNKS + 1, config.PAS_GRILLE) * config.ECHELLE_GRILLE
        xs = pas + cx * taille
        zs = pas + cz * taille
        gx, gz = np.meshgrid(xs, zs)
        gx, gz = gx.ravel(), gz.ravel()
        
        gy = get_hauteur_sol(gx, gz, biome)
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
        bases_arbres = np.array([(p[0], p[1], p[2]) for p in arbres], dtype=np.float32)
    else:
        bases_arbres = np.empty((0, 3), dtype=np.float32)

    bases_chests = [{
        "pos":      np.array([c["x"], c["y"], c["z"]], dtype=np.float32),
        "type":     c["type"],
        "ouvert":   c["ouvert"],
        "rotation": c["rotation"],
        "normale":  c["normale"],
    } for c in chests]

    biome_courant = get_biome_actuel(cam_cx, cam_cz)

    def _build_fog_lut_biome(biome):
        r0, g0, b0 = config.TERRAIN_PROCHE
        r1, g1, b1 = biome.get("couleur_brouillard", config.TERRAIN_LOIN)
        n = config.FOG_STEPS - 1
        return [(int(r0 + (r1 - r0) * i / n),
                 int(g0 + (g1 - g0) * i / n),
                 int(b0 + (b1 - b0) * i / n)) for i in range(config.FOG_STEPS)]

    zone = {
        "pts": np.concatenate(pts_l),
        "A": np.concatenate(A), "B": np.concatenate(B),
        "C": np.concatenate(C), "D": np.concatenate(D),
        "cles": cles,
        "arbres": bases_arbres,
        "chests": bases_chests,
        "couleur_grille": biome_courant["couleur_grille"],
        "couleur_brouillard": biome_courant["couleur_brouillard"],
        "couleur_ciel": biome_courant["couleur_ciel"],
        "couleur_arbres": biome_courant["couleur_arbres"],
        "fog_lut": _build_fog_lut_biome(biome_courant),
    }

    for k in [k for k in _cache_geo_chunks
              if abs(k[0] - cam_cx) > portee + 2 or abs(k[1] - cam_cz) > portee + 2]:
        del _cache_geo_chunks[k]

    _zone_cache["cle"] = cle
    _zone_cache["zone"] = zone
    return zone


def reinitialiser_monde(graine=None):
    """Nouveau monde : nouvelle seed (aléatoire si None) => nouvelle disposition des biomes."""
    global _graine_monde
    _graine_monde = random.randrange(1 << 30) if graine is None else int(graine)
    _cache_regions.clear()
    _cache_geo_chunks.clear()
    arbres_caches.clear()
    monstres_caches.clear()
    chest_caches.clear()
    _zone_cache["cle"] = None
    _zone_cache["zone"] = None