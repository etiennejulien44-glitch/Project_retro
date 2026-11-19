# world/entity.py
from data import boosts
from world import butin
import math
import random
import time
import numpy as np
from data import config
from world import boss as boss_module
from world import balistique
from world.monstre import ABSORBE
from .terrain import get_hauteur_sol, monstres_caches, bloque_point, bloque_segment
from engine.renderer import projeter_3d_masse
from engine import effets, rendu_monstres
from engine.geometrie import diff_angle

projectiles = []
pickups = []       # [x, z, type, spawn_time]
zaps = []          # éclairs du zap_chaine : [x1, y1, z1, x2, y2, z2, durée_restante]
monstres_actifs = []   # monstres des chunks chargés, recalculé 1 fois par frame (mettre_a_jour_monstres)

DELAI_RAMASSAGE = 0.6


class Joueur:
    def __init__(self):
        self.reinitialiser()

    def reinitialiser(self):
        self.pv = config.JOUEUR_PV_MAX
        self.chargeur = config.CHARGEUR_TAILLE
        self.reserve = config.MUNITIONS_RESERVE_DEPART
        self.t_recharge = 0.0
        self.t_cadence = 0.0
        self.flash_degats = 0.0
        self.t_hit = 0.0
        self.t_kill = 0.0
        self.message = ""
        self.t_message = 0.0
        self.kills = 0
        self.score = 0
        self.facteur_source = 1.0
        self.mort = False

    def progression_recharge(self):
        if self.t_recharge <= 0:
            return 0.0
        return 1.0 - self.t_recharge / config.RECHARGE_DUREE

    def dire(self, texte, duree=1.3):
        self.message = texte
        self.t_message = duree

    def prendre_degats(self, n):
        if self.mort:
            return
        n = n * self.facteur_source               # dégâts infligés réduits par la Corruption (world/competences.py)
        if n <= 0:
            return
        if config.REDUCTION_DEGATS > 0:           # armures : casque / jambières / bottes...
            n = max(1, int(round(n * (1.0 - config.REDUCTION_DEGATS))))
        self.pv -= n
        self.flash_degats = 0.35
        if self.pv <= 0:
            self.pv = 0
            self.mort = True

    def soigner(self, n):
        self.pv = min(config.JOUEUR_PV_MAX, self.pv + n)

    def ajouter_munitions(self, n):
        place_reserve = config.MUNITIONS_RESERVE_MAX - self.reserve
        ajout = min(n, place_reserve)
        self.reserve += ajout
        reste = n - ajout
        if reste > 0:
            place_chargeur = config.CHARGEUR_TAILLE - self.chargeur
            self.chargeur += min(reste, place_chargeur)

    def lancer_recharge(self):
        if (self.mort or self.t_recharge > 0 or self.reserve <= 0
                or self.chargeur >= config.CHARGEUR_TAILLE):
            return False
        self.t_recharge = config.RECHARGE_DUREE
        return True

    def tenter_tir(self):
        if self.mort or self.t_recharge > 0 or self.t_cadence > 0:
            return False
        if self.chargeur <= 0:
            if self.reserve > 0:
                self.lancer_recharge()
            else:
                self.dire("PLUS DE MUNITIONS")
            return False
        self.chargeur -= 1
        self.t_cadence = config.CADENCE_TIR
        if self.chargeur == 0 and self.reserve > 0:
            self.lancer_recharge()
        return True

    def mettre_a_jour(self, dt):
        self.t_cadence = max(0.0, self.t_cadence - dt)
        self.flash_degats = max(0.0, self.flash_degats - dt)
        self.t_hit = max(0.0, self.t_hit - dt)
        self.t_kill = max(0.0, self.t_kill - dt)
        self.t_message = max(0.0, self.t_message - dt)
        if self.t_recharge > 0:
            self.t_recharge -= dt
            if self.t_recharge <= 0:
                self.t_recharge = 0.0
                pris = min(config.CHARGEUR_TAILLE - self.chargeur, self.reserve)
                self.chargeur += pris
                self.reserve -= pris


