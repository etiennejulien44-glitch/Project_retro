# engine/scene.py -- LA SCÈNE 3D : transforme le monde (terrain, décors, monstres, boss, effets) en dessins.
#   Reçoit un `jeu` (world/jeu.py) en lecture seule et dessine ; ne modifie jamais l'état du jeu.
import math
from itertools import repeat
from operator import itemgetter

import numpy as np
import pygame

from data import config, modeles, boosts
from data.coffres import COFFRES
from data.decors import DECORS
from engine import geometrie as G, effets, rendu_monstres
from engine.ciel import Ciel
from engine.qualite import qualite
from engine.textes import texte
from engine.renderer import vers_camera, ecran_depuis_camera, projeter_3d_masse, clipper_near
from world import entity, butin, competences
from world import boss as boss_module
from world.terrain import get_hauteur_sol, chest_caches

BLANC = (255, 255, 255)
ECHELLE_BUTIN = 200.0
_aplatir_modele = G.aplatir_modele
_tourner_y = G.tourner_y
_segments_entites = G.segments_entites
BIAIS_ENTITES = G.BIAIS_ENTITES
glow_de = G.glow_de
_Z3 = np.zeros((1, 3), dtype=np.float32)

PYR_P1, PYR_P2 = _aplatir_modele(modeles.MODELE_PYRAMIDE, ECHELLE_BUTIN)

# Pickups (munitions, soin...), décors et coffres : AUTOMATIQUE depuis data/boosts.py, data/decors.py, data/coffres.py
PICKUPS_RENDU = {i: (*_aplatir_modele(boosts.BOOSTS[k]["pickup"]["modele"], boosts.BOOSTS[k]["pickup"]["echelle"]),
                     boosts.BOOSTS[k]["pickup"]["couleur"])
                 for i, k in enumerate(boosts.PICKUP_IDS)}


def _couleurs_decor(spec):
    seuil = -spec["hauteur"] / spec["echelle"] * 0.35
    return [spec["couleur_2"] if max(a[1], b[1]) < seuil else spec["couleur"] for a, b in spec["modele"]]


def _faces_boite_decor(spec):
    """Génère automatiquement les 6 faces d'un décor opaque. -> (F (6,4,3), couleurs, normales (6,3), centres (6,3))
    Les normales servent à NE PAS dessiner les faces dos à la caméra (back-face culling : ~2x moins de polygones)."""
    if not spec.get("opaque"):
        return None
    pts = [p for seg in spec["modele"] for p in seg]
    e = spec["echelle"]
    xs, ys, zs = [p[0] * e for p in pts], [p[1] * e for p in pts], [p[2] * e for p in pts]
    x0, x1, y0, y1, z0, z1 = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    F = np.array([
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
        [(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)],
    ], dtype=np.float32)
    cols = [spec["couleur_2"]] + [spec["couleur"]] * 5
    C = F.mean(axis=1)
    N = np.cross(F[:, 1] - F[:, 0], F[:, 3] - F[:, 0])
    centre = C.mean(axis=0)
    N = np.where((np.einsum("fj,fj->f", N, C - centre) < 0)[:, None], -N, N)
    N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
    return F, cols, N.astype(np.float32), C.astype(np.float32)


DECORS_RENDU = {
    did: (*_aplatir_modele(d["modele"], d["echelle"]), _couleurs_decor(d), _faces_boite_decor(d))
    for did, d in DECORS.items()
}
COFFRES_RENDU = {cle: (*_aplatir_modele(d["modele"], d["echelle"]), d) for cle, d in COFFRES.items()}

