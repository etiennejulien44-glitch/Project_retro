# renderer.py
import numpy as np
import config


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