def reinitialiser_entites():
    projectiles.clear()
    pickups.clear()
    zaps.clear()
    monstres_actifs.clear()
    effets.reinitialiser()


def ligne_de_vue(x0, y0, z0, x1, y1, z1, n=14):
    t = np.linspace(0.05, 0.95, n)
    xs = x0 + (x1 - x0) * t
    zs = z0 + (z1 - z0) * t
    ys = y0 + (y1 - y0) * t
    sol = get_hauteur_sol(xs, zs)
    return not np.any(ys > sol - 3) and not bloque_segment(x0, y0, z0, x1, y1, z1)


def deposer_butin(x, z):
    """Drop à la mort d'un monstre : tiré parmi les boosts qui ont un "pickup" (data/boosts.py)."""
    r = random.random()
    t = time.time()
    acc = 0.0
    for idx, def_id in enumerate(boosts.PICKUP_IDS):
        acc += boosts.BOOSTS[def_id]["pickup"].get("drop", 0.0)
        if r < acc:
            pickups.append([x, z, idx, t])
            break
    if len(pickups) > 80:
        pickups.pop(0)


def mettre_a_jour_pickups(joueur, dt, stats):
    """Ramassage au contact (sans aimant), seulement si config.RAMASSAGE_AUTO. Sinon : touche F."""
    if joueur.mort or not config.RAMASSAGE_AUTO:
        return
    now = time.time()
    restants = []
    for p in pickups:
        if now - p[3] < DELAI_RAMASSAGE:
            restants.append(p)
            continue
        d = math.hypot(p[0] - config.cam_x, p[1] - config.cam_z)

        if d < config.RAYON_RAMASSAGE_BUTINS:
            if not butin.appliquer(boosts.PICKUP_IDS[int(p[2])], stats, joueur):
                restants.append(p)        # plein : reste au sol
            continue

        restants.append(p)
    pickups[:] = restants


def _hauteur_centre(m):
    return get_hauteur_sol(m.x, m.z) + m.data.get("hauteur_centre", -20)


# ===========================================================================
#  IA DES MONSTRES -- registre de comportements
#  data/monstres.py -> "comportement": "nom"   <->   @comportement("nom") ci-dessous.
#  Une IA reçoit (monstre, dt, joueur, temps) et pilote m.x / m.z / m.etat / m.t_etat.
# ===========================================================================
COMPORTEMENTS = {}


def comportement(nom):
    def deco(f):
        COMPORTEMENTS[nom] = f
        return f
    return deco


def mettre_a_jour_monstres(dt, cles, joueur, temps):
    global monstres_actifs
    monstres_actifs = [m for cle in cles for m in monstres_caches[cle]]
    for m in monstres_actifs:
        m.hit = max(0.0, m.hit - dt)
        if m.allie:
            _ia_allie(m, dt, joueur, temps, cles)
            continue
        if m.ralenti <= 0.0:
            continue                                         # étourdi
        joueur.facteur_source = m.mult_inf
        COMPORTEMENTS[m.data["comportement"]](m, dt * m.ralenti, joueur, temps)
    joueur.facteur_source = 1.0


@comportement("melee")
def _ia_melee(m, dt, joueur, temps):
    dx, dz = config.cam_x - m.x, config.cam_z - m.z
    d = math.hypot(dx, dz)
    if d >= m.data["aggro"]:
        return
    if d > m.data["portee"]:
        m.x += dx / d * m.data["vitesse"] * dt
        m.z += dz / d * m.data["vitesse"] * dt
        m.cd = max(m.cd, 0.4)
    else:
        m.cd -= dt
        if m.cd <= 0:
            joueur.prendre_degats(m.data["degats"])
            m.cd = m.data["cooldown"]


