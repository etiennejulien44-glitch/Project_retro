# world/entity.py
from data import boosts
import math
import random
import time
import numpy as np
from data import config
from world import boss as boss_module
from .terrain import get_hauteur_sol, monstres_caches, bloque_point, bloque_segment
from engine.renderer import projeter_3d_masse

projectiles = []
pickups = []       # [x, z, type, spawn_time]
zaps = []          # éclairs du zap_chaine : [x1, y1, z1, x2, y2, z2, durée_restante]

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
            if not boosts.appliquer(boosts.PICKUP_IDS[int(p[2])], stats, joueur):
                restants.append(p)        # plein : reste au sol
            continue

        restants.append(p)
    pickups[:] = restants


def _hauteur_centre(m):
    return get_hauteur_sol(m.x, m.z) + m.data.get("hauteur_centre", -20)


def mettre_a_jour_monstres(dt, cles, joueur, temps):
    cx, cz = config.cam_x, config.cam_z
    for cle in cles:
        for m in monstres_caches[cle]:
            m.hit = max(0.0, m.hit - dt)
            dx, dz = cx - m.x, cz - m.z
            d = math.hypot(dx, dz)

            if m.data["comportement"] == "melee":
                if d >= m.data["aggro"]:
                    continue
                if d > m.data["portee"]:
                    m.x += dx / d * m.data["vitesse"] * dt
                    m.z += dz / d * m.data["vitesse"] * dt
                    m.cd = max(m.cd, 0.4)
                else:
                    m.cd -= dt
                    if m.cd <= 0:
                        joueur.prendre_degats(m.data["degats"])
                        m.cd = m.data["cooldown"]
            else:
                if d >= m.data["aggro"] or d < 1e-6:
                    continue
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


def _tirer_projectile(m):
    x, y, z = m.x, _hauteur_centre(m), m.z
    dx, dy, dz = config.cam_x - x, config.cam_y - y, config.cam_z - z
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    v = config.PROJECTILE_VITESSE
    projectiles.append([x, y, z, dx / n * v, dy / n * v, dz / n * v, config.PROJECTILE_VIE])


def mettre_a_jour_projectiles(dt, joueur):
    r2 = config.PROJECTILE_RAYON ** 2
    vivants = []
    for p in projectiles:
        p[0] += p[3] * dt
        p[1] += p[4] * dt
        p[2] += p[5] * dt
        p[6] -= dt
        if p[6] <= 0 or p[1] > get_hauteur_sol(p[0], p[2]) or bloque_point(p[0], p[1], p[2]):
            continue
        dx, dy, dz = p[0] - config.cam_x, p[1] - config.cam_y, p[2] - config.cam_z
        if dx * dx + dy * dy + dz * dz < r2:
            joueur.prendre_degats(config.PROJECTILE_DEGATS)
            continue
        vivants.append(p)
    projectiles[:] = vivants


def tirer_laser(cles, joueur):
    cx, cy = config.LARGEUR // 2, config.HAUTEUR // 2
    candidats = []
    aim = 1.0 + config.AUTO_AIM * config.AUTO_AIM_RAYON       # casque : aide à la visée

    b = boss_module.boss
    if b is not None and not b.en_spawn and b.invuln <= 0:
        bx = b.x
        by = get_hauteur_sol(b.x, b.z) - config.BOSS_HAUTEUR_CENTRE
        bz = b.z
        pos = np.array([[bx, by, bz]], dtype=np.float32)
        ex, ey, rz, v = projeter_3d_masse(pos)
        if v[0] and rz[0] < config.PORTEE_TIR:
            rayon_screen = config.BOSS_HAUTEUR_CENTRE * config.FOCALE / max(rz[0], 1.0)
            rayon_screen = min(rayon_screen, 250.0) * aim
            if math.hypot(int(ex[0]) - cx, int(ey[0]) - cy) < rayon_screen:
                if ligne_de_vue(config.cam_x, config.cam_y, config.cam_z, bx, by, bz):
                    candidats.append({
                        "type": "boss", "obj": b,
                        "ex": int(ex[0]), "ey": int(ey[0]), "rz": float(rz[0]),
                    })

    mons = [m for cle in cles for m in monstres_caches[cle]]
    if mons:
        pos = np.array([[m.x, _hauteur_centre(m), m.z] for m in mons], dtype=np.float32)
        ex, ey, rz, v = projeter_3d_masse(pos)
        for i, m in enumerate(mons):
            if not v[i] or rz[i] >= config.PORTEE_TIR:
                continue
            rayon_screen = 40.0 * config.FOCALE / max(rz[i], 1.0)
            rayon_screen = max(rayon_screen, 22.0) * aim
            if math.hypot(int(ex[i]) - cx, int(ey[i]) - cy) < rayon_screen:
                if ligne_de_vue(config.cam_x, config.cam_y, config.cam_z,
                                float(pos[i][0]), float(pos[i][1]), float(pos[i][2])):
                    candidats.append({
                        "type": "monstre", "obj": m,
                        "ex": int(ex[i]), "ey": int(ey[i]), "rz": float(rz[i]),
                    })

    if not candidats:
        return None, False, False

    c = min(candidats, key=lambda x: x["rz"])

    if c["type"] == "boss":
        boss_module.toucher_boss(config.DEGATS_TIR)
        joueur.t_hit = 0.15
        _zap_chaine(c["obj"], cles, joueur, config.DEGATS_TIR)
        return (c["ex"], c["ey"]), True, False

    m = c["obj"]
    fin = (c["ex"], c["ey"])
    _zap_chaine(m, cles, joueur, config.DEGATS_TIR)     # avant la mort : on a besoin de sa position
    mort = _blesser_monstre(m, config.DEGATS_TIR, cles, joueur)
    if not mort:
        joueur.t_hit = 0.15
    return fin, True, mort


# ---------------------------------------------------------------------------
#  Dégâts partagés : tir, zap_chaine (jambières), dash (torse)
# ---------------------------------------------------------------------------
def _blesser_monstre(m, degats, cles, joueur):
    """Inflige des dégâts à un monstre (kill + butin gérés). -> True s'il est mort."""
    m.hp -= degats
    m.hit = 0.12
    if m.hp > 0:
        return False
    for cle in cles:
        if m in monstres_caches[cle]:
            monstres_caches[cle].remove(m)
            break
    joueur.kills += 1
    joueur.t_kill = 0.25
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
    cur = (depart.x, _hauteur_centre(depart) if hasattr(depart, "data") else
           get_hauteur_sol(depart.x, depart.z) - config.BOSS_HAUTEUR_CENTRE, depart.z)
    touches = {id(depart)}
    mons = [m for cle in cles for m in monstres_caches[cle]]
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
            cible = (b.x, get_hauteur_sol(b.x, b.z) - config.BOSS_HAUTEUR_CENTRE, b.z)
        else:
            cible = (meilleur.x, _hauteur_centre(meilleur), meilleur.z)
            _blesser_monstre(meilleur, dmg, cles, joueur)
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
    for m in [m for cle in cles for m in monstres_caches[cle]]:
        if dist(m.x, m.z) < rayon:
            _blesser_monstre(m, degats, cles, joueur)
            nb += 1
    b = _boss_ciblable()
    if b is not None and dist(b.x, b.z) < rayon + 60:
        boss_module.toucher_boss(degats)
        nb += 1
    if nb:
        joueur.t_hit = 0.2
    return nb