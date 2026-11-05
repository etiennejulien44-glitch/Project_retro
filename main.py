# game_test.py  --  FPS rétro synthwave
import math
import sys
from itertools import repeat
from operator import itemgetter

import numpy as np
import pygame

# Fichiers situés dans le dossier 'data'
from data import config, boosts, modeles
from data.boosts import StatsBoostes, Butin, TypeBoost, Rarete
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
ECHELLE_ARBRE     = 4.0
ECHELLE_ARAIGNEE  = 1.0
ECHELLE_DRONE     = 1.0
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

ARBRE_P1,    ARBRE_P2    = _aplatir_modele(MODELE_ARBRE,    ECHELLE_ARBRE)
ARAIGNEE_P1, ARAIGNEE_P2 = _aplatir_modele(MODELE_ARAIGNEE, ECHELLE_ARAIGNEE)
DRONE_P1,    DRONE_P2    = _aplatir_modele(MODELE_DRONE,    ECHELLE_DRONE)
MUN_P1,      MUN_P2      = _aplatir_modele(MODELE_MUNITIONS, ECHELLE_PICKUP)
SOIN_P1,     SOIN_P2     = _aplatir_modele(MODELE_SOINS,    ECHELLE_PICKUP)
CHEST_P1,    CHEST_P2    = _aplatir_modele(MODELE_CHEST,      ECHELLE_CHEST)
PRISMA_P1,   PRISMA_P2   = _aplatir_modele(PRISMATIC_CHEST,   ECHELLE_CHEST)
PYR_P1,      PYR_P2      = _aplatir_modele(boosts.MODELE_PYRAMIDE, ECHELLE_BUTIN)
BOSS_P1,     BOSS_P2     = _aplatir_modele(SPIDER_BOSS,      ECHELLE_BOSS)

COULEUR_TRONC = (120, 70, 255)
COULEUR_FEUILLES = (40, 240, 255)
ARBRE_COULEURS = [COULEUR_TRONC if l[0][1] == 0 else COULEUR_FEUILLES for l in MODELE_ARBRE]
COULEUR_ARAIGNEE = (255, 130, 30)
COULEUR_DRONE = (255, 235, 70)
COULEUR_MUNITIONS = (60, 240, 255)
COULEUR_SOIN = (120, 255, 150)
COULEUR_TOUCHE = (255, 255, 255)
COULEUR_CHEST = (255, 210, 90)
COULEUR_CHEST_OUVERT = (255, 255, 255)

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
    haut = (42 if m.tipo == 0 else 98) * config.FOCALE / rz
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
    bases = zone["arbres"]
    if len(bases):
        _, _, rz, v = projeter_3d_masse(bases)
        vis = np.nonzero(v)[0]
        if len(vis):
            for segs, p in zip(_segments_entites(bases[vis], ARBRE_P1, ARBRE_P2, ARBRE_COULEURS),
                               rz[vis].tolist()):
                if segs:
                    items.append((p - BIAIS_ENTITES, 1, segs, None))

    mons = [m for cle in zone["cles"] for m in monstres_caches[cle]]
    if mons:
        xs = np.array([m.x for m in mons])
        zs = np.array([m.z for m in mons])
        tipo = np.array([m.tipo for m in mons])
        phase = np.array([m.phase for m in mons])
        araignee = tipo == 0
        saut = np.where(araignee, np.sin(temps * 12 + phase) * 6, np.sin(temps * 6 + phase) * 15)
        decal = np.where(araignee, 0.0, -40.0)
        pos = np.column_stack((xs, get_hauteur_sol(xs, zs) + decal + saut, zs)).astype(np.float32)
        ex, ey, rz, v = projeter_3d_masse(pos)

        for id_t, P1, P2, col in ((0, ARAIGNEE_P1, ARAIGNEE_P2, COULEUR_ARAIGNEE),
                                  (1, DRONE_P1, DRONE_P2, COULEUR_DRONE)):
            sel = np.nonzero(v & (tipo == id_t))[0]
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
        bob = np.sin(temps * 3 + arr[:, 0] * 0.01) * 6 + 45
        pos = np.column_stack((arr[:, 0],
                               get_hauteur_sol(arr[:, 0], arr[:, 1]) + bob,
                               arr[:, 1])).astype(np.float32)
        _, _, rz, v = projeter_3d_masse(pos)
        ang = temps * 2.0
        for id_t, P1, P2, col in ((0, MUN_P1, MUN_P2, COULEUR_MUNITIONS),
                                  (1, SOIN_P1, SOIN_P2, COULEUR_SOIN)):
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
            is_prisma = chest["type"] == "PRISMATIC_CHEST"
            ouvert = chest["ouvert"]

            if ouvert:
                P1, P2 = (PRISMA_P1, PRISMA_P2) if is_prisma else (CHEST_P1, CHEST_P2)
                base = COULEUR_CHEST_OUVERT
            elif is_prisma:
                P1, P2 = PRISMA_P1, PRISMA_P2
                puls = 0.55 + 0.45 * math.sin(
                    temps * 5 + chest["x"] * 0.13 + chest["z"] * 0.07)
                base = (int(180 * puls + 60), int(60 + 130 * puls), 255)
            else:
                P1, P2 = CHEST_P1, CHEST_P2
                base = COULEUR_CHEST

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
    y_offset = (1.0 - t_anim) * 120.0 + 30.0

    bob = np.sin(temps * 3 + ph) * 6
    ys = (get_hauteur_sol(xs, zs) + bob + y_offset).astype(np.float32)

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
        base = boosts.COULEURS_RARETE[butins[i].rarete]
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
def ouvrir_coffre_proche(zone, joueur_x, joueur_z, distance=DISTANCE_INTERACTION_COFFRE):
    meilleur = None
    meilleure_dist = distance
    for cle in zone["cles"]:
        for chest in chest_caches[cle]:
            if chest["ouvert"]:
                continue
            d = math.hypot(chest["x"] - joueur_x, chest["z"] - joueur_z)
            if d < meilleure_dist:
                meilleure_dist = d
                meilleur = chest
    if meilleur is None:
        return None
    meilleur["ouvert"] = True
    butin = boosts.tirer_butin(meilleur["type"], meilleur["x"], meilleur["z"])
    boosts.spawner_butin(butin)
    return butin