@comportement("distance")
def _ia_distance(m, dt, joueur, temps):
    dx, dz = config.cam_x - m.x, config.cam_z - m.z
    d = math.hypot(dx, dz)
    if d >= m.data["aggro"] or d < 1e-6:
        return
    v = m.data["vitesse"] * dt
    dist_pref = m.data.get("dist_pref", 80.0)

    if d > dist_pref + 80:
        m.x += dx / d * v
        m.z += dz / d * v
    elif d < dist_pref - 150:
        m.x -= dx / d * v
        m.z -= dz / d * v
    lat = math.sin(temps * 0.8 + m.phase) * v * 0.7
    m.x += -dz / d * lat
    m.z += dx / d * lat

    m.cd -= dt
    portee_maximale = m.data.get("portee_tir", 150.0)
    if m.cd <= 0 and d < portee_maximale and not joueur.mort:
        _tirer_projectile(m)
        m.cd = m.data["cooldown"] + random.random() * 0.8


@comportement("striker")
def _ia_striker(m, dt, joueur, temps):
    """Ligne électrique : repos -> vise (se verrouille juste avant de partir) -> fonce en ligne droite -> repos."""
    D = m.data
    dx, dz = config.cam_x - m.x, config.cam_z - m.z
    d = math.hypot(dx, dz) or 1e-6
    m.t_etat -= dt
    if m.etat == "repos":
        if d < D["aggro"]:
            m.dir_x, m.dir_z = dx / d, dz / d
            if m.t_etat <= 0 and not joueur.mort:
                m.etat, m.t_etat = "vise", D["duree_vise"]
    elif m.etat == "vise":
        if m.t_etat > D["verrou"]:                          # suit le joueur... jusqu'au verrouillage
            m.dir_x, m.dir_z = dx / d, dz / d
        if m.t_etat <= 0:
            m.etat, m.t_etat = "fonce", D["duree_charge"]
    elif m.etat == "fonce":
        pas = D["vitesse_charge"] * dt
        nx, nz = m.x + m.dir_x * pas, m.z + m.dir_z * pas
        y = float(get_hauteur_sol(nx, nz)) + D["hauteur_centre"]
        fini = False
        if bloque_point(nx, y, nz):                          # un couvert l'arrête (et l'éclate en étincelles)
            effets.etincelles((m.x, y, m.z), D["couleur"], n=8)
            fini = True
        else:
            m.x, m.z = nx, nz
            if (math.hypot(config.cam_x - m.x, config.cam_z - m.z) < D["rayon_contact"]
                    and abs(config.cam_y - y) < 55 and not joueur.mort):
                joueur.prendre_degats(D["degats"])
                effets.etincelles((m.x, y, m.z), (255, 40, 40), n=10)
                fini = True
        if fini or m.t_etat <= 0:
            m.etat, m.t_etat = "repos", D["cooldown"]


@comportement("shield")
def _ia_shield(m, dt, joueur, temps):
    """Polygone Shield : présente toujours une face DEBOUT vers le joueur, mais pivote lentement :
    il faut lui tourner autour pour viser une face détruite et toucher le coeur."""
    D = m.data
    dx, dz = config.cam_x - m.x, config.cam_z - m.z
    d = math.hypot(dx, dz)
    if d >= D["aggro"] or d < 1e-6:
        return
    phi = math.atan2(dx, dz)
    n = len(m.faces)
    pas = 2 * math.pi / n
    debout = [i for i in range(n) if m.faces[i]]
    cible = m.rot
    if debout:
        meilleure = min(debout, key=lambda i: abs(diff_angle(phi - i * pas, m.rot)))
        cible = phi - meilleure * pas
    delta = diff_angle(cible, m.rot)
    maxi = D["vit_rot"] * dt
    m.rot += max(-maxi, min(maxi, delta))
    if d > D["portee"]:
        m.x += dx / d * D["vitesse"] * dt
        m.z += dz / d * D["vitesse"] * dt
        m.cd = max(m.cd, 0.4)
    else:
        m.cd -= dt
        if m.cd <= 0 and not joueur.mort:
            joueur.prendre_degats(D["degats"])
            m.cd = D["cooldown"]


