# renderer.py
import numpy as np
from data import config


# =============================================================
#  Projection monde -> caméra -> écran
# =============================================================

def vers_camera(points_3d):
    """Monde -> repere camera. Retourne (rx, ry, rz) : rz = profondeur."""
    points = np.asarray(points_3d, dtype=np.float32)
    dx = points[:, 0] - config.cam_x
    dy = points[:, 1] - config.cam_y
    dz = points[:, 2] - config.cam_z

    rx = dx * config.COS_YAW - dz * config.SIN_YAW
    rz = dx * config.SIN_YAW + dz * config.COS_YAW
    ry = dy * config.COS_PITCH - rz * config.SIN_PITCH
    rz_final = dy * config.SIN_PITCH + rz * config.COS_PITCH
    return rx, ry, rz_final


def ecran_depuis_camera(rx, ry, rz):
    """Repere camera -> pixels (les points trop proches sont neutralises)."""
    rz_safe = np.where(rz > config.NEAR, rz, 1.0)
    ex = (config.LARGEUR * 0.5 + (rx * config.FOCALE) / rz_safe).astype(np.int32)
    ey = (config.HAUTEUR * 0.5 + (ry * config.FOCALE) / rz_safe).astype(np.int32)
    return ex, ey


def projeter_3d_masse(points_3d):
    points = np.asarray(points_3d, dtype=np.float32)
    if points.size == 0 or points.ndim != 2 or points.shape[1] != 3:
        return (np.empty(0, dtype=np.int32), np.empty(0, dtype=np.int32),
                np.empty(0, dtype=np.float32), np.empty(0, dtype=bool))

    rx, ry, rz = vers_camera(points)
    valides = (rz > config.NEAR) & (rz <= config.DIST_AFFICHAGE_MAX)
    ex, ey = ecran_depuis_camera(rx, ry, rz)
    return ex, ey, rz, valides


def clipper_near(poly):
    """Decoupe un polygone (liste de (x, y, z) en repere camera) contre le plan z = NEAR.
    Retourne (points, flags) ; flags[k] = True si l'arete k -> k+1 existe vraiment
    (False = arete creee par la coupe, qu'on ne veut pas tracer)."""
    near = config.NEAR
    pts, flags = [], []
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        a_in = a[2] >= near
        b_in = b[2] >= near
        if a_in:
            pts.append(a)
            flags.append(True)
        if a_in != b_in:
            t = (near - a[2]) / (b[2] - a[2])
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, near))
            flags.append(b_in)  # entrant : inter -> b est une vraie arete ; sortant : arete de coupe
    return pts, flags


# =============================================================
#  Helpers coffres : local -> monde -> écran
# =============================================================

def transformer_vertices_monde(rotation, position, vertices_locaux):
    """Applique la rotation sol + la translation aux vertices locaux d'un objet.
    rotation : matrice 3x3 ligne-major (telle que produite par terrain.py)
    position : np.array (3,)
    vertices_locaux : np.array (N, 3)
    Retourne : np.array (N, 3) en coordonnées monde.
    """
    v = np.asarray(vertices_locaux, dtype=np.float32)
    if v.ndim != 2 or v.shape[1] != 3 or len(v) == 0:
        return np.empty((0, 3), dtype=np.float32)
    R = np.asarray(rotation, dtype=np.float32)
    pos = np.asarray(position, dtype=np.float32)
    return (v @ R.T + pos).astype(np.float32)


def projeter_coffre(chest, vertices_locaux):
    """Projette les vertices locaux d'un coffre vers l'écran.
    Retourne (ex, ey, rz, valides) — même format que projeter_3d_masse.
    """
    monde = transformer_vertices_monde(chest["rotation"], chest["pos"], vertices_locaux)
    return projeter_3d_masse(monde)


def normale_monde(rotation, normale_locale=(0.0, 1.0, 0.0)):
    """Normale locale transformée en normale monde (pour l'éclairage)."""
    n = np.asarray(normale_locale, dtype=np.float32)
    return (np.asarray(rotation, dtype=np.float32) @ n).astype(np.float32)


def coords_monde_boite(chest, demi_dimensions, offset_local=(0.0, 0.0, 0.0)):
    """Retourne les 8 coins d'une boîte orientée (pour painter's algorithm / AABB).
    Ordre : (---, +--, -+-, ++-, --+, +-+, -++, +++)
    `offset_local` sert si l'origine du modèle n'est pas à la base (ex : (0, h/2, 0)).
    """
    hx, hy, hz = demi_dimensions
    ox, oy, oz = offset_local
    signs = np.array([
        [-hx + ox, -hy + oy, -hz + oz], [ hx + ox, -hy + oy, -hz + oz],
        [-hx + ox,  hy + oy, -hz + oz], [ hx + ox,  hy + oy, -hz + oz],
        [-hx + ox, -hy + oy,  hz + oz], [ hx + ox, -hy + oy,  hz + oz],
        [-hx + ox,  hy + oy,  hz + oz], [ hx + ox,  hy + oy,  hz + oz],
    ], dtype=np.float32)
    return transformer_vertices_monde(chest["rotation"], chest["pos"], signs)


def profondeur_coffre(chest):
    """rz caméra-space du centre du coffre (pour tri painter's algorithm)."""
    pos = np.asarray(chest["pos"], dtype=np.float32)[None, :]
    _, _, rz = vers_camera(pos)
    return float(rz[0])


def position_ecran_centre(chest):
    """(ex, ey, rz, valide) du centre du coffre — utile pour billboard / debug."""
    ex, ey, rz, valides = projeter_3d_masse(
        np.asarray(chest["pos"], dtype=np.float32)[None, :]
    )
    if len(ex) == 0:
        return 0, 0, 0.0, False
    return int(ex[0]), int(ey[0]), float(rz[0]), bool(valides[0])