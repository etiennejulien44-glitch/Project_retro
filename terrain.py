# terrain.py
import numpy as np
import random
import math
import config
from monstre import Monstre

arbres_caches = {}
monstres_caches = {}

def get_hauteur_sol(monde_x, monde_z):
    gx = monde_x / config.ECHELLE_GRILLE
    gz = monde_z / config.ECHELLE_GRILLE
    base = np.sin(gx * 0.05) * np.cos(gz * 0.05) * 2.0
    detail = np.sin(gx * 0.15) * np.sin(gz * 0.15) * 0.4
    return -(base + detail) * config.EVAL_HAUTEUR

def get_elements_chunk(cx, cz):
    cle = (cx, cz)
    if cle not in arbres_caches:
        rand_gen = random.Random((cx * 73856093) ^ (cz * 19349663))
        
        arbres_chunk = []
        for _ in range(2):
            ax = (cx * config.TAILLE_CHUNKS + rand_gen.randint(2, config.TAILLE_CHUNKS - 2)) * config.ECHELLE_GRILLE
            az = (cz * config.TAILLE_CHUNKS + rand_gen.randint(2, config.TAILLE_CHUNKS - 2)) * config.ECHELLE_GRILLE
            arbres_chunk.append((ax, az))
        arbres_caches[cle] = arbres_chunk
        
        monstres_chunk = []
        for _ in range(2):
            mx = (cx * config.TAILLE_CHUNKS + rand_gen.randint(3, config.TAILLE_CHUNKS - 3)) * config.ECHELLE_GRILLE
            mz = (cz * config.TAILLE_CHUNKS + rand_gen.randint(3, config.TAILLE_CHUNKS - 3)) * config.ECHELLE_GRILLE
            tipo = rand_gen.randint(0, 1)
            monstre = Monstre(mx, mz, tipo, rand_gen)
            # pas de monstre sur la zone de départ du joueur
            if math.hypot(mx - config.DEPART_X, mz - config.DEPART_Z) >= config.ZONE_SECURITE_DEPART:
                monstres_chunk.append(monstre)
        monstres_caches[cle] = monstres_chunk

    return arbres_caches[cle], monstres_caches[cle]


# ---------------------------------------------------------------------------
# Geometrie du terrain : calculee UNE FOIS par chunk, puis fusionnee en une
# seule "zone" (un seul tableau de points) => une seule projection par frame.
# ---------------------------------------------------------------------------
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
    """Retourne la zone autour de la camera (reconstruite seulement quand on change de chunk)."""
    cle = (cam_cx, cam_cz, portee)
    if _zone_cache["cle"] == cle:
        return _zone_cache["zone"]

    pts_l, A, B, C, D, cles, arbres = [], [], [], [], [], [], []
    decalage = 0
    for cx in range(cam_cx - portee, cam_cx + portee + 1):
        for cz in range(cam_cz - portee, cam_cz + portee + 1):
            pts, a, b, c, d = _geo_chunk(cx, cz)
            pts_l.append(pts)
            A.append(a + decalage); B.append(b + decalage)
            C.append(c + decalage); D.append(d + decalage)
            decalage += len(pts)

            arbres_chunk, _ = get_elements_chunk(cx, cz)   # genere aussi les monstres
            arbres.extend(arbres_chunk)
            cles.append((cx, cz))

    if arbres:
        ax = np.array([p[0] for p in arbres], dtype=np.float64)
        az = np.array([p[1] for p in arbres], dtype=np.float64)
        bases_arbres = np.column_stack((ax, get_hauteur_sol(ax, az), az)).astype(np.float32)
    else:
        bases_arbres = np.empty((0, 3), dtype=np.float32)

    zone = {
        "pts": np.concatenate(pts_l),
        "A": np.concatenate(A), "B": np.concatenate(B),
        "C": np.concatenate(C), "D": np.concatenate(D),
        "cles": cles,
        "arbres": bases_arbres,
    }

    # menage : on oublie la geometrie des chunks trop lointains
    for k in [k for k in _cache_geo_chunks
              if abs(k[0] - cam_cx) > portee + 2 or abs(k[1] - cam_cz) > portee + 2]:
        del _cache_geo_chunks[k]

    _zone_cache["cle"] = cle
    _zone_cache["zone"] = zone
    return zone


def reinitialiser_monde():
    """Efface monstres/arbres (régénérés à l'identique) -> utilisé pour rejouer."""
    arbres_caches.clear()
    monstres_caches.clear()
    _zone_cache["cle"] = None
    _zone_cache["zone"] = None
