# game_test.py  --  FPS rétro synthwave
import math
import random
import sys
from itertools import repeat
from operator import itemgetter

import numpy as np
import pygame

# Fichiers situés dans le dossier 'data'
from data import config, boosts, modeles
from data.boosts import StatsBoostes, Butin, Rarete
from data.coffres import COFFRES
from data.modeles import (
    MODELE_ARBRE, MODELE_ARAIGNEE, MODELE_DRONE,
    MODELE_MUNITIONS, MODELE_SOINS,
    MODELE_CHEST, PRISMATIC_CHEST, SPIDER_BOSS
)

# Fichiers situés dans le dossier 'world'
from world import entity, ciel, terrain
from world.entity import Joueur
from world.ciel import Ciel
from world import boss as boss_module
from data import equipements
from data.decors import DECORS
from world.terrain import (
    get_hauteur_sol, get_zone, reinitialiser_monde,
    monstres_caches, chest_caches
)

# Fichiers situés dans le dossier 'engine'
from engine.renderer import (
    vers_camera, ecran_depuis_camera, projeter_3d_masse,
    clipper_near, transformer_vertices_monde
)

# Fichiers situés dans le dossier 'ui'
from ui.hud import HUD, MUZZLE, CYAN, BLANC
from ui.terminal import TerminalInventory

# ---------------------------------------------------------------------------
# Échelles / rendu
# ---------------------------------------------------------------------------
ECHELLE_PICKUP    = 3.0
ECHELLE_CHEST     = 1.0
ECHELLE_BUTIN     = 200.0
ECHELLE_BOSS      = 4.0

BOSS_YAW_OFFSET   = 0.0
DEBUG_STATS       = True   # F3 pour toggle

DISTANCE_INTERACTION_COFFRE = 160

def _aplatir_modele(modele, echelle=1.0):
    P1 = np.array([l[0] for l in modele], dtype=np.float32) * echelle
    P2 = np.array([l[1] for l in modele], dtype=np.float32) * echelle
    return P1, P2

PYR_P1,      PYR_P2      = _aplatir_modele(boosts.MODELE_PYRAMIDE, ECHELLE_BUTIN)
BOSS_P1,     BOSS_P2     = _aplatir_modele(SPIDER_BOSS,      ECHELLE_BOSS)

# Rendu des monstres : construit AUTOMATIQUEMENT depuis data/bestiaire.py
from data.bestiaire import BESTIAIRE
# Pickups (munitions, soin...) et coffres : AUTOMATIQUE depuis data/boosts.py et data/coffres.py
PICKUPS_RENDU = {i: (*_aplatir_modele(boosts.BOOSTS[k]["pickup"]["modele"], boosts.BOOSTS[k]["pickup"]["echelle"]),
                     boosts.BOOSTS[k]["pickup"]["couleur"])
                 for i, k in enumerate(boosts.PICKUP_IDS)}
def _couleurs_decor(spec):
    seuil = -spec["hauteur"] / spec["echelle"] * 0.35
    return [spec["couleur_2"] if max(a[1], b[1]) < seuil else spec["couleur"] for a, b in spec["modele"]]

def _faces_boite_decor(spec):
    """Génère automatiquement les 6 faces d'un décor opaque à partir de ses points."""
    if not spec.get("opaque"):
        return None
    pts = [p for seg in spec["modele"] for p in seg]
    echelle = spec["echelle"]
    xs, ys, zs = [p[0] * echelle for p in pts], [p[1] * echelle for p in pts], [p[2] * echelle for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    z0, z1 = min(zs), max(zs)
    return [
        (np.array([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], dtype=np.float32), spec["couleur_2"]),
        (np.array([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], dtype=np.float32), spec["couleur"]),
        (np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], dtype=np.float32), spec["couleur"]),
        (np.array([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], dtype=np.float32), spec["couleur"]),
        (np.array([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], dtype=np.float32), spec["couleur"]),
        (np.array([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], dtype=np.float32), spec["couleur"]),
    ]

# Décors : AUTOMATIQUE depuis data/decors.py
DECORS_RENDU = {
    did: (*_aplatir_modele(d["modele"], d["echelle"]), _couleurs_decor(d), _faces_boite_decor(d))
    for did, d in DECORS.items()
}
COFFRES_RENDU = {cle: (*_aplatir_modele(d["modele"], d["echelle"]), d) for cle, d in COFFRES.items()}
MONSTRES_RENDU = {cle: (*_aplatir_modele(d["modele"], d.get("echelle", 1.0)), d["couleur"])
                  for cle, d in BESTIAIRE.items()}

COULEUR_TOUCHE = (255, 255, 255)

def _build_fog_lut():
    r0, g0, b0 = config.TERRAIN_PROCHE
    r1, g1, b1 = config.TERRAIN_LOIN
    n = config.FOG_STEPS - 1
    return [(int(r0 + (r1 - r0) * i / n),
             int(g0 + (g1 - g0) * i / n),
             int(b0 + (b1 - b0) * i / n)) for i in range(config.FOG_STEPS)]

FOG_LUT = _build_fog_lut()
FOG_MAX_INV = config.FOG_STEPS / config.DIST_AFFICHAGE_MAX
DIST_BORD_EPAIS = 400
DIST_GLOW_TERRAIN = 600
DIST_GLOW_ENTITES = 900
BIAIS_ENTITES = 150

_GLOW = {}

def glow_de(c):
    g = _GLOW.get(c)
    if g is None:
        g = (int(c[0] * 0.35), int(c[1] * 0.35), int(c[2] * 0.35))
        _GLOW[c] = g
    return g

def _couleur_fog(profondeur):
    i = int(profondeur * FOG_MAX_INV)
    return FOG_LUT[i if i < config.FOG_STEPS - 1 else config.FOG_STEPS - 1]

