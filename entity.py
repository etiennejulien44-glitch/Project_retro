# entity.py  --  joueur, ennemis (IA), projectiles, butin, tir
import math
import random
import time
import numpy as np
import config
from terrain import get_hauteur_sol, monstres_caches
from renderer import projeter_3d_masse

projectiles = []
pickups = []       # [x, z, type, spawn_time]   type 0=mun, 1=soin

DELAI_RAMASSAGE = 0.6   # secondes avant qu'un pickup puisse être ramassé


# ---------------------------------------------------------------------------
# Joueur
# ---------------------------------------------------------------------------
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
        self.pv -= n
        self.flash_degats = 0.35
        if self.pv <= 0:
            self.pv = 0
            self.mort = True

    def soigner(self, n):
        self.pv = min(config.JOUEUR_PV_MAX, self.pv + n)

    def ajouter_munitions(self, n):
        self.reserve = min(config.MUNITIONS_RESERVE_MAX, self.reserve + n)

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


# ---------------------------------------------------------------------------
# Ligne de vue
# ---------------------------------------------------------------------------
def ligne_de_vue(x0, y0, z0, x1, y1, z1, n=14):
    t = np.linspace(0.05, 0.95, n)
    xs = x0 + (x1 - x0) * t
    zs = z0 + (z1 - z0) * t
    ys = y0 + (y1 - y0) * t
    sol = get_hauteur_sol(xs, zs)
    return not np.any(ys > sol - 3)


# ---------------------------------------------------------------------------
# Butin (drops de monstres)
# ---------------------------------------------------------------------------
def deposer_butin(x, z):
    r = random.random()
    t = time.time()
    if r < config.DROP_MUNITIONS:
        pickups.append([x, z, 0, t])
    elif r < config.DROP_MUNITIONS + config.DROP_SOIN:
        pickups.append([x, z, 1, t])
    if len(pickups) > 80:
        pickups.pop(0)


def mettre_a_jour_pickups(joueur):
    if joueur.mort:
        return
    now = time.time()
    restants = []
    for p in pickups:
        if now - p[3] < DELAI_RAMASSAGE:
            restants.append(p)      # période de grâce (visibilité)
            continue
        proche = math.hypot(p[0] - config.cam_x, p[1] - config.cam_z) < config.RAYON_RAMASSAGE
        if proche and p[2] == 0:
            joueur.ajouter_munitions(config.PACK_MUNITIONS)
            joueur.dire(f"+{config.PACK_MUNITIONS} MUNITIONS")
        elif proche and p[2] == 1 and joueur.pv < config.JOUEUR_PV_MAX:
            joueur.soigner(config.PACK_SOIN)
            joueur.dire(f"+{config.PACK_SOIN} PV")
        else:
            restants.append(p)
    pickups[:] = restants


# ---------------------------------------------------------------------------
# IA ennemis
# ---------------------------------------------------------------------------
def _hauteur_centre(m):
    return get_hauteur_sol(m.x, m.z) + (-15 if m.tipo == 0 else -65)


def mettre_a_jour_monstres(dt, cles, joueur, temps):
    cx, cz = config.cam_x, config.cam_z
    for cle in cles:
        for m in monstres_caches[cle]:
            m.hit = max(0.0, m.hit - dt)
            dx, dz = cx - m.x, cz - m.z
            d = math.hypot(dx, dz)

            if m.tipo == 0:
                if d >= config.ARAIGNEE_AGGRO:
                    continue
                if d > config.ARAIGNEE_PORTEE:
                    m.x += dx / d * config.ARAIGNEE_VITESSE * dt
                    m.z += dz / d * config.ARAIGNEE_VITESSE * dt
                    m.cd = max(m.cd, 0.4)
                else:
                    m.cd -= dt
                    if m.cd <= 0:
                        joueur.prendre_degats(config.ARAIGNEE_DEGATS)
                        m.cd = config.ARAIGNEE_COOLDOWN
            else:
                if d >= config.DRONE_AGGRO or d < 1e-6:
                    continue
                v = config.DRONE_VITESSE * dt
                if d > config.DRONE_DIST_PREF + 80:
                    m.x += dx / d * v
                    m.z += dz / d * v
                elif d < config.DRONE_DIST_PREF - 150:
                    m.x -= dx / d * v
                    m.z -= dz / d * v
                lat = math.sin(temps * 0.8 + m.phase) * v * 0.7
                m.x += -dz / d * lat
                m.z += dx / d * lat

                m.cd -= dt
                if m.cd <= 0 and d < config.DRONE_PORTEE_TIR and not joueur.mort:
                    _tirer_projectile(m)
                    m.cd = config.DRONE_COOLDOWN + random.random() * 0.8


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
        if p[6] <= 0 or p[1] > get_hauteur_sol(p[0], p[2]):
            continue
        dx, dy, dz = p[0] - config.cam_x, p[1] - config.cam_y, p[2] - config.cam_z
        if dx * dx + dy * dy + dz * dz < r2:
            joueur.prendre_degats(config.PROJECTILE_DEGATS)
            continue
        vivants.append(p)
    projectiles[:] = vivants


# ---------------------------------------------------------------------------
# Tir joueur
# ---------------------------------------------------------------------------
def tirer_laser(cles, joueur):
    mons = [m for cle in cles for m in monstres_caches[cle]]
    if not mons:
        return None, False, False

    pos = np.array([[m.x, _hauteur_centre(m), m.z] for m in mons], dtype=np.float32)
    ex, ey, rz, v = projeter_3d_masse(pos)
    cx, cy = config.LARGEUR // 2, config.HAUTEUR // 2
    dist = np.hypot(ex - cx, ey - cy)
    rayon = np.maximum(22.0, 30.0 * config.FOCALE / np.maximum(rz, 1.0))
    candidats = np.nonzero(v & (dist < rayon) & (rz < config.PORTEE_TIR))[0]

    for i in sorted(candidats.tolist(), key=lambda k: rz[k]):
        m = mons[i]
        if not ligne_de_vue(config.cam_x, config.cam_y, config.cam_z,
                            float(pos[i][0]), float(pos[i][1]), float(pos[i][2])):
            continue
        m.hp -= config.DEGATS_TIR
        m.hit = 0.12
        fin = (int(ex[i]), int(ey[i]))
        if m.hp <= 0:
            for cle in cles:
                if m in monstres_caches[cle]:
                    monstres_caches[cle].remove(m)
                    break
            joueur.kills += 1
            joueur.t_kill = 0.25
            deposer_butin(m.x, m.z)
            return fin, True, True
        joueur.t_hit = 0.15
        return fin, True, False
    return None, False, False