# ---------------------------------------------------------------------------
# Terrain (+ GRID WAVE : les ondes décalent les sommets du maillage avant la projection)
# ---------------------------------------------------------------------------
def collecter_terrain(zone, items, temps):
    pts = zone["pts"]
    dy = effets.ondes.deplacement(pts[:, 0], pts[:, 2])
    if dy is not None:
        pts = pts.copy()
        pts[:, 1] += dy
    rx, ry, rz = vers_camera(pts)
    ex, ey = ecran_depuis_camera(rx, ry, rz)
    A, B, C, D = zone["A"], zone["B"], zone["C"], zone["D"]

    proche = rz > config.NEAR
    loin_ok = rz <= config.DIST_AFFICHAGE_MAX
    nA, nB, nC, nD = proche[A], proche[B], proche[C], proche[D]
    tous_proches = nA & nB & nC & nD
    tous_loin_ok = loin_ok[A] & loin_ok[B] & loin_ok[C] & loin_ok[D]
    fog_max_inv = config.FOG_STEPS / config.DIST_AFFICHAGE_MAX
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
            fog = np.minimum((prof * fog_max_inv).astype(np.int32), config.FOG_STEPS - 1)
            polys = np.stack((X, Y), axis=2).tolist()
            couleurs = [fog_lut_biome[i] for i in fog.tolist()]
            items.extend(zip(prof.tolist(), repeat(0), polys, couleurs))

    partiels = np.nonzero((nA | nB | nC | nD) & ~tous_proches & tous_loin_ok)[0]
    W2, H2, F = config.LARGEUR * 0.5, config.HAUTEUR * 0.5, config.FOCALE
    for qi in partiels.tolist():
        poly = [(float(rx[i]), float(ry[i]), float(rz[i])) for i in (A[qi], B[qi], C[qi], D[qi])]
        pts3, flags = clipper_near(poly)
        if len(pts3) < 3:
            continue
        pts2 = [(max(-20000, min(20000, int(W2 + x * F / z))),
                 max(-20000, min(20000, int(H2 + y * F / z)))) for x, y, z in pts3]
        prof = sum(p[2] for p in pts3) / len(pts3)
        i_fog = min(int(prof * fog_max_inv), config.FOG_STEPS - 1)
        items.append((prof, 2, (pts2, flags), fog_lut_biome[i_fog]))


# ---------------------------------------------------------------------------
# BOSS (Spider / Cube rotatif / Icosaèdre) + satellites + ondes néons
# ---------------------------------------------------------------------------
def collecter_boss(items, temps):
    b = boss_module.boss
    if b is None:
        return
    P1, P2, cols = b.segments_monde(temps)
    segs = _segments_entites(_Z3, P1, P2, cols)[0]
    if segs:
        _, _, rz, _ = projeter_3d_masse(np.array([b.centre()], dtype=np.float32))
        items.append((float(rz[0]) - BIAIS_ENTITES, 3, segs, None))
    if isinstance(b, boss_module.BossGeo):
        for s, sp1, sp2, col in b.segments_satellites(temps):
            ssegs = _segments_entites(_Z3, sp1, sp2, [col] * len(sp1))[0]
            if ssegs:
                _, _, rz, _ = projeter_3d_masse(np.array([[s.x, s.y, s.z]], dtype=np.float32))
                items.append((float(rz[0]) - BIAIS_ENTITES, 3, ssegs, None))


_ANG_ANNEAU = np.linspace(0.0, 2.0 * math.pi, 41)


def collecter_ondes_boss(items):
    for o in boss_module.ondes_boss:
        if o.r <= 5:
            continue
        xs, zs = o.x + np.cos(_ANG_ANNEAU) * o.r, o.z + np.sin(_ANG_ANNEAU) * o.r
        pts = np.column_stack((xs, get_hauteur_sol(xs, zs) - 6.0, zs)).astype(np.float32)
        ex, ey, rz, v = projeter_3d_masse(pts)
        if not v.any():
            continue
        k = 1.0 - 0.55 * min(1.0, o.r / o.rmax)
        col = (int(o.couleur[0] * k), int(o.couleur[1] * k), int(o.couleur[2] * k))
        exl, eyl, vl = ex.tolist(), ey.tolist(), v.tolist()
        segs = [((exl[i], eyl[i]), (exl[i + 1], eyl[i + 1]), col) for i in range(40) if vl[i] and vl[i + 1]]
        if segs:
            items.append((float(rz[v].min()) - BIAIS_ENTITES - 100, 3, segs, None))