def _tourner_y(P, a):
    c, s = math.cos(a), math.sin(a)
    out = P.copy()
    out[:, 0] = P[:, 0] * c + P[:, 2] * s
    out[:, 2] = -P[:, 0] * s + P[:, 2] * c
    return out

# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------
def collecter_terrain(zone, items):
    rx, ry, rz = vers_camera(zone["pts"])
    ex, ey = ecran_depuis_camera(rx, ry, rz)
    A, B, C, D = zone["A"], zone["B"], zone["C"], zone["D"]

    proche = rz > config.NEAR
    loin_ok = rz <= config.DIST_AFFICHAGE_MAX
    nA, nB, nC, nD = proche[A], proche[B], proche[C], proche[D]
    tous_proches = nA & nB & nC & nD
    tous_loin_ok = loin_ok[A] & loin_ok[B] & loin_ok[C] & loin_ok[D]

    # Récupération de la LUT de brouillard spécifique au biome de la zone
    fog_lut_biome = zone["fog_lut"]

    q = np.nonzero(tous_proches & tous_loin_ok)[0]
    if q.size:
        idx = np.stack((A[q], B[q], C[q], D[q]), axis=1)
        X, Y = ex[idx], ey[idx]
        visible = ((X.max(1) >= 0) & (X.min(1) <= config.LARGEUR) &
                   (Y.max(1) >= 0) & (Y.min(1) <= config.HAUTEUR))
        idx, X, Y = idx[visible], X[visible], Y[visible]
        if len(idx):
            prof = rz[idx].mean(axis=1)
            fog = np.minimum((prof * FOG_MAX_INV).astype(np.int32), config.FOG_STEPS - 1)
            polys = np.stack((X, Y), axis=2).tolist()
            couleurs = [fog_lut_biome[i] for i in fog.tolist()]
            items.extend(zip(prof.tolist(), repeat(0), polys, couleurs))

    partiels = np.nonzero((nA | nB | nC | nD) & ~tous_proches & tous_loin_ok)[0]
    W2, H2, F = config.LARGEUR * 0.5, config.HAUTEUR * 0.5, config.FOCALE
    for qi in partiels.tolist():
        poly = [(float(rx[i]), float(ry[i]), float(rz[i]))
                for i in (A[qi], B[qi], C[qi], D[qi])]
        pts3, flags = clipper_near(poly)
        if len(pts3) < 3:
            continue
        pts2 = [(max(-20000, min(20000, int(W2 + x * F / z))),
                 max(-20000, min(20000, int(H2 + y * F / z)))) for x, y, z in pts3]
        prof = sum(p[2] for p in pts3) / len(pts3)
        
        # Calcul de la couleur de brouillard locale pour les polygones partiels
        i_fog = int(prof * FOG_MAX_INV)
        i_fog = i_fog if i_fog < config.FOG_STEPS - 1 else config.FOG_STEPS - 1
        col_fog = fog_lut_biome[i_fog]
        
        items.append((prof, 2, (pts2, flags), col_fog))

def _segments_entites(bases, P1, P2, couleurs_seg=None, couleurs_inst=None):
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

def _barre_vie(ex, ey, rz, m):
    frac = max(0.0, m.hp / m.hp_max)
    w = max(10.0, 12000.0 / rz)
    haut = m.data["hauteur_barre"] * config.FOCALE / rz
    x0, x1 = int(ex - w), int(ex + w)
    y = int(ey - haut)
    xf = int(ex - w + 2 * w * frac)
    fond, plein = (70, 0, 60), (255, 60, 200)
    return [((x0, y), (x1, y), fond), ((x0, y + 2), (x1, y + 2), fond),
            ((x0, y), (xf, y), plein), ((x0, y + 2), (xf, y + 2), plein)]

# ---------------------------------------------------------------------------
# BOSS
# ---------------------------------------------------------------------------
def collecter_boss(items, temps):
    b = boss_module.boss
    if b is None:
        return

    y = get_hauteur_sol(b.x, b.z) + config.BOSS_OFFSET_MODELE + b.saut_hauteur_courante
    pos = np.array([[b.x, y, b.z]], dtype=np.float32)

    if b.etat == "charge":
        yaw = math.atan2(b.charge_dir[0], b.charge_dir[1])
    else:
        dx = config.cam_x - b.x
        dz = config.cam_z - b.z
        yaw = math.atan2(dx, dz) if (dx != 0 or dz != 0) else 0.0
    yaw += BOSS_YAW_OFFSET

    B1 = _tourner_y(BOSS_P1, yaw)
    B2 = _tourner_y(BOSS_P2, yaw)

    if b.en_spawn:
        puls = 0.5 + 0.5 * math.sin(temps * 15)
        couleur = (int(255 * puls), int(80 * puls), int(80 * puls))
    else:
        puls = 0.6 + 0.4 * math.sin(temps * 8)
        frac = b.hp / b.hp_max if b.hp_max > 0 else 1.0
        intensite = 0.5 + 0.5 * (1 - frac)
        couleur = (int(255 * intensite), int(60 * puls), int(60 * puls))

    segs_l = _segments_entites(pos, B1, B2, [couleur] * B1.shape[0])
    if segs_l and segs_l[0]:
        _, _, rz, v = projeter_3d_masse(pos)
        prof = float(rz[0]) - BIAIS_ENTITES
        items.append((prof, 3, segs_l[0], None))

def collecter_projectiles_boss(items):
    if not boss_module.projectiles_boss:
        return
    for p in boss_module.projectiles_boss:
        p0 = np.array([[p[0], p[1], p[2]]], dtype=np.float32)
        n = math.sqrt(p[3] ** 2 + p[4] ** 2 + p[5] ** 2) + 1e-6
        p1 = np.array([[p[0] - p[3] / n * 55,
                        p[1] - p[4] / n * 55,
                        p[2] - p[5] / n * 55]], dtype=np.float32)
        ax, ay, rz, va = projeter_3d_masse(p0)
        bx, by, _, vb = projeter_3d_masse(p1)
        if va[0] and vb[0]:
            items.append((float(rz[0]) - 20, 5,
                          ((int(ax[0]), int(ay[0])), (int(bx[0]), int(by[0]))),
                          None))

