# engine/rendu_monstres.py -- rendu des monstres, PILOTÉ PAR LE MONSTRES
#   data/monstres.py -> champ "rendu" :  "segments" (défaut) | "rayon" | "shield" | "phasme"
#   AJOUTER UN MODE DE RENDU = une fonction @rendu("nom") (reçoit les monstres visibles d'un même type).
#   Les mêmes fonctions de géométrie servent à l'EXPLOSION de sommets (Vertex Shatter) à la mort.
import math
import numpy as np
from data import config
from data.monstres import MONSTRES
from data.modeles import _octaedre
from engine import geometrie as G, effets
from engine.renderer import projeter_3d_masse
from world.terrain import get_hauteur_sol

BIAIS = G.BIAIS_ENTITES
BLANC = (255, 255, 255)

# ---- géométrie préparée une fois pour toutes -------------------------------
_MODELES = {cle: (*G.aplatir_modele(d["modele"], d.get("echelle", 1.0)), d["couleur"])
            for cle, d in MONSTRES.items() if d.get("modele")}
_FACES = {cle: G.faces_shield(d["nb_faces"], d["rayon_faces"], d["y_bas"], d["y_haut"])
          for cle, d in MONSTRES.items() if d.get("nb_faces")}
_COEUR = G.aplatir_modele(_octaedre(11, -32))             # le coeur vulnérable du Polygone Shield
_Z3 = np.zeros((1, 3), dtype=np.float32)

RENDUS = {}


def rendu(nom):
    def deco(f):
        RENDUS[nom] = f
        return f
    return deco


def couleur_monstre(m):
    """Couleur de base d'un monstre : allié piraté = cyan, corrompu = violet instable, sinon couleur du bestiaire."""
    if m.allie:
        return (60, 240, 255)
    c = m.fx.get("corr")
    if c is not None:
        if c["etat"] == 2:
            return (200, 70, 255) if int(effets.temps * 9 + m.phase) % 2 else (60, 0, 90)
        return (170, 120, 230)
    return m.data["couleur"]


class Contexte:
    """Tout ce dont un mode de rendu a besoin pour la frame courante."""
    __slots__ = ("mons", "pos", "ex", "ey", "rz", "valides", "temps", "items")


def _positions(mons, temps):
    xs = np.fromiter((m.x for m in mons), np.float64, len(mons))
    zs = np.fromiter((m.z for m in mons), np.float64, len(mons))
    freq = np.fromiter((m.data["anim_freq"] for m in mons), np.float64, len(mons))
    amp = np.fromiter((m.data["anim_amp"] for m in mons), np.float64, len(mons))
    decal = np.fromiter((m.data["decal_y"] for m in mons), np.float64, len(mons))
    phase = np.fromiter((m.phase for m in mons), np.float64, len(mons))
    saut = np.sin(temps * freq + phase) * amp
    return np.column_stack((xs, get_hauteur_sol(xs, zs) + decal + saut, zs)).astype(np.float32)


def collecter(mons, temps, items):
    """Ajoute à `items` (painter's algorithm) tous les monstres visibles. `mons` = liste de Monstre."""
    if not mons:
        return
    c = Contexte()
    c.mons, c.temps, c.items = mons, temps, items
    c.pos = _positions(mons, temps)
    c.ex, c.ey, c.rz, c.valides = projeter_3d_masse(c.pos)
    types = np.array([m.type_cle for m in mons])
    for cle in np.unique(types).tolist():
        sel = np.nonzero(c.valides & (types == cle))[0]
        if len(sel):
            RENDUS[MONSTRES[cle].get("rendu", "segments")](cle, sel.tolist(), c)


def _barre(c, i, items, bonus=5):
    m = c.mons[i]
    if m.hp < m.hp_max:
        items.append((float(c.rz[i]) - BIAIS - bonus, 1, G.barre_vie(int(c.ex[i]), int(c.ey[i]), float(c.rz[i]), m), None))


# ---------------------------------------------------------------------------
@rendu("segments")
def _rendu_segments(cle, sel, c):
    P1, P2, _ = _MODELES[cle]
    cols = [G.COULEUR_TOUCHE if c.mons[i].hit > 0 else couleur_monstre(c.mons[i]) for i in sel]
    for i, segs in zip(sel, G.segments_entites(c.pos[sel], P1, P2, None, cols)):
        if segs:
            c.items.append((float(c.rz[i]) - BIAIS, 3, segs, None))
        _barre(c, i, c.items)


