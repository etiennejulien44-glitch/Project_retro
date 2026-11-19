# engine/geometrie.py -- petits outils géométriques partagés (rendu, effets, boss, monstres)
import math
import numpy as np
from engine.renderer import projeter_3d_masse

BIAIS_ENTITES = 150          # les entités passent devant le terrain de même profondeur
COULEUR_TOUCHE = (255, 255, 255)

_GLOW = {}


def glow_de(c):
    """Couleur sombre du halo (mise en cache)."""
    g = _GLOW.get(c)
    if g is None:
        g = (int(c[0] * 0.35), int(c[1] * 0.35), int(c[2] * 0.35))
        _GLOW[c] = g
    return g


def aplatir_modele(modele, echelle=1.0):
    P1 = np.array([l[0] for l in modele], dtype=np.float32) * echelle
    P2 = np.array([l[1] for l in modele], dtype=np.float32) * echelle
    return P1, P2


def tourner_y(P, a):
    c, s = math.cos(a), math.sin(a)
    out = P.copy()
    out[:, 0] = P[:, 0] * c + P[:, 2] * s
    out[:, 2] = -P[:, 0] * s + P[:, 2] * c
    return out


def matrice_xy(ax, ay):
    """Rotation autour de X puis de Y (pour les solides qui tournent sur eux-mêmes)."""
    cx, sx, cy, sy = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    return ry @ rx


def segments_entites(bases, P1, P2, couleurs_seg=None, couleurs_inst=None):
    """Projette k instances (bases (k,3)) d'un modèle (P1,P2 : (m,3)) en UNE seule passe numpy.
    -> liste (une par instance) de [((x1,y1),(x2,y2),couleur), ...]"""
    bases = np.asarray(bases, dtype=np.float32).reshape(-1, 3)
    k, m = len(bases), P1.shape[0]
    p1 = (bases[:, None, :] + P1[None, :, :]).reshape(-1, 3)
    p2 = (bases[:, None, :] + P2[None, :, :]).reshape(-1, 3)
    ax, ay, _, va = projeter_3d_masse(p1)
    bx, by, _, vb = projeter_3d_masse(p2)
    ok = (va & vb).reshape(k, m).tolist()
    AX, AY = ax.reshape(k, m).tolist(), ay.reshape(k, m).tolist()
    BX, BY = bx.reshape(k, m).tolist(), by.reshape(k, m).tolist()
    resultat = []
    for i in range(k):
        if couleurs_inst is not None:
            ci = couleurs_inst[i]
            resultat.append([((AX[i][j], AY[i][j]), (BX[i][j], BY[i][j]), ci)
                             for j in range(m) if ok[i][j]])
        else:
            resultat.append([((AX[i][j], AY[i][j]), (BX[i][j], BY[i][j]), couleurs_seg[j])
                             for j in range(m) if ok[i][j]])
    return resultat


def barre_vie(ex, ey, rz, m):
    frac = max(0.0, m.hp / m.hp_max)
    w = max(10.0, 12000.0 / rz)
    from data import config
    haut = m.data["hauteur_barre"] * config.FOCALE / rz
    x0, x1 = int(ex - w), int(ex + w)
    y = int(ey - haut)
    xf = int(ex - w + 2 * w * frac)
    fond, plein = (70, 0, 60), (255, 60, 200)
    return [((x0, y), (x1, y), fond), ((x0, y + 2), (x1, y + 2), fond),
            ((x0, y), (xf, y), plein), ((x0, y + 2), (xf, y + 2), plein)]


def faces_shield(n, rayon, y_bas, y_haut):
    """Géométrie LOCALE des n faces d'un Polygone Shield (prisme à n pans, axe Y).
    La face i est centrée sur l'angle i*2π/n (convention (sin a, cos a) = (x, z)).
    -> (P1, P2) de forme (n, 5, 3) : 5 segments par face (4 arêtes + 1 diagonale)."""
    pas = 2 * math.pi / n
    P1 = np.zeros((n, 5, 3), dtype=np.float32)
    P2 = np.zeros((n, 5, 3), dtype=np.float32)
    for i in range(n):
        a0, a1 = i * pas - pas / 2, i * pas + pas / 2
        A0 = (rayon * math.sin(a0), y_bas, rayon * math.cos(a0))
        B0 = (rayon * math.sin(a1), y_bas, rayon * math.cos(a1))
        A1 = (A0[0], y_haut, A0[2])
        B1 = (B0[0], y_haut, B0[2])
        for j, (p, q) in enumerate(((A0, B0), (A1, B1), (A0, A1), (B0, B1), (A0, B1))):
            P1[i, j], P2[i, j] = p, q
    return P1, P2


def diff_angle(a, b):
    """Plus petit écart signé a - b, dans [-π, π]."""
    return (a - b + math.pi) % (2 * math.pi) - math.pi
