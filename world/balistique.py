# world/balistique.py -- avance des projectiles EN BLOC (numpy) : sol, couverts et joueur testés en une passe
import numpy as np
from data import config
from .terrain import get_hauteur_sol, bloque_points


def avancer(liste, dt, joueur, rayon2, degats_fixe=None):
    """liste de [x,y,z,vx,vy,vz,duree(,degats)] -- modifiée en place. Les touches infligent des dégâts au joueur
    (degats_fixe, sinon la colonne 7 du projectile)."""
    if not liste:
        return
    a = np.array(liste, dtype=np.float64)
    a[:, 0:3] += a[:, 3:6] * dt
    a[:, 6] -= dt
    vivants = a[:, 6] > 0
    if vivants.any():
        vivants &= ~(a[:, 1] > get_hauteur_sol(a[:, 0], a[:, 2]))
    if vivants.any():
        vivants &= ~bloque_points(a[:, 0], a[:, 1], a[:, 2])
    d2 = (a[:, 0] - config.cam_x) ** 2 + (a[:, 1] - config.cam_y) ** 2 + (a[:, 2] - config.cam_z) ** 2
    touche = vivants & (d2 < rayon2)
    if touche.any():
        for i in np.nonzero(touche)[0].tolist():
            joueur.prendre_degats(degats_fixe if degats_fixe is not None else a[i, 7])
        vivants &= ~touche
    liste[:] = a[vivants].tolist()