@comportement("phasme")
def _ia_phasme(m, dt, joueur, temps):
    """Traqueur de grille : voyage SOUS le sol (distorsion visible dans le maillage, intouchable),
    surgit au dernier moment, mord, reste exposé un instant puis replonge."""
    D = m.data
    dx, dz = config.cam_x - m.x, config.cam_z - m.z
    d = math.hypot(dx, dz) or 1e-6
    m.t_etat -= dt
    if m.etat == "traque":
        m.y_haut = 0.0
        if d < D["aggro"]:
            v = D["vitesse"] * (D["bonus_proche"] if d < D["dist_rush"] else 1.0) * dt
            lat = math.sin(temps * 3.0 + m.phase) * 0.5          # trajectoire sinueuse
            ux, uz = dx / d, dz / d
            m.x += (ux - uz * lat) * v
            m.z += (uz + ux * lat) * v
            if d < D["dist_surgir"] and m.t_etat <= 0 and not joueur.mort:
                m.etat, m.t_etat = "surgit", D["duree_surgit"]
                effets.onde(m.x, m.z, amp=config.ONDE_MORT_AMP * 0.7)
    elif m.etat == "surgit":
        m.y_haut = min(1.0, 1.0 - m.t_etat / D["duree_surgit"])
        if m.t_etat <= 0:
            m.etat, m.t_etat, m.y_haut, m.cd = "surgi", D["duree_expose"], 1.0, D["cooldown_attaque"] * 0.5
            effets.etincelles((m.x, float(get_hauteur_sol(m.x, m.z)) - 20, m.z), D["couleur"], n=10)
            if d < D["portee_attaque"] and not joueur.mort:
                joueur.prendre_degats(D["degats"])
    elif m.etat == "surgi":
        m.cd -= dt
        if m.cd <= 0 and d < D["portee_attaque"] and not joueur.mort:
            joueur.prendre_degats(D["degats"])
            m.cd = D["cooldown_attaque"]
        if m.t_etat <= 0:
            m.etat, m.t_etat = "plonge", D["duree_plonge"]
    elif m.etat == "plonge":
        m.y_haut = max(0.0, m.t_etat / D["duree_plonge"])
        if m.t_etat <= 0:
            m.etat, m.t_etat, m.y_haut = "traque", D["cooldown"], 0.0


def _ia_allie(m, dt, joueur, temps, cles):
    """Ennemi piraté (Contrôle total) : attaque l'ennemi le plus proche, sinon suit le joueur. Stats +50%."""
    D = m.data
    vit = max(120.0, float(D.get("vitesse", 0.0))) * 1.5
    cible, dmin = None, 900.0
    for autre in monstres_actifs:
        if autre is m or autre.allie:
            continue
        d = math.hypot(autre.x - m.x, autre.z - m.z)
        if d < dmin:
            cible, dmin = autre, d
    if cible is not None:
        tx, tz, portee = cible.x, cible.z, 70.0
    else:
        tx, tz, portee = config.cam_x, config.cam_z, 160.0     # reste près du joueur
    dx, dz = tx - m.x, tz - m.z
    d = math.hypot(dx, dz) or 1e-6
    if d > portee:
        m.x += dx / d * vit * dt
        m.z += dz / d * vit * dt
    elif cible is not None:
        m.cd -= dt
        if m.cd <= 0:
            m.cd = D.get("cooldown", 1.2)
            _blesser_monstre(cible, float(D.get("degats", 6)) * 1.5, cles, joueur, m.x, m.z)


def sources_distorsion():
    """Distorsions continues pour la grille : [(x, z, amplitude, sigma)] (monstres à champ "distorsion")."""
    res = []
    for m in monstres_actifs:
        dist = m.data.get("distorsion")
        if dist and m.etat != "surgi":
            res.append((m.x, m.z, dist["amp"] * (1.0 - m.y_haut), dist["sigma"]))
    return res