def dessiner_barre_vie_boss(surf, temps):
    b = boss_module.boss
    if b is None:
        return

    if b.en_spawn:
        frac = 1.0 - max(0.0, b.t_spawn) / config.BOSS_SPAWN_ANIM_DUREE
        frac = min(1.0, max(0.0, frac))
    else:
        frac = b.hp / b.hp_max if b.hp_max > 0 else 0.0

    largeur = int(config.LARGEUR * 0.65)
    hauteur = 46
    x0 = (config.LARGEUR - largeur) // 2
    y0 = 40

    puls = 0.6 + 0.4 * math.sin(temps * 6)
    puls2 = 0.5 + 0.5 * math.sin(temps * 12 + 1.3)

    fond = pygame.Surface((largeur, hauteur), pygame.SRCALPHA)
    fond.fill((0, 0, 0, 200))
    surf.blit(fond, (x0, y0))

    bord = (int(255 * puls), int(40 * puls2), int(40 * puls2))
    pygame.draw.rect(surf, bord, (x0, y0, largeur, hauteur), 4)

    rempli = int((largeur - 6) * frac)
    if rempli > 0:
        if b.en_spawn:
            cr = int(255 * (0.3 + 0.7 * frac))
            cg = int(80 * frac)
            cb = int(80 * frac)
        else:
            frac_hp = b.hp / b.hp_max if b.hp_max > 0 else 0
            intensite = 0.5 + 0.5 * (1 - frac_hp)
            cr = int(255 * intensite)
            cg = int(50 * puls)
            cb = int(50 * puls)
        pygame.draw.rect(surf, (cr, cg, cb),
                         (x0 + 3, y0 + 3, rempli, hauteur - 6))

    for i in range(1, 10):
        sx = x0 + 3 + (largeur - 6) * i // 10
        pygame.draw.line(surf, (0, 0, 0), (sx, y0 + 5), (sx, y0 + hauteur - 5), 2)

    if int(temps * 4) % 2 == 0:
        font = pygame.font.SysFont(None, 42)
        txt = font.render(f"BOSS NIVEAU {b.niveau + 1}", True, (255, 200, 200))
        surf.blit(txt, (x0 + largeur // 2 - txt.get_width() // 2, y0 + hauteur + 8))

    if b.en_spawn and int(temps * 8) % 2 == 0:
        font = pygame.font.SysFont(None, 96)
        txt = font.render("⚠ DANGER ⚠", True, (255, 40, 40))
        surf.blit(txt, (config.LARGEUR // 2 - txt.get_width() // 2,
                        config.HAUTEUR // 2 - 120))

# ---------------------------------------------------------------------------
# Entités
# ---------------------------------------------------------------------------
def collecter_entites(zone, items, temps):
    for did, bases in zone["decors"].items():
        _, _, rz, v = projeter_3d_masse(bases)
        vis = np.nonzero(v)[0]
        if not len(vis):
            continue
        
        P1, P2, cols, faces = DECORS_RENDU[did]
        if faces is not None:
            # Nouveau rendu opaque
            for b in bases[vis]:
                for f_pts, f_col in faces:
                    ex_f, ey_f, rz_f, vf = projeter_3d_masse(b[None, :] + f_pts)
                    if vf.all():
                        pts2 = list(zip(ex_f.astype(int).tolist(), ey_f.astype(int).tolist()))
                        items.append((float(rz_f.mean()) - BIAIS_ENTITES, 2, (pts2, [True, True, True, True]), f_col))
        else:
            # Rendu fil de fer classique d'origine
            for segs, p in zip(_segments_entites(bases[vis], P1, P2, cols), rz[vis].tolist()):
                if segs:
                    items.append((p - BIAIS_ENTITES, 1, segs, None))

    mons = [m for cle in zone["cles"] for m in monstres_caches[cle]]
    if mons:
        xs = np.array([m.x for m in mons])
        zs = np.array([m.z for m in mons])
        cles_m = np.array([m.type_cle for m in mons])
        phase = np.array([m.phase for m in mons])
        freq = np.array([m.data["anim_freq"] for m in mons])
        amp = np.array([m.data["anim_amp"] for m in mons])
        decal = np.array([m.data["decal_y"] for m in mons])
        saut = np.sin(temps * freq + phase) * amp
        pos = np.column_stack((xs, get_hauteur_sol(xs, zs) + decal + saut, zs)).astype(np.float32)
        ex, ey, rz, v = projeter_3d_masse(pos)

        for cle_m, (P1, P2, col) in MONSTRES_RENDU.items():
            sel = np.nonzero(v & (cles_m == cle_m))[0]
            if not len(sel):
                continue
            cols = [COULEUR_TOUCHE if mons[i].hit > 0 else col for i in sel.tolist()]
            for i, segs in zip(sel.tolist(), _segments_entites(pos[sel], P1, P2, None, cols)):
                p = float(rz[i])
                if segs:
                    items.append((p - BIAIS_ENTITES, 3, segs, None))
                m = mons[i]
                if m.hp < m.hp_max:
                    items.append((p - BIAIS_ENTITES - 5, 1,
                                  _barre_vie(int(ex[i]), int(ey[i]), p, m), None))

    if entity.pickups:
        arr = np.array(entity.pickups, dtype=np.float64)
        bob = np.sin(temps * 3 + arr[:, 0] * 0.01) * 6 + 22      # flotte au-dessus du sol
        pos = np.column_stack((arr[:, 0],
                               get_hauteur_sol(arr[:, 0], arr[:, 1]) - bob,
                               arr[:, 1])).astype(np.float32)
        _, _, rz, v = projeter_3d_masse(pos)
        ang = temps * 2.0
        for id_t, (P1, P2, col) in PICKUPS_RENDU.items():
            sel = np.nonzero(v & (arr[:, 2] == id_t))[0]
            if not len(sel):
                continue
            segs_l = _segments_entites(pos[sel], _tourner_y(P1, ang), _tourner_y(P2, ang),
                                       [col] * P1.shape[0])
            for i, segs in zip(sel.tolist(), segs_l):
                if segs:
                    items.append((float(rz[i]) - BIAIS_ENTITES, 3, segs, None))

    if entity.projectiles:
        arr = np.array(entity.projectiles, dtype=np.float32)
        p0 = arr[:, :3]
        vel = arr[:, 3:6]
        n = np.linalg.norm(vel, axis=1, keepdims=True) + 1e-6
        p1 = p0 - vel / n * 45
        ax, ay, rz, va = projeter_3d_masse(p0)
        bx, by, _, vb = projeter_3d_masse(p1)
        for i in np.nonzero(va & vb)[0].tolist():
            items.append((float(rz[i]) - 20, 4,
                          ((int(ax[i]), int(ay[i])), (int(bx[i]), int(by[i]))),
                          None))

# ---------------------------------------------------------------------------
# Coffres
# ---------------------------------------------------------------------------
def collecter_coffres(zone, items, temps):
    for cle in zone["cles"]:
        for chest in chest_caches[cle]:
            pos = np.array([chest["x"], chest["y"], chest["z"]], dtype=np.float32)
            R = chest["rotation"]
            P1, P2, cdef = COFFRES_RENDU[chest["type"]]
            if chest["ouvert"]:
                base = cdef["couleur_ouvert"]
            elif "couleur_pulse" in cdef:
                puls = 0.55 + 0.45 * math.sin(temps * 5 + chest["x"] * 0.13 + chest["z"] * 0.07)
                c0, c1 = cdef["couleur"], cdef["couleur_pulse"]
                base = tuple(int(c0[i] + (c1[i] - c0[i]) * puls) for i in range(3))
            else:
                base = cdef["couleur"]

            w1 = transformer_vertices_monde(R, pos, P1)
            w2 = transformer_vertices_monde(R, pos, P2)
            ax, ay, rz, va = projeter_3d_masse(w1)
            bx, by, _, vb = projeter_3d_masse(w2)
            ok = va & vb
            if not ok.any():
                continue
            prof = float(rz[ok].mean()) - BIAIS_ENTITES
            ax_i, ay_i = ax.tolist(), ay.tolist()
            bx_i, by_i = bx.tolist(), by.tolist()
            segs = [((ax_i[j], ay_i[j]), (bx_i[j], by_i[j]), base)
                    for j in np.nonzero(ok)[0].tolist()]
            if segs:
                items.append((prof, 3, segs, None))

# ---------------------------------------------------------------------------
# Éclairs (zap_chaine des jambières)
# ---------------------------------------------------------------------------
def collecter_zaps(items):
    for z in entity.zaps:
        pts = np.array([[z[0], z[1], z[2]], [z[3], z[4], z[5]]], dtype=np.float32)
        ax, ay, rz, ok = projeter_3d_masse(pts)
        if ok[0] and ok[1]:
            items.append((float(min(rz[0], rz[1])) - 20, 4,
                          ((int(ax[0]), int(ay[0])), (int(ax[1]), int(ay[1]))), None))

# ---------------------------------------------------------------------------
# Butins
# ---------------------------------------------------------------------------
def collecter_butins(items, temps):
    if not boosts.butins_au_sol:
        return
    butins = boosts.butins_au_sol
    k = len(butins)
    xs = np.array([b.x for b in butins], dtype=np.float32)
    zs = np.array([b.z for b in butins], dtype=np.float32)
    ph = np.array([b.phase for b in butins], dtype=np.float32)
    spawn = np.array([b.spawn_time for b in butins], dtype=np.float64)

    age = np.clip(temps - spawn, 0.0, 0.35)
    t_anim = age / 0.35
    scale = 0.3 + 0.7 * t_anim
    y_offset = (1.0 - t_anim) * 120.0 + 40.0                 # jaillit du coffre puis flotte à 40

    bob = np.sin(temps * 3 + ph) * 6
    ys = (get_hauteur_sol(xs, zs) - bob - y_offset).astype(np.float32)   # Y vers le bas : on soustrait

    ang = temps * 2.0
    c, s = math.cos(ang), math.sin(ang)

    for i in range(k):
        sc = float(scale[i])
        P1r = np.column_stack((
            PYR_P1[:, 0] * c * sc + PYR_P1[:, 2] * s * sc,
            PYR_P1[:, 1] * sc,
            -PYR_P1[:, 0] * s * sc + PYR_P1[:, 2] * c * sc,
        )).astype(np.float32)
        P2r = np.column_stack((
            PYR_P2[:, 0] * c * sc + PYR_P2[:, 2] * s * sc,
            PYR_P2[:, 1] * sc,
            -PYR_P2[:, 0] * s * sc + PYR_P2[:, 2] * c * sc,
        )).astype(np.float32)

        base_pos = np.array([xs[i], ys[i], zs[i]], dtype=np.float32)
        p1w = (base_pos[None, :] + P1r).astype(np.float32)
        p2w = (base_pos[None, :] + P2r).astype(np.float32)
        ax, ay, rz, va = projeter_3d_masse(p1w)
        bx, by, _, vb = projeter_3d_masse(p2w)
        ok = va & vb
        if not ok.any():
            continue
        base = butins[i].couleur
        ax_i, ay_i = ax.tolist(), ay.tolist()
        bx_i, by_i = bx.tolist(), by.tolist()
        segs = [((ax_i[j], ay_i[j]), (bx_i[j], by_i[j]), base)
                for j in np.nonzero(ok)[0].tolist()]
        if segs:
            prof = float(rz[ok].mean()) - BIAIS_ENTITES
            items.append((prof, 3, segs, None))

# ---------------------------------------------------------------------------
# Interaction coffres
# ---------------------------------------------------------------------------
def coffre_proche(zone, joueur_x, joueur_z, distance=DISTANCE_INTERACTION_COFFRE):
    """(coffre, distance) du coffre fermé le plus proche, ou (None, inf)."""
    meilleur, meilleure_dist = None, distance
    for cle in zone["cles"]:
        for chest in chest_caches[cle]:
            if chest["ouvert"]:
                continue
            d = math.hypot(chest["x"] - joueur_x, chest["z"] - joueur_z)
            if d < meilleure_dist:
                meilleure_dist = d
                meilleur = chest
    return meilleur, (meilleure_dist if meilleur else float("inf"))


def ouvrir_coffre_proche(zone, joueur_x, joueur_z, distance=DISTANCE_INTERACTION_COFFRE):
    meilleur, _ = coffre_proche(zone, joueur_x, joueur_z, distance)
    if meilleur is None:
        return None
    meilleur["ouvert"] = True
    butins = []
    for i in range(COFFRES[meilleur["type"]].get("nb_butins", 1)):
        dx, dz = (0.0, 0.0) if i == 0 else (random.uniform(-70, 70), random.uniform(-70, 70))
        butin = boosts.tirer_butin(meilleur["type"], meilleur["x"] + dx, meilleur["z"] + dz)
        boosts.spawner_butin(butin)
        butins.append(butin)
    return butins

# ---------------------------------------------------------------------------
# Overlay debug
# ---------------------------------------------------------------------------
def dessiner_debug_stats(surf, joueur, stats, jeu=None):
    font = pygame.font.SysFont(None, 22)
    arme = equipements.possedees.get(equipements.equipees["arme"], {})
    lignes = [
        f"PV : {joueur.pv}/{config.JOUEUR_PV_MAX}",
        f"Vitesse : x{stats.vitesse_mult:.2f}  (+{int(stats.vitesse_bonus*100)}%)",
        f"Saut : x{stats.saut_mult:.2f}  (+{int(stats.saut_bonus*100)}%)",
        f"Degats : x{stats.degats_mult:.2f}  (+{int(stats.degats_bonus*100)}%)",
        f"Auto-regen : {'ON' if stats.auto_regen else 'off'}",
        f"Munitions : {joueur.chargeur} / {joueur.reserve}",
        f"Kills : {joueur.kills}",
        f"Arme : {arme.get('nom', '-')} [{arme.get('rarete', '-')}]  dgt {config.DEGATS_TIR:.2f}",
        f"Armure : -{int(config.REDUCTION_DEGATS*100)}% dgts  +{int(config.BONUS_HP)} PV  vit +{int(config.BONUS_VITESSE*100)}%",
        f"Poids : {equipements.poids_porte()}/{equipements.poids_max()} MB",
    ]
    if config.DASH_CELLULES > 0 and jeu is not None:
        etat = "PRET [A]" if jeu.dash_cd <= 0 else f"{jeu.dash_cd:.0f}s"
        lignes.append(f"Dash ({config.DASH_CELLULES:.1f} cell) : {etat}")
    pad = 8
    largeur = 380
    hauteur = len(lignes) * 22 + pad * 2
    x0 = 12
    y0 = config.HAUTEUR - hauteur - 120
    bg = pygame.Surface((largeur, hauteur), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 160))
    surf.blit(bg, (x0, y0))
    for i, ligne in enumerate(lignes):
        txt = font.render(ligne, True, (200, 255, 200))
        surf.blit(txt, (x0 + pad, y0 + pad + i * 22))

# ---------------------------------------------------------------------------
# Dessin des items
# ---------------------------------------------------------------------------
def dessiner_items(surf, items, zone=None):
    items.sort(key=itemgetter(0), reverse=True)
    poly, ligne = pygame.draw.polygon, pygame.draw.line
    noir = config.COULEUR_REMPLISSAGE

    # Récupération de la couleur de grille du biome si disponible
    couleur_grille_biome = zone.get("couleur_grille", (255, 0, 128)) if zone else (255, 0, 128)

    for prof, genre, data, col in items:
        if genre == 0:
            poly(surf, noir, data)
            if prof < DIST_GLOW_TERRAIN:
                # Utilisation de la couleur du biome pour le glow de la grille
                poly(surf, glow_de(couleur_grille_biome), data, 4)
            # Utilisation de la couleur du biome pour les arêtes de la grille
            poly(surf, couleur_grille_biome, data, 2 if prof < DIST_BORD_EPAIS else 1)
        elif genre == 1:
            for p1, p2, c in data:
                ligne(surf, c, p1, p2, 2)
        elif genre == 3:
            if prof < DIST_GLOW_ENTITES:
                for p1, p2, c in data:
                    ligne(surf, glow_de(c), p1, p2, 6)
            for p1, p2, c in data:
                ligne(surf, c, p1, p2, 2)
        elif genre == 4:
            ligne(surf, (120, 20, 90), data[0], data[1], 10)
            ligne(surf, (255, 70, 170), data[0], data[1], 5)
            ligne(surf, BLANC, data[0], data[1], 2)
        elif genre == 5:
            ligne(surf, (140, 0, 0), data[0], data[1], 14)
            ligne(surf, (255, 40, 40), data[0], data[1], 7)
            ligne(surf, (255, 220, 100), data[0], data[1], 2)
        else:
            pts, flags = data
            poly(surf, noir, pts)
            n = len(pts)
            for k in range(n):
                if flags[k]:
                    ligne(surf, col, pts[k], pts[(k + 1) % n], 2)

# ---------------------------------------------------------------------------
# Jeu
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Jeu
# ---------------------------------------------------------------------------
class Jeu:
    def __init__(self, surface):
        self.surf = surface
        self.joueur = Joueur()
        self.ciel = Ciel()
        self.hud = HUD()
        self.stats = StatsBoostes()
        self.tir_t = 0.0
        self.tir_fin = None
        self.zone = None
        self.popup_text = ""
        self.popup_timer = 0.0
        self.popup_color = (255, 255, 255)
        self.font_popup = pygame.font.SysFont(None, 56)
        self.font_invite = pygame.font.SysFont(None, 36)
        self.debug_stats = DEBUG_STATS
        self.terminal = TerminalInventory()
        self.terminal.jeu = self
        self.en_inventaire = False
        self.dash_cd = 0.0
        self.sprint = False
        self._equip_version = -1
        self._arme_affichee = None
        self.reinitialiser()

    def reinitialiser(self):
        equipements.reinitialiser()
        reinitialiser_monde()
        entity.reinitialiser_entites()
        boosts.vider_butins()
        boss_module.reinitialiser_boss()
        self.stats = StatsBoostes()
        self.temps_run = 0.0
        self.couche_max = 0          # couche la plus profonde atteinte (progression / boss)
        config.cam_x, config.cam_z = config.DEPART_X, config.DEPART_Z
        
        # Récupération dynamique du biome pour placer la caméra à la bonne hauteur sur le relief
        biome_actuel = terrain.get_biome_actuel(
            int(math.floor(config.cam_x / (config.TAILLE_CHUNKS * config.ECHELLE_GRILLE))), 
            int(math.floor(config.cam_z / (config.TAILLE_CHUNKS * config.ECHELLE_GRILLE)))
        )
        config.cam_y = get_hauteur_sol(config.cam_x, config.cam_z) - 30
        
        config.yaw = config.pitch = config.vitesse_y = 0.0
        config.mettre_a_jour_rayons()
        self.joueur.reinitialiser()
        self.dash_cd = 0.0
        self.sprint = False
        self._arme_affichee = equipements.equipees["arme"]
        self.synchroniser_equipement(annonce=False)
        self.tir_t = 0.0
        self.tir_fin = None
        self.popup_text = ""
        self.popup_timer = 0.0
        self._maj_zone()

    def _maj_zone(self):
        t = config.TAILLE_CHUNKS * config.ECHELLE_GRILLE
        self.zone = get_zone(int(math.floor(config.cam_x / t)),
                             int(math.floor(config.cam_z / t)), config.PORTEE_CHUNKS)

    def regarder(self, rel_x, rel_y):
        if self.joueur.mort:
            return
        config.yaw += rel_x * 0.2
        config.pitch = max(-85, min(85, config.pitch + rel_y * 0.2))

    def tirer(self):
        j = self.joueur
        if boss_module.run_gagnee:
            return
        if not j.tenter_tir():
            return
        self.tir_t = 0.10
        mult = self.stats.degats_mult * equipements.multiplicateur_degats(self.sprint)
        base_degats = config.DEGATS_TIR
        config.DEGATS_TIR = base_degats * mult
        try:
            self.tir_fin, _, _ = entity.tirer_laser(self.zone["cles"], j)
        finally:
            config.DEGATS_TIR = base_degats

    def synchroniser_equipement(self, annonce=True):
        """Appelé dès que l'équipement change (terminal, ramassage, reset) : PV max, chargeur, annonce d'arme."""
        j = self.joueur
        self.stats.recalculer_pv_max(j)
        if j.chargeur > config.CHARGEUR_TAILLE:          # arme au chargeur plus petit : le surplus retourne en réserve
            surplus = j.chargeur - config.CHARGEUR_TAILLE
            j.chargeur = config.CHARGEUR_TAILLE
            j.reserve = min(config.MUNITIONS_RESERVE_MAX, j.reserve + surplus)
        self._equip_version = equipements.version
        arme_id = equipements.equipees["arme"]
        if annonce and arme_id != self._arme_affichee and arme_id in equipements.possedees:
            it = equipements.possedees[arme_id]
            self.popup_text = f"ARME : {it['nom']} [{it['rarete'].upper()}]"
            self.popup_color = equipements.RARETES[it["rarete"]]["couleur"]
            self.popup_timer = 2.0
        self._arme_affichee = arme_id

    def cible_interaction(self):
        """Ce que la touche F ferait ici : le plus proche parmi coffre fermé / butin / pickup.
        -> (genre, objet, libellé, couleur) ou None."""
        x, z, r = config.cam_x, config.cam_z, config.RAYON_INTERACTION
        meilleur, d_min = None, r
        chest, d = coffre_proche(self.zone, x, z, r)
        if chest is not None:
            meilleur, d_min = ("coffre", chest, "Ouvrir le coffre", (255, 255, 255)), d
        for b in boosts.butins_au_sol:
            d = math.hypot(b.x - x, b.z - z)
            if d < d_min:
                meilleur, d_min = ("butin", b, f"Ramasser {b.nom}", b.couleur), d
        for p in entity.pickups:
            d = math.hypot(p[0] - x, p[1] - z)
            if d < d_min:
                d_def = boosts.BOOSTS[boosts.PICKUP_IDS[int(p[2])]]
                meilleur, d_min = ("pickup", p, f"Ramasser {d_def['nom']}", d_def["pickup"]["couleur"]), d
        return meilleur

    def interagir(self):
        """Touche F : ouvre le coffre / ramasse l'objet le plus proche. Plus d'aimant ni de ramassage forcé."""
        if self.joueur.mort or boss_module.run_gagnee:
            return
        cible = self.cible_interaction()
        if cible is None:
            return
        genre, obj, _, _ = cible
        if genre == "coffre":
            self.interagir_coffre()
            return
        self.stats.messages_ramassage.clear()
        if genre == "butin":
            obj.notifie = False                       # on veut le message "trop lourd" à chaque essai
            if boosts.appliquer(obj.def_id, self.stats, self.joueur, obj):
                boosts.butins_au_sol[:] = [b for b in boosts.butins_au_sol if b is not obj]
        else:
            if boosts.appliquer(boosts.PICKUP_IDS[int(obj[2])], self.stats, self.joueur):
                entity.pickups[:] = [p for p in entity.pickups if p is not obj]
        if not self.stats.messages_ramassage:             # refus sans message (munitions / PV déjà pleins...)
            self.stats.messages_ramassage.append(("DEJA AU MAXIMUM", (255, 120, 120)))

    def interagir_coffre(self):
        butins = ouvrir_coffre_proche(self.zone, config.cam_x, config.cam_z)
        if butins:
            self.popup_text = "COFFRE : " + " + ".join(b.nom for b in butins)
            self.popup_color = butins[0].couleur
            self.popup_timer = 2.5
        return butins

    def dash(self):
        """Torse (dash_atq) : bond en avant qui blesse tout sur le trajet. Touche A, recharge 30 s."""
        j = self.joueur
        if j.mort or boss_module.run_gagnee or config.DASH_CELLULES <= 0:
            return
        if self.dash_cd > 0:
            self.popup_text = f"DASH : {self.dash_cd:.0f}s"
            self.popup_color = (255, 120, 120)
            self.popup_timer = 1.0
            return
        dist = config.DASH_CELLULES * config.DASH_UNITES_PAR_CELLULE
        rad = math.radians(config.yaw)
        dx, dz = math.sin(rad), math.cos(rad)
        x0, z0 = config.cam_x, config.cam_z
        etapes = max(1, int(dist // 25))
        x, z = x0, z0
        for _ in range(etapes):                           # par petits pas : les décors solides bloquent le dash
            x, z = terrain.repousser(x + dx * dist / etapes, z + dz * dist / etapes, config.cam_y + 30)
        config.cam_x, config.cam_z = x, z
        t = max(0.0, min(1.0, (config.DASH_CELLULES - 1.0) / 2.0))     # 1 cellule -> 150%, 3 cellules -> 300%
        mult_dash = config.DASH_DEGATS_MIN + (config.DASH_DEGATS_MAX - config.DASH_DEGATS_MIN) * t
        degats = (config.DEGATS_TIR * self.stats.degats_mult
                  * equipements.multiplicateur_degats(False) * mult_dash)
        nb = entity.degats_zone_segment(self.zone["cles"], x0, z0, x, z, config.DASH_RAYON, degats, j)
        self.dash_cd = config.DASH_COOLDOWN
        self.popup_text = f"DASH ! {nb} cible(s)" if nb else "DASH !"
        self.popup_color = (0, 255, 255)
        self.popup_timer = 1.2

    def recharger(self):
        if self.joueur.mort or boss_module.run_gagnee:
            self.reinitialiser()
        else:
            self.joueur.lancer_recharge()

    def mettre_a_jour(self, dt, temps, avant, cote, saut, sprint=False):
        config.mettre_a_jour_rayons()
        j = self.joueur
        if equipements.version != self._equip_version:       # équipement modifié depuis la dernière frame
            self.synchroniser_equipement()
        j.mettre_a_jour(dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        entity.mettre_a_jour_zaps(dt)
        self.stats.update(dt, j)
        self.tir_t = max(0.0, self.tir_t - dt)
        self.popup_timer = max(0.0, self.popup_timer - dt)
        if j.mort or boss_module.run_gagnee:
            return
        self.temps_run += dt

        self.sprint = bool(sprint) and (avant != 0 or cote != 0)
        vitesse = 250 * self.stats.vitesse_mult * (1.0 + config.BONUS_VITESSE) * dt
        if self.sprint:
            vitesse *= config.SPRINT_MULT
        rad = math.radians(config.yaw)
        config.cam_x += (avant * math.sin(rad) + cote * math.cos(rad)) * vitesse
        config.cam_z += (avant * math.cos(rad) - cote * math.sin(rad)) * vitesse

        config.cam_x, config.cam_z = terrain.repousser(config.cam_x, config.cam_z, config.cam_y + 30)

        # Calcul de la hauteur du sol selon le biome actuel de la zone
        biome_courant = terrain.get_biome_actuel(
            int(math.floor(config.cam_x / (config.TAILLE_CHUNKS * config.ECHELLE_GRILLE))),
            int(math.floor(config.cam_z / (config.TAILLE_CHUNKS * config.ECHELLE_GRILLE)))
        )
        sol = get_hauteur_sol(config.cam_x, config.cam_z) - 30

        if saut and abs(config.cam_y - sol) < 2:
            config.vitesse_y = -300 * self.stats.saut_mult
        config.vitesse_y += config.gravite * dt
        config.cam_y += config.vitesse_y * dt
        if config.cam_y > sol:
            config.cam_y = sol
            config.vitesse_y = 0

        self._maj_zone()

        # Progression : nouvelle couche atteinte -> annonce
        couche = terrain.get_couche_monde(config.cam_x, config.cam_z)
        if couche > self.couche_max:
            self.couche_max = couche
            biome = terrain.BIOMES[terrain.COUCHES[couche]]
            self.popup_text = f"COUCHE {couche + 1}/{terrain.NB_COUCHES} - {biome['nom']}"
            self.popup_color = biome["couleur_grille"]
            self.popup_timer = 3.5

        # Dernière couche atteinte -> boss final (fin de run quand il tombe)
        if couche >= terrain.NB_COUCHES - 1 and boss_module.lancer_boss_final(config.cam_x, config.cam_z):
            self.popup_text = "!!! BOSS FINAL !!!"
            self.popup_color = (255, 40, 40)
            self.popup_timer = 4.0
        boosts.ramasser_butins(j, self.stats, config.cam_x, config.cam_z, dt)

        entity.mettre_a_jour_monstres(dt, self.zone["cles"], j, temps)
        entity.mettre_a_jour_projectiles(dt, j)
        entity.mettre_a_jour_pickups(j, dt, self.stats)
        boss_module.mettre_a_jour_boss(dt, j, temps)
        boss_module.mettre_a_jour_projectiles_boss(dt, j)

    def rendre(self, temps):
        surf = self.surf
        self.ciel.dessiner(surf, temps)

        items = []
        collecter_terrain(self.zone, items)
        collecter_coffres(self.zone, items, temps)
        collecter_boss(items, temps)
        collecter_projectiles_boss(items)
        collecter_butins(items, temps)
        collecter_zaps(items)
        collecter_entites(self.zone, items, temps)
        dessiner_items(surf, items, self.zone)

        j = self.joueur
        if not j.mort:
            if self.tir_t > 0:
                fin = self.tir_fin or (config.LARGEUR // 2, config.HAUTEUR // 2)
                pygame.draw.line(surf, (30, 140, 160), MUZZLE, fin, 7)
                pygame.draw.line(surf, CYAN, MUZZLE, fin, 3)
                pygame.draw.line(surf, BLANC, MUZZLE, fin, 1)
                pygame.draw.circle(surf, BLANC, MUZZLE, 10)
                pygame.draw.circle(surf, CYAN, MUZZLE, 20, 2)
            self.hud.dessiner_arme(surf, j, self.tir_t / 0.10)

        self.hud.dessiner(surf, j, temps, self.stats)
        dessiner_barre_vie_boss(surf, temps)

        if self.stats.messages_ramassage:
            texte, couleur = self.stats.messages_ramassage[-1]
            self.stats.messages_ramassage.clear()
            self.popup_text = texte
            self.popup_color = couleur
            self.popup_timer = 2.5

        if not j.mort and not boss_module.run_gagnee and not self.en_inventaire:
            cible = self.cible_interaction()
            if cible is not None:
                invite = self.font_invite.render(f"[F]  {cible[2]}", True, cible[3])
                surf.blit(invite, (config.LARGEUR // 2 - invite.get_width() // 2, config.HAUTEUR // 2 + 110))

        if self.popup_timer > 0 and self.popup_text:
            alpha = min(1.0, self.popup_timer / 0.4)
            txt = self.font_popup.render(self.popup_text, True, self.popup_color)
            pad = 16
            bg = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, int(140 * alpha)))
            cx = config.LARGEUR // 2
            cy = config.HAUTEUR - 260
            surf.blit(bg, (cx - bg.get_width() // 2, cy - bg.get_height() // 2))
            txt.set_alpha(int(255 * alpha))
            surf.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))

        if self.debug_stats:
            dessiner_debug_stats(surf, j, self.stats, self)

        if self.en_inventaire:
            overlay = pygame.Surface((config.LARGEUR, config.HAUTEUR), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160)) # Voile noir semi-transparent (effet pause)
            surf.blit(overlay, (0, 0))
            
            font_term = pygame.font.SysFont(None, 24)
            self.terminal.dessiner(surf, font_term)

        if j.mort:
            self.hud.dessiner_game_over(surf, j, temps)
        elif boss_module.run_gagnee:
            self.hud.dessiner_victoire(surf, j, temps, self.temps_run)

# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    fenetre = pygame.display.set_mode((config.LARGEUR, config.HAUTEUR), pygame.RESIZABLE)
    pygame.display.set_caption("FPS Rétro Synthwave")
    horloge = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    jeu = Jeu(fenetre)
    timer_caption = 0.0
    en_cours = True

    while en_cours:
        dt = min(horloge.tick(60) / 1000.0, 0.05)
        temps = pygame.time.get_ticks() / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                en_cours = False
            
            # --- 1. OUVERTURE DU TERMINAL VIA TAB (Uniquement si fermé) ---
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_TAB and not jeu.en_inventaire:
                jeu.en_inventaire = True
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                continue

            # --- 2. SI LE TERMINAL EST OUVERT ---
            if jeu.en_inventaire:
                # On envoie TOUS les événements clavier au terminal (plus de fermeture intempestive par touche bindée)
                action = jeu.terminal.handle_event(event)
                if action == "CLOSE_TERMINAL":
                    jeu.en_inventaire = False
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
            
            # --- 3. SI LE JEU EST ACTIF (FPS) ---
            else:
                if event.type == pygame.MOUSEMOTION:
                    jeu.regarder(*event.rel)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    jeu.tirer()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                    jeu.interagir()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_a:
                    jeu.dash()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    jeu.recharger()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                    jeu.debug_stats = not jeu.debug_stats
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and (jeu.joueur.mort or boss_module.run_gagnee):
                    jeu.recharger()

        # Vraie pause totale du jeu si l'inventaire est ouvert
        if not jeu.en_inventaire:
            touches = pygame.key.get_pressed()
            jeu.mettre_a_jour(dt, temps,
                              touches[pygame.K_z] - touches[pygame.K_s],
                              touches[pygame.K_d] - touches[pygame.K_q],
                              touches[pygame.K_SPACE],
                              touches[pygame.K_LSHIFT])

        jeu.rendre(temps)
        pygame.display.flip()

        timer_caption += dt
        if timer_caption >= 0.5:
            timer_caption = 0.0
            pygame.display.set_caption(f"FPS Rétro Synthwave - {horloge.get_fps():.0f} FPS")

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()