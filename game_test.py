# game_test.py  --  FPS rétro synthwave
import math
import sys
import time
from itertools import repeat
from operator import itemgetter

import numpy as np
import pygame

import config
import entity
import boosts
from boosts import StatsBoostes
from entity import Joueur
from renderer import (vers_camera, ecran_depuis_camera, projeter_3d_masse,
                      clipper_near, transformer_vertices_monde)
from terrain import (get_hauteur_sol, get_zone, reinitialiser_monde,
                     monstres_caches, chest_caches)
from modeles import (MODELE_ARBRE, MODELE_ARAIGNEE, MODELE_DRONE,
                     MODELE_MUNITIONS, MODELE_SOINS,
                     MODELE_CHEST, PRISMATIC_CHEST)
from ciel import Ciel
from hud import HUD, MUZZLE, CYAN, BLANC


# ---------------------------------------------------------------------------
# Échelles globales
# ---------------------------------------------------------------------------
ECHELLE_ARBRE    = 1.0
ECHELLE_ARAIGNEE = 1.0
ECHELLE_DRONE    = 1.0
ECHELLE_PICKUP   = 3.0        # ← plus visible
ECHELLE_CHEST    = 1.0
ECHELLE_BUTIN    = 22.0       # ← pyramides plus grosses

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
            couleurs = [FOG_LUT[i] for i in fog.tolist()]
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
        items.append((prof, 2, (pts2, flags), _couleur_fog(prof)))


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
                    items.append((p - BIAIS_ENTITES - 5, 1, _barre_vie(int(ex[i]), int(ey[i]), p, m), None))

    if entity.pickups:
        arr = np.array(entity.pickups, dtype=np.float64)   # [x, z, type, t]
        bob = np.sin(temps * 3 + arr[:, 0] * 0.01) * 6 + 45
        pos = np.column_stack((arr[:, 0], get_hauteur_sol(arr[:, 0], arr[:, 1]) + bob, arr[:, 1])).astype(np.float32)
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
            items.append((float(rz[i]) - 20, 4, ((int(ax[i]), int(ay[i])), (int(bx[i]), int(by[i]))), None))


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
# Butins pyramides (avec pop-in visible)
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

    # Pop-in : grandit de 0.3 à 1 sur 0.35 s, et descend de +120 à +30
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
        P1r = PYR_P1 * sc
        P2r = PYR_P2 * sc
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
# Dessin
# ---------------------------------------------------------------------------
def dessiner_items(surf, items):
    items.sort(key=itemgetter(0), reverse=True)
    poly, ligne = pygame.draw.polygon, pygame.draw.line
    noir = config.COULEUR_REMPLISSAGE

    for prof, genre, data, col in items:
        if genre == 0:
            poly(surf, noir, data)
            if prof < DIST_GLOW_TERRAIN:
                poly(surf, glow_de(col), data, 4)
            poly(surf, col, data, 2 if prof < DIST_BORD_EPAIS else 1)
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
        self.reinitialiser()

    def reinitialiser(self):
        reinitialiser_monde()
        entity.reinitialiser_entites()
        boosts.vider_butins()
        self.stats = StatsBoostes()
        config.cam_x, config.cam_z = config.DEPART_X, config.DEPART_Z
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
        if butin is None:
            return
        self.popup_text = f"+ {butin.nom}"
        self.popup_timer = 2.0
        self.popup_color = boosts.COULEURS_RARETE[butin.rarete]

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

        sol = get_hauteur_sol(config.cam_x, config.cam_z) - 30
        if saut and abs(config.cam_y - sol) < 2:
            config.vitesse_y = -300 * self.stats.saut_mult
        config.vitesse_y += config.gravite * dt
        config.cam_y += config.vitesse_y * dt
        if config.cam_y > sol:
            config.cam_y = sol
            config.vitesse_y = 0

        self._maj_zone()
        boosts.ramasser_butins(j, self.stats, config.cam_x, config.cam_z)

        entity.mettre_a_jour_monstres(dt, self.zone["cles"], j, temps)
        entity.mettre_a_jour_projectiles(dt, j)
        entity.mettre_a_jour_pickups(j)

    def rendre(self, temps):
        surf = self.surf
        self.ciel.dessiner(surf, temps)

        items = []
        collecter_terrain(self.zone, items)
        collecter_coffres(self.zone, items, temps)
        collecter_butins(items, temps)
        collecter_entites(self.zone, items, temps)
        dessiner_items(surf, items)

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
        self.hud.dessiner(surf, j, temps)

        # Popup de butin
        if self.popup_timer > 0 and self.popup_text:
            alpha = min(1.0, self.popup_timer / 0.4)   # fondu sur les 0.4 dernières s
            color = self.popup_color
            txt = self.font_popup.render(self.popup_text, True, color)
            # Fond sombre semi-transparent
            pad = 16
            bg = pygame.Surface((txt.get_width() + pad * 2, txt.get_height() + pad),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, int(140 * alpha)))
            cx = config.LARGEUR // 2
            cy = config.HAUTEUR - 260
            surf.blit(bg, (cx - bg.get_width() // 2, cy - bg.get_height() // 2))
            txt.set_alpha(int(255 * alpha))
            surf.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))

        if j.mort:
            self.hud.dessiner_game_over(surf, j, temps)


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
            elif event.type == pygame.MOUSEMOTION:
                jeu.regarder(*event.rel)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                jeu.tirer()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                jeu.interagir_coffre()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                jeu.recharger()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and jeu.joueur.mort:
                jeu.recharger()

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