def _tirer_projectile(m):
    x, y, z = m.x, _hauteur_centre(m), m.z
    dx, dy, dz = config.cam_x - x, config.cam_y - y, config.cam_z - z
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    v = config.PROJECTILE_VITESSE
    projectiles.append([x, y, z, dx / n * v, dy / n * v, dz / n * v, config.PROJECTILE_VIE,
                        config.PROJECTILE_DEGATS * m.mult_inf])


def mettre_a_jour_projectiles(dt, joueur):
    balistique.avancer(projectiles, dt, joueur, config.PROJECTILE_RAYON ** 2)


def _impact_sol():
    """Point où le rayon de visée (centre de l'écran) touche le sol, ou None (tir dans le ciel)."""
    yaw, pit = math.radians(config.yaw), math.radians(config.pitch)
    fx, fy, fz = math.cos(pit) * math.sin(yaw), math.sin(pit), math.cos(pit) * math.cos(yaw)
    t = np.linspace(40.0, config.PORTEE_TIR, 28)
    xs, ys, zs = config.cam_x + fx * t, config.cam_y + fy * t, config.cam_z + fz * t
    g = ys - get_hauteur_sol(xs, zs)                         # > 0 : sous le sol (Y vers le bas)
    bas = g > 0
    if not bas.any():
        return None
    i = int(np.argmax(bas))
    f = 0.0 if i == 0 else float(-g[i - 1] / (g[i] - g[i - 1]))
    j = max(i - 1, 0)
    return (float(xs[j] + (xs[i] - xs[j]) * f), float(ys[j] + (ys[i] - ys[j]) * f), float(zs[j] + (zs[i] - zs[j]) * f))


# Modificateurs de tir posés par world/competences.py avant chaque tir (portée, pénétration)
tir_mod = {"portee": 1.0, "penetration": 0}
dernier_tir = {"cible": None, "pos": None}       # lu par world/competences.py (ricochet, stacking, dôme)


def _candidats(cles):
    """Tout ce qui est sous le réticule : boss, satellites, monstres (triés plus tard par distance)."""
    cx, cy = config.LARGEUR // 2, config.HAUTEUR // 2
    candidats = []
    aim = 1.0 + config.AUTO_AIM * config.AUTO_AIM_RAYON       # casque : aide à la visée
    F = config.FOCALE
    portee = config.PORTEE_TIR * tir_mod["portee"]
    traverse = tir_mod["penetration"] > 0                      # pénétration : on tire à travers les couverts

    b = _boss_ciblable()
    if b is not None:
        bx, by, bz = b.centre()
        ex, ey, rz, v = projeter_3d_masse(np.array([[bx, by, bz]], dtype=np.float32))
        if v[0] and rz[0] < portee:
            rayon_screen = min(b.rayon_visee * F / max(rz[0], 1.0), 250.0) * aim
            if math.hypot(int(ex[0]) - cx, int(ey[0]) - cy) < rayon_screen:
                if traverse or ligne_de_vue(config.cam_x, config.cam_y, config.cam_z, bx, by, bz):
                    candidats.append({"type": "boss", "obj": b, "ex": int(ex[0]), "ey": int(ey[0]),
                                      "rz": float(rz[0]), "pos": (bx, by, bz)})

    for sat in boss_module.satellites_ciblables():             # tourelles satellites du boss
        ex, ey, rz, v = projeter_3d_masse(np.array([[sat.x, sat.y, sat.z]], dtype=np.float32))
        if v[0] and rz[0] < portee:
            rayon_screen = max(30.0 * F / max(rz[0], 1.0), 22.0) * aim
            if math.hypot(int(ex[0]) - cx, int(ey[0]) - cy) < rayon_screen:
                candidats.append({"type": "satellite", "obj": sat, "ex": int(ex[0]), "ey": int(ey[0]),
                                  "rz": float(rz[0]), "pos": (sat.x, sat.y, sat.z)})

    mons = [m for cle in cles for m in monstres_caches[cle] if m.ciblable]
    if mons:
        xs = np.fromiter((m.x for m in mons), np.float64, len(mons))
        zs = np.fromiter((m.z for m in mons), np.float64, len(mons))
        hc = np.fromiter((m.data.get("hauteur_centre", -20) for m in mons), np.float64, len(mons))
        ray = np.fromiter((m.data.get("rayon_visee", 40.0) for m in mons), np.float64, len(mons))
        pos = np.column_stack((xs, get_hauteur_sol(xs, zs) + hc, zs)).astype(np.float32)
        ex, ey, rz, v = projeter_3d_masse(pos)
        rayon_screen = np.maximum(ray * F / np.maximum(rz, 1.0), 22.0) * aim
        ok = v & (rz < portee) & (np.hypot(ex - cx, ey - cy) < rayon_screen)
        for i in np.nonzero(ok)[0].tolist():
            if traverse or ligne_de_vue(config.cam_x, config.cam_y, config.cam_z,
                                        float(pos[i][0]), float(pos[i][1]), float(pos[i][2])):
                candidats.append({"type": "monstre", "obj": mons[i], "ex": int(ex[i]), "ey": int(ey[i]),
                                  "rz": float(rz[i]), "pos": tuple(pos[i].tolist())})
    candidats.sort(key=lambda x: x["rz"])
    return candidats