# ---------------------------------------------------------------------------
def _rayon_longueur(m):
    D = m.data
    if m.etat == "fonce":
        return D["longueur_charge"]
    if m.etat == "vise":
        k = 1.0 - max(0.0, m.t_etat) / D["duree_vise"]
        return D["longueur_repos"] + (D["longueur_vise"] - D["longueur_repos"]) * k
    return D["longueur_repos"] * (1.0 + 0.25 * math.sin(effets.temps * 10 + m.phase))


def _couleur_rayon(m):
    if m.hit > 0:
        return BLANC
    col = couleur_monstre(m)
    if m.etat == "vise":                                    # clignote en s'armant
        k = 0.55 + 0.45 * math.sin(effets.temps * 30)
        return (int(255 * (1 - k) + col[0] * k), int(255 * (1 - k) + col[1] * k), int(255 * (1 - k) + col[2] * k))
    return col


@rendu("rayon")
def _rendu_rayon(cle, sel, c):
    """Striker : AUCUN volume 3D, un simple trait d'énergie (genre 7 : halo + coeur blanc)."""
    k = len(sel)
    heads = c.pos[sel]
    dirs = np.array([[c.mons[i].dir_x, 0.0, c.mons[i].dir_z] for i in sel], dtype=np.float32)
    L = np.array([_rayon_longueur(c.mons[i]) for i in sel], dtype=np.float32)
    tails = heads - dirs * L[:, None]
    ax, ay, rz, va = projeter_3d_masse(heads)
    bx, by, _, vb = projeter_3d_masse(tails)
    for j in range(k):
        if not (va[j] and vb[j]):
            continue
        m = c.mons[sel[j]]
        c.items.append((float(rz[j]) - BIAIS, 7, ((int(ax[j]), int(ay[j])), (int(bx[j]), int(by[j]))), _couleur_rayon(m)))
        if m.etat == "vise":                                # ligne d'alerte : où il va foncer
            fin = heads[j] + dirs[j] * 700.0
            fx, fy, _, vf = projeter_3d_masse(fin[None, :])
            if vf[0]:
                c.items.append((float(rz[j]) - BIAIS + 1, 1,
                                [((int(ax[j]), int(ay[j])), (int(fx[0]), int(fy[0])), (150, 30, 70))], None))
        _barre(c, sel[j], c.items)


# ---------------------------------------------------------------------------
def segments_shield(m, base, temps):
    """(P1, P2, couleurs) en coordonnées MONDE : faces encore debout + coeur."""
    F1, F2 = _FACES[m.type_cle]
    debout = np.nonzero(np.array(m.faces, dtype=bool))[0]
    P1 = F1[debout].reshape(-1, 3)
    P2 = F2[debout].reshape(-1, 3)
    P1 = G.tourner_y(P1, m.rot)
    P2 = G.tourner_y(P2, m.rot)
    C1, C2 = _COEUR
    a = temps * 2.5 + m.phase
    C1, C2 = G.tourner_y(C1, a), G.tourner_y(C2, a)
    blanc = m.hit > 0
    cf = BLANC if blanc else couleur_monstre(m)
    puls = 0.6 + 0.4 * math.sin(temps * 9)
    cc = BLANC if blanc else (255, int(70 + 60 * puls), int(60 * puls))      # coeur : rouge vif qui bat
    cols = [cf] * len(P1) + [cc] * len(C1)
    return (np.concatenate((P1, C1)) + base, np.concatenate((P2, C2)) + base, cols)


@rendu("shield")
def _rendu_shield(cle, sel, c):
    for i in sel:
        m = c.mons[i]
        P1, P2, cols = segments_shield(m, c.pos[i], c.temps)
        segs = G.segments_entites(_Z3, P1, P2, cols)[0]
        if segs:
            c.items.append((float(c.rz[i]) - BIAIS, 3, segs, None))
        _barre(c, i, c.items)