def collecter_projectiles_boss(items):
    if not boss_module.projectiles_boss:
        return
    arr = np.array(boss_module.projectiles_boss, dtype=np.float32)
    p0 = arr[:, :3]
    vel = arr[:, 3:6]
    p1 = p0 - vel / (np.linalg.norm(vel, axis=1, keepdims=True) + 1e-6) * 55
    ax, ay, rz, va = projeter_3d_masse(p0)
    bx, by, _, vb = projeter_3d_masse(p1)
    for i in np.nonzero(va & vb)[0].tolist():
        items.append((float(rz[i]) - 20, 5, ((int(ax[i]), int(ay[i])), (int(bx[i]), int(by[i]))), None))


# ---------------------------------------------------------------------------
# Entités
# ---------------------------------------------------------------------------
def collecter_entites(zone, items, temps):
    cam = np.array([config.cam_x, config.cam_y, config.cam_z], dtype=np.float32)
    for did, bases in zone["decors"].items():
        _, _, rz, v = projeter_3d_masse(bases)
        vis = np.nonzero(v)[0]
        if not len(vis):
            continue
        P1, P2, cols, faces = DECORS_RENDU[did]
        if faces is not None:
            # Décors opaques : TOUTES les faces de TOUTES les instances projetées en un seul appel numpy,
            # et seules les faces tournées vers la caméra sont dessinées (back-face culling).
            F, fcols, N, FC = faces
            b = bases[vis]
            k = len(b)
            face_vis = np.einsum("kfj,fj->kf", cam - (b[:, None, :] + FC[None]), N) > 0          # (k, 6)
            world = (b[:, None, None, :] + F[None]).reshape(-1, 3)                               # (k*6*4, 3)
            ex_f, ey_f, rz_f, vf = projeter_3d_masse(world)
            ok = face_vis & vf.reshape(k, 6, 4).all(axis=2)
            if not ok.any():
                continue
            prof = rz_f.reshape(k, 6, 4).mean(axis=2)
            polys = np.stack((ex_f.reshape(k, 6, 4), ey_f.reshape(k, 6, 4)), axis=3)
            for i, f in zip(*(a.tolist() for a in np.nonzero(ok))):
                items.append((float(prof[i, f]) - BIAIS_ENTITES, 2, (polys[i, f].tolist(), (True, True, True, True)), fcols[f]))
        else:
            for segs, p in zip(_segments_entites(bases[vis], P1, P2, cols), rz[vis].tolist()):
                if segs:
                    items.append((p - BIAIS_ENTITES, 1, segs, None))

    rendu_monstres.collecter(entity.monstres_actifs, temps, items)

    if entity.pickups:
        arr = np.array(entity.pickups, dtype=np.float64)
        bob = np.sin(temps * 3 + arr[:, 0] * 0.01) * 6 + 22
        pos = np.column_stack((arr[:, 0], get_hauteur_sol(arr[:, 0], arr[:, 1]) - bob, arr[:, 1])).astype(np.float32)
        _, _, rz, v = projeter_3d_masse(pos)
        ang = temps * 2.0
        for id_t, (P1, P2, col) in PICKUPS_RENDU.items():
            sel = np.nonzero(v & (arr[:, 2] == id_t))[0]
            if not len(sel):
                continue
            segs_l = _segments_entites(pos[sel], _tourner_y(P1, ang), _tourner_y(P2, ang), [col] * P1.shape[0])
            for i, segs in zip(sel.tolist(), segs_l):
                if segs:
                    items.append((float(rz[i]) - BIAIS_ENTITES, 3, segs, None))

    if entity.projectiles:
        arr = np.array(entity.projectiles, dtype=np.float32)
        p0 = arr[:, :3]
        vel = arr[:, 3:6]
        p1 = p0 - vel / (np.linalg.norm(vel, axis=1, keepdims=True) + 1e-6) * 45
        ax, ay, rz, va = projeter_3d_masse(p0)
        bx, by, _, vb = projeter_3d_masse(p1)
        for i in np.nonzero(va & vb)[0].tolist():
            items.append((float(rz[i]) - 20, 4, ((int(ax[i]), int(ay[i])), (int(bx[i]), int(by[i]))), None))