# ---------------------------------------------------------------------------
# Overlay debug
# ---------------------------------------------------------------------------
def dessiner_debug_stats(surf, joueur, stats):
    font = pygame.font.SysFont(None, 22)
    lignes = [
        f"PV : {joueur.pv}/{config.JOUEUR_PV_MAX}",
        f"Vitesse : x{stats.vitesse_mult:.2f}  (+{int(stats.vitesse_bonus*100)}%)",
        f"Saut : x{stats.saut_mult:.2f}  (+{int(stats.saut_bonus*100)}%)",
        f"Degats : x{stats.degats_mult:.2f}  (+{int(stats.degats_bonus*100)}%)",
        f"Auto-regen : {'ON' if stats.auto_regen else 'off'}",
        f"Munitions : {joueur.chargeur} / {joueur.reserve}",
        f"Kills : {joueur.kills}",
    ]
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
        self.debug_stats = DEBUG_STATS
        self.terminal = TerminalInventory()
        self.en_inventaire = False
        self.reinitialiser()

    def reinitialiser(self):
        reinitialiser_monde()
        entity.reinitialiser_entites()
        boosts.vider_butins()
        boss_module.reinitialiser_boss()
        self.stats = StatsBoostes()
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
        if not j.tenter_tir():
            return
        self.tir_t = 0.10
        mult = self.stats.degats_mult
        base_degats = config.DEGATS_TIR
        config.DEGATS_TIR = base_degats * mult
        try:
            self.tir_fin, _, _ = entity.tirer_laser(self.zone["cles"], j)
        finally:
            config.DEGATS_TIR = base_degats

    def interagir_coffre(self):
        butin = ouvrir_coffre_proche(self.zone, config.cam_x, config.cam_z)
        return butin

    def recharger(self):
        if self.joueur.mort:
            self.reinitialiser()
        else:
            self.joueur.lancer_recharge()

    def mettre_a_jour(self, dt, temps, avant, cote, saut):
        config.mettre_a_jour_rayons()
        j = self.joueur
        j.mettre_a_jour(dt)
        self.stats.update(dt, j)
        self.tir_t = max(0.0, self.tir_t - dt)
        self.popup_timer = max(0.0, self.popup_timer - dt)
        if j.mort:
            return

        vitesse = 250 * self.stats.vitesse_mult * dt
        rad = math.radians(config.yaw)
        config.cam_x += (avant * math.sin(rad) + cote * math.cos(rad)) * vitesse
        config.cam_z += (avant * math.cos(rad) - cote * math.sin(rad)) * vitesse

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
        boosts.ramasser_butins(j, self.stats, config.cam_x, config.cam_z, dt)

        entity.mettre_a_jour_monstres(dt, self.zone["cles"], j, temps)
        entity.mettre_a_jour_projectiles(dt, j)
        entity.mettre_a_jour_pickups(j, dt)
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
            dessiner_debug_stats(surf, j, self.stats)

        if self.en_inventaire:
            overlay = pygame.Surface((config.LARGEUR, config.HAUTEUR), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160)) # Voile noir semi-transparent (effet pause)
            surf.blit(overlay, (0, 0))
            
            font_term = pygame.font.SysFont(None, 24)
            self.terminal.dessiner(surf, font_term)

        if j.mort:
            self.hud.dessiner_game_over(surf, j, temps)

# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    fenetre = pygame.display.set_mode((config.LARGEUR, config.HAUTEUR))
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
                    jeu.interagir_coffre()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    jeu.recharger()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3:
                    jeu.debug_stats = not jeu.debug_stats
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and jeu.joueur.mort:
                    jeu.recharger()

        # Vraie pause totale du jeu si l'inventaire est ouvert
        if not jeu.en_inventaire:
            touches = pygame.key.get_pressed()
            jeu.mettre_a_jour(dt, temps,
                              touches[pygame.K_z] - touches[pygame.K_s],
                              touches[pygame.K_d] - touches[pygame.K_q],
                              touches[pygame.K_SPACE])

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