# ---------------------------------------------------------------------------
def segments_phasme(m, base, temps):
    """Sorti : gerbe de pointes qui pousse du sol. Sous la grille : petit anneau + 3 picots (la distorsion
    elle-même est dessinée par la grille, cf. effets.ondes.sources)."""
    D = m.data
    if m.etat == "traque":
        r = 46.0 + 8.0 * math.sin(temps * 7 + m.phase)
        ang = np.linspace(0, 2 * math.pi, 11, dtype=np.float32) + temps * 1.5
        ring = np.stack((np.sin(ang) * r, np.full(11, -3.0, np.float32), np.cos(ang) * r), axis=1)
        P1, P2 = ring[:-1], ring[1:]
        spk = np.stack((np.sin(ang[:3] * 2.0) * r * 0.5, np.zeros(3, np.float32), np.cos(ang[:3] * 2.0) * r * 0.5), axis=1)
        P1 = np.concatenate((P1, spk))
        P2 = np.concatenate((P2, spk + np.array([0, -16.0, 0], np.float32)))
        base = base + np.array([0, -D["distorsion"]["amp"] * 0.8, 0], np.float32)
        col = (180, 40, 140)
    else:
        M1, M2, _ = _MODELES[m.type_cle]
        col = couleur_monstre(m)
        s = np.array([1.0, max(0.05, m.y_haut), 1.0], dtype=np.float32)
        P1, P2 = G.tourner_y(M1 * s, m.phase + temps * 0.8), G.tourner_y(M2 * s, m.phase + temps * 0.8)
    if m.hit > 0:
        col = BLANC
    return P1 + base, P2 + base, [col] * len(P1)


@rendu("phasme")
def _rendu_phasme(cle, sel, c):
    for i in sel:
        m = c.mons[i]
        P1, P2, cols = segments_phasme(m, c.pos[i], c.temps)
        segs = G.segments_entites(_Z3, P1, P2, cols)[0]
        if segs:
            c.items.append((float(c.rz[i]) - BIAIS, 3, segs, None))
        if m.etat != "traque":
            _barre(c, i, c.items)


# ---------------------------------------------------------------------------
#  Segments MONDE d'un monstre (pour l'explosion de sommets)
# ---------------------------------------------------------------------------
def _base(m, temps):
    D = m.data
    y = float(get_hauteur_sol(m.x, m.z)) + D["decal_y"] + math.sin(temps * D["anim_freq"] + m.phase) * D["anim_amp"]
    return np.array([m.x, y, m.z], dtype=np.float32), float(get_hauteur_sol(m.x, m.z))


def segments_monde(m, temps):
    base, sol = _base(m, temps)
    mode = m.data.get("rendu", "segments")
    if mode == "shield":
        P1, P2, _ = segments_shield(m, base, temps)
    elif mode == "phasme":
        P1, P2, _ = segments_phasme(m, base, temps)
    elif mode == "rayon":
        d = np.array([m.dir_x, 0.0, m.dir_z], dtype=np.float32)
        P1, P2 = base[None, :], (base - d * _rayon_longueur(m))[None, :]
    else:
        M1, M2, _ = _MODELES[m.type_cle]
        P1, P2 = M1 + base, M2 + base
    return P1, P2, sol


def mort_monstre(m):
    """MORT : Vertex Shatter (chaque arête devient un débris avec gravité) + étincelles + onde dans la grille."""
    t = effets.temps
    P1, P2, sol = segments_monde(m, t)
    col = m.data["couleur"]
    effets.eclater(P1, P2, col, sol, force=1.0, morceaux=2 if len(P1) < 24 else 1)
    centre = (P1.mean(axis=0) + P2.mean(axis=0)) * 0.5
    effets.etincelles(centre, (255, 40, 40), n=10)
    effets.onde(m.x, m.z, amp=config.ONDE_MORT_AMP)


def casser_face(m):
    """Une face du Polygone Shield vient d'être détruite : elle éclate en débris."""
    i = m.face_touchee
    if i < 0 or m.type_cle not in _FACES:
        return
    F1, F2 = _FACES[m.type_cle]
    base, sol = _base(m, effets.temps)
    P1, P2 = G.tourner_y(F1[i], m.rot) + base, G.tourner_y(F2[i], m.rot) + base
    effets.eclater(P1, P2, m.data["couleur"], sol, force=0.8, morceaux=2)
    effets.etincelles(P1.mean(axis=0), m.data["couleur"], n=6)
    effets.onde(m.x, m.z, amp=config.ONDE_TIR_AMP * 1.5)
    m.face_touchee = -1