def cible_visee(cles):
    """Monstre sous le réticule (le plus proche), ou None. Sert aux compétences ciblées (virus, piratage)."""
    for c in _candidats(cles):
        if c["type"] == "monstre":
            return c["obj"]
    return None


def tirer_laser(cles, joueur):
    candidats = _candidats(cles)
    dernier_tir["cible"], dernier_tir["pos"] = None, None
    if not candidats:
        imp = _impact_sol()                                  # tir raté : impact + onde dans la grille
        if imp is not None:
            dernier_tir["pos"] = imp
            effets.etincelles(imp, (60, 240, 255), n=4, vitesse=170.0, taille=6.0)
            effets.onde(imp[0], imp[2], amp=config.ONDE_TIR_AMP * 0.8)
        return None, False, False

    fin, mort_premier = None, False
    for k, c in enumerate(candidats[:1 + tir_mod["penetration"]]):       # pénétration : le tir traverse N cibles
        if c["type"] == "boss":
            boss_module.toucher_boss(config.DEGATS_TIR)
            joueur.t_hit = 0.15
            effets.etincelles(c["pos"], (255, 30, 30), n=6)
            _zap_chaine(c["obj"], cles, joueur, config.DEGATS_TIR)
            mort = False
        elif c["type"] == "satellite":
            boss_module.toucher_satellite(c["obj"], config.DEGATS_TIR, joueur)
            joueur.t_hit = 0.15
            mort = False
        else:
            m = c["obj"]
            _zap_chaine(m, cles, joueur, config.DEGATS_TIR)     # avant la mort : on a besoin de sa position
            mort = _blesser_monstre(m, config.DEGATS_TIR, cles, joueur)
            if not mort:
                joueur.t_hit = 0.15
        if k == 0:
            fin, mort_premier = (c["ex"], c["ey"]), mort
            dernier_tir["cible"] = c["obj"] if c["type"] == "monstre" else None
            dernier_tir["pos"] = c["pos"]
    return fin, True, mort_premier