# ---------------------------------------------------------------------------
# Coffres (groupés par type : une seule projection numpy par type)
# ---------------------------------------------------------------------------
def collecter_coffres(zone, items, temps):
    tous = [c for cle in zone["cles"] for c in chest_caches[cle]]
    if not tous:
        return
    centres = np.array([[c["x"], c["y"], c["z"]] for c in tous], dtype=np.float32)
    _, _, _, v = projeter_3d_masse(centres)
    par_type = {}
    for i in np.nonzero(v)[0].tolist():
        par_type.setdefault(tous[i]["type"], []).append(tous[i])
    for type_c, lst in par_type.items():
        P1, P2, cdef = COFFRES_RENDU[type_c]
        k, m = len(lst), P1.shape[0]
        R = np.array([c["rotation"] for c in lst], dtype=np.float32)               # (k,3,3)
        pos = np.array([[c["x"], c["y"], c["z"]] for c in lst], dtype=np.float32)  # (k,3)
        w1 = (np.einsum("kij,mj->kmi", R, P1) + pos[:, None, :]).reshape(-1, 3)
        w2 = (np.einsum("kij,mj->kmi", R, P2) + pos[:, None, :]).reshape(-1, 3)
        ax, ay, rz, va = projeter_3d_masse(w1)
        bx, by, _, vb = projeter_3d_masse(w2)
        ok = (va & vb).reshape(k, m)
        AX, AY, BX, BY = (a.reshape(k, m).tolist() for a in (ax, ay, bx, by))
        RZ = rz.reshape(k, m)
        for i, chest in enumerate(lst):
            js = np.nonzero(ok[i])[0].tolist()
            if not js:
                continue
            if chest["ouvert"]:
                base = cdef["couleur_ouvert"]
            elif "couleur_pulse" in cdef:
                puls = 0.55 + 0.45 * math.sin(temps * 5 + chest["x"] * 0.13 + chest["z"] * 0.07)
                c0, c1 = cdef["couleur"], cdef["couleur_pulse"]
                base = tuple(int(c0[n] + (c1[n] - c0[n]) * puls) for n in range(3))
            else:
                base = cdef["couleur"]
            segs = [((AX[i][j], AY[i][j]), (BX[i][j], BY[i][j]), base) for j in js]
            items.append((float(RZ[i][ok[i]].mean()) - BIAIS_ENTITES, 3, segs, None))


# ---------------------------------------------------------------------------
# Éclairs (zap_chaine des jambières)
# ---------------------------------------------------------------------------
def collecter_zaps(items):
    for z in entity.zaps:
        pts = np.array([[z[0], z[1], z[2]], [z[3], z[4], z[5]]], dtype=np.float32)
        ax, ay, rz, ok = projeter_3d_masse(pts)
        if ok[0] and ok[1]:
            items.append((float(min(rz[0], rz[1])) - 20, 4, ((int(ax[0]), int(ay[0])), (int(ax[1]), int(ay[1]))), None))


# ---------------------------------------------------------------------------
# Particules (Vertex Shatter, étincelles) : un seul item pour toutes
# ---------------------------------------------------------------------------
def collecter_particules(items):
    r = effets.particules.segments_ecran()
    if r is not None:
        items.append((r[0] - BIAIS_ENTITES - 60, 1, r[1], None))


# ---------------------------------------------------------------------------
# Compétences : dôme de l'Effondrement, sillages toxiques, infos de piratage au-dessus des ennemis
# ---------------------------------------------------------------------------
_EL = np.radians([0, 22, 44, 66, 84])
_AZ = np.linspace(0.0, 2.0 * math.pi, 33)


def _segments_dome(d):
    cx, cz = d["x"], d["z"]
    y0 = float(get_hauteur_sol(cx, cz))
    R = d["r"]
    pts = []
    for el in _EL:                                              # parallèles
        pts.append(np.stack((cx + R * math.cos(el) * np.cos(_AZ), np.full(33, y0 - R * math.sin(el)),
                             cz + R * math.cos(el) * np.sin(_AZ)), axis=1))
    for az in np.linspace(0, 2 * math.pi, 13)[:-1]:             # méridiens
        e = np.linspace(0.0, math.pi / 2 * 0.95, 9)
        pts.append(np.stack((cx + R * np.cos(e) * math.cos(az), y0 - R * np.sin(e), cz + R * np.cos(e) * math.sin(az)), axis=1))
    return pts