# ---------------------------------------------------------------------------
#  Dégâts partagés : tir, zap_chaine (jambières), dash (torse)
# ---------------------------------------------------------------------------
def _blesser_monstre(m, degats, cles, joueur, ox=None, oz=None):
    """Inflige des dégâts à un monstre (kill, score, butin, effets). (ox, oz) = origine du coup (un Polygone
    Shield absorbe les coups qui touchent une de ses faces debout). -> True s'il est mort."""
    if m.allie:
        return False
    degats *= m.vuln                                          # Contrôle / Corruption : dégâts subis augmentés
    if ox is None:
        ox, oz = config.cam_x, config.cam_z
    m.hit = 0.12
    if m.encaisser(degats, ox, oz) == ABSORBE:
        rendu_monstres.casser_face(m)
        return False
    if m.hp > 0:
        effets.etincelles((m.x, _hauteur_centre(m), m.z), (255, 30, 30), n=6)   # ROUGE VIF
        effets.onde(m.x, m.z, amp=config.ONDE_TIR_AMP)
        return False
    for cle in cles:
        if m in monstres_caches[cle]:
            monstres_caches[cle].remove(m)
            break
    joueur.kills += 1
    joueur.score += m.data.get("score", 100)
    joueur.t_kill = 0.25
    rendu_monstres.mort_monstre(m)
    deposer_butin(m.x, m.z)
    return True


def _boss_ciblable():
    b = boss_module.boss
    return b if (b is not None and not b.en_spawn and b.invuln <= 0) else None


def _zap_chaine(depart, cles, joueur, degats):
    """Jambières : l'éclair saute de cible en cible (ZAP_NB sauts, au plus proche à chaque fois),
    chaque éclair inflige dégâts x(1 + ZAP_BONUS_DEGATS)."""
    n = config.ZAP_NB
    if n <= 0:
        return
    dmg = degats * (1.0 + config.ZAP_BONUS_DEGATS)
    cur = depart.centre() if hasattr(depart, "centre") else (depart.x, _hauteur_centre(depart), depart.z)
    touches = {id(depart)}
    mons = [m for cle in cles for m in monstres_caches[cle] if m.ciblable]
    for _ in range(n):
        meilleur, d_min = None, config.ZAP_PORTEE
        for m in mons:
            if id(m) in touches:
                continue
            d = math.hypot(m.x - cur[0], m.z - cur[2])
            if d < d_min:
                meilleur, d_min = m, d
        b = _boss_ciblable()
        if b is not None and id(b) not in touches and math.hypot(b.x - cur[0], b.z - cur[2]) < d_min:
            meilleur = b
        if meilleur is None:
            break
        touches.add(id(meilleur))
        if meilleur is b:
            boss_module.toucher_boss(dmg)
            cible = b.centre()
        else:
            cible = (meilleur.x, _hauteur_centre(meilleur), meilleur.z)
            _blesser_monstre(meilleur, dmg, cles, joueur, cur[0], cur[2])
        zaps.append([cur[0], cur[1], cur[2], cible[0], cible[1], cible[2], 0.25])
        cur = cible


def mettre_a_jour_zaps(dt):
    for z in zaps:
        z[6] -= dt
    zaps[:] = [z for z in zaps if z[6] > 0]


def degats_zone_segment(cles, x0, z0, x1, z1, rayon, degats, joueur):
    """Dash : blesse tous les monstres (et le boss) à moins de `rayon` du segment. -> nb de cibles."""
    sx, sz = x1 - x0, z1 - z0
    l2 = sx * sx + sz * sz or 1.0

    def dist(x, z):
        t = max(0.0, min(1.0, ((x - x0) * sx + (z - z0) * sz) / l2))
        return math.hypot(x - (x0 + sx * t), z - (z0 + sz * t))

    nb = 0
    for m in [m for cle in cles for m in monstres_caches[cle] if m.ciblable]:
        if dist(m.x, m.z) < rayon:
            _blesser_monstre(m, degats, cles, joueur, x0, z0)
            nb += 1
    b = _boss_ciblable()
    if b is not None and dist(b.x, b.z) < rayon + 60:
        boss_module.toucher_boss(degats)
        nb += 1
    if nb:
        joueur.t_hit = 0.2
    return nb