def collecter_competences(items, temps):
    d = competences.dome
    if d is not None:
        reste = d["fin"] - competences.t
        k = 1.0 if reste > 1.5 else max(0.2, reste / 1.5)
        col = (int(255 * k), int(200 * k), int(60 * k))
        tout = np.concatenate(_segments_dome(d)).astype(np.float32)
        ex, ey, rz, v = projeter_3d_masse(tout)
        exl, eyl, vl = ex.tolist(), ey.tolist(), v.tolist()
        segs, i = [], 0
        for n in [33] * len(_EL) + [9] * 12:                      # chaque ligne : segments consécutifs
            segs += [((exl[j], eyl[j]), (exl[j + 1], eyl[j + 1]), col) for j in range(i, i + n - 1) if vl[j] and vl[j + 1]]
            i += n
        if segs:
            items.append((float(rz[v].min()) - BIAIS_ENTITES - 150, 3, segs, None))

    if competences.sillages:
        pts = np.array([[s[0], get_hauteur_sol(s[0], s[1]) - 2.0, s[1]] for s in competences.sillages], dtype=np.float32)
        hauts = pts + np.array([0.0, -14.0, 0.0], dtype=np.float32)
        ex, ey, rz, v = projeter_3d_masse(pts)
        fx_, fy_, _, v2 = projeter_3d_masse(hauts)
        segs = [((int(ex[i]), int(ey[i])), (int(fx_[i]), int(fy_[i])), (190, 60, 255))
                for i in np.nonzero(v & v2)[0].tolist()]
        if segs:
            items.append((float(rz[v].min()) - BIAIS_ENTITES, 1, segs, None))

    if competences.ultime == "controle_total" and competences.niveau("controle_total") > 0:   # passif de l'ultime
        mons = [m for m in entity.monstres_actifs if m.hp > 0]
        if mons:
            pos = np.array([[m.x, get_hauteur_sol(m.x, m.z) - m.data["hauteur_barre"] - 10, m.z] for m in mons], dtype=np.float32)
            ex, ey, rz, v = projeter_3d_masse(pos)
            for i in np.argsort(rz).tolist()[:14]:
                if v[i] and rz[i] < 1400:
                    m = mons[i]
                    txt = (f"ALLIÉ  {m.hp:.0f}/{m.hp_max}" if m.allie
                           else f"{m.hp:.0f}/{m.hp_max}  piratage {competences.chance_piratage(m):.0f}%")
                    img = texte(txt, max(16, int(22 * config.HAUTEUR / 1080)), (60, 240, 255) if m.allie else (255, 230, 120), True)
                    items.append((float(rz[i]) - BIAIS_ENTITES - 300, 8, (int(ex[i]) - img.get_width() // 2, int(ey[i]) - 26, img), None))


# ---------------------------------------------------------------------------
# Butins (vectorisé : tous les butins partagent le même modèle)
# ---------------------------------------------------------------------------
def collecter_butins(items, temps):
    butins = butin.butins_au_sol
    if not butins:
        return
    k = len(butins)
    xs = np.array([b.x for b in butins], dtype=np.float32)
    zs = np.array([b.z for b in butins], dtype=np.float32)
    ph = np.array([b.phase for b in butins], dtype=np.float32)
    spawn = np.array([b.spawn_time for b in butins], dtype=np.float64)
    t_anim = np.clip(temps - spawn, 0.0, 0.35) / 0.35
    sc = (0.3 + 0.7 * t_anim).astype(np.float32)
    y_offset = (1.0 - t_anim) * 120.0 + 40.0                 # jaillit du coffre puis flotte à 40
    ys = (get_hauteur_sol(xs, zs) - np.sin(temps * 3 + ph) * 6 - y_offset).astype(np.float32)
    bases = np.column_stack((xs, ys, zs))
    R1, R2 = _tourner_y(PYR_P1, temps * 2.0), _tourner_y(PYR_P2, temps * 2.0)
    m = R1.shape[0]
    w1 = (bases[:, None, :] + R1[None] * sc[:, None, None]).reshape(-1, 3)
    w2 = (bases[:, None, :] + R2[None] * sc[:, None, None]).reshape(-1, 3)
    ax, ay, rz, va = projeter_3d_masse(w1)
    bx, by, _, vb = projeter_3d_masse(w2)
    ok = (va & vb).reshape(k, m)
    AX, AY, BX, BY = (a.reshape(k, m).tolist() for a in (ax, ay, bx, by))
    RZ = rz.reshape(k, m)
    for i in range(k):
        js = np.nonzero(ok[i])[0].tolist()
        if js:
            base = butins[i].couleur
            segs = [((AX[i][j], AY[i][j]), (BX[i][j], BY[i][j]), base) for j in js]
            items.append((float(RZ[i][ok[i]].mean()) - BIAIS_ENTITES, 3, segs, None))


# ---------------------------------------------------------------------------
# Dessin des items (painter's algorithm)
#   genres : 0 terrain | 1 traits simples | 2 polygone (décor opaque / terrain clippé) | 3 trait néon (halo)
#            4 tir joueur | 5 tir boss | 7 rayon d'énergie (Striker)
# ---------------------------------------------------------------------------
def dessiner_items(surf, items, zone=None):
    items.sort(key=itemgetter(0), reverse=True)
    poly, ligne = pygame.draw.polygon, pygame.draw.line
    noir = config.COULEUR_REMPLISSAGE
    q = qualite.profil()
    d_glow_t, d_glow_e, d_bord = q.glow_terrain, q.glow_entites, q.bord_epais
    couleur_grille = zone.get("couleur_grille", (255, 0, 128)) if zone else (255, 0, 128)
    glitch = effets.glitch_moteur                           # Propagation létale : décor corrompu, murs translucides
    if glitch:
        couleur_grille = (200, 70, 255) if int(effets.temps * 7) % 2 else (110, 0, 150)
    halo_grille = glow_de(couleur_grille)

    for prof, genre, data, col in items:
        if genre == 0:
            poly(surf, noir, data)
            if prof < d_glow_t:                                   # HALO : tracé large sombre...
                poly(surf, halo_grille, data, 4)
            poly(surf, couleur_grille, data, 2 if prof < d_bord else 1)   # ...puis arête fine vive par-dessus
        elif genre == 1:
            for p1, p2, c in data:
                ligne(surf, c, p1, p2, 2)
        elif genre == 3:
            if prof < d_glow_e:
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
        elif genre == 8:                                      # texte (infos de piratage)
            surf.blit(data[2], (data[0], data[1]))
        elif genre == 7:
            if d_glow_e:
                ligne(surf, glow_de(col), data[0], data[1], 12)
            ligne(surf, col, data[0], data[1], 5)
            ligne(surf, BLANC, data[0], data[1], 2)
        else:
            pts, flags = data
            if not glitch:                                    # glitch : pas de remplissage = on voit à travers les murs
                poly(surf, noir, pts)
            n = len(pts)
            for k in range(n):
                if flags[k]:
                    ligne(surf, col, pts[k], pts[(k + 1) % n], 2)




# ---------------------------------------------------------------------------
# La scène
# ---------------------------------------------------------------------------
class Scene:
    def __init__(self):
        self.ciel = Ciel()
        self.nb_items = 0

    def dessiner(self, surf, jeu, temps):
        self.ciel.dessiner(surf, temps)
        effets.ondes.sources = entity.sources_distorsion()      # le Phasme déforme la grille sous ses pas
        zone, items = jeu.zone, []
        collecter_terrain(zone, items, temps)
        collecter_coffres(zone, items, temps)
        collecter_boss(items, temps)
        collecter_ondes_boss(items)
        collecter_projectiles_boss(items)
        collecter_butins(items, temps)
        collecter_zaps(items)
        collecter_entites(zone, items, temps)
        collecter_competences(items, temps)
        collecter_particules(items)
        self.nb_items = len(items)
        dessiner_items(surf, items, zone)
