# boss.py  --  Spider Boss : IA, patterns, spawn, mort
import math
import random
import numpy as np
from data import config
from .terrain import get_hauteur_sol


boss = None
projectiles_boss = []     # [x, y, z, vx, vy, vz, duree, degats]
bosses_vaincus = 0
prochain_seuil_kills = config.BOSS_SPAWN_KILLS_1


class SpiderBoss:
    def __init__(self, x, z, niveau):
        self.x = x
        self.z = z
        self.niveau = niveau

        mult_pv  = config.BOSS_PV_MULT      ** niveau
        mult_vit = config.BOSS_VITESSE_MULT ** niveau
        mult_deg = config.BOSS_DEGATS_MULT  ** niveau

        self.hp_max        = int(config.BOSS_PV * mult_pv)
        self.hp            = self.hp_max
        self.vitesse       = config.BOSS_VITESSE * mult_vit
        self.degats_contact = config.BOSS_DEGATS_CONTACT * mult_deg
        self.degats_aoe    = config.BOSS_SAUT_DEGATS_AOE * mult_deg
        self.degats_proj   = config.BOSS_PROJECTILE_DEGATS * mult_deg

        self.hit = 0.0
        self.t_spawn = config.BOSS_SPAWN_ANIM_DUREE
        self.en_spawn = True
        self.invuln = config.BOSS_SPAWN_ANIM_DUREE

        # cooldowns
        self.cd_charge  = 2.0
        self.cd_saut    = 3.0
        self.cd_rafale  = 2.5
        self.cd_contact = 0.0

        # machine d'état
        self.etat = "poursuite"
        self.etat_timer = 0.0
        self.charge_dir = (0.0, 0.0)
        self.saut_cible = (0.0, 0.0)
        self.saut_hauteur_courante = 0.0

    @property
    def phase(self):
        if self.hp_max <= 0:
            return 1
        frac = self.hp / self.hp_max
        if frac > config.BOSS_PHASE_2:
            return 1
        if frac > config.BOSS_PHASE_3:
            return 2
        return 3

    def est_vivant(self):
        return self.hp > 0


def spawner_boss(joueur_x, joueur_z):
    global boss
    base_yaw = math.radians(config.yaw)
    variance = random.uniform(-math.pi / 4, math.pi / 4)
    a = base_yaw + variance
    x = joueur_x + math.sin(a) * config.BOSS_SPAWN_DISTANCE
    z = joueur_z + math.cos(a) * config.BOSS_SPAWN_DISTANCE
    boss = SpiderBoss(x, z, bosses_vaincus)
    return boss


def toucher_boss(degats):
    """Appelé par le système de tir du joueur."""
    if boss is None or boss.invuln > 0:
        return False
    boss.hp -= degats
    boss.hit = 0.15
    return True


def _tuer_boss(joueur):
    global boss, bosses_vaincus, prochain_seuil_kills
    import boosts
    b = boss
    if b is None:
        return
    bosses_vaincus += 1
    prochain_seuil_kills = joueur.kills + config.BOSS_SPAWN_KILLS_INCREMENT
    # Drop 2 boosts uniformes (indépendant des tables pondérées)
    for _ in range(config.BOSS_NB_DROPS):
        def_id = random.choice(config.BOSS_DROPS_POOL)
        butin = boosts.Butin(
            b.x + random.uniform(-80, 80),
            b.z + random.uniform(-80, 80),
            def_id,
        )
        boosts.spawner_butin(butin)
    joueur.dire("BOSS VAINCU !")
    boss = None


def _tirer_rafale(b, dx, dz, d):
    base_ang = math.atan2(dz, dx)
    n = config.BOSS_RAFALE_NB_PROJ
    spread = math.radians(config.BOSS_RAFALE_ANGLE)
    y = get_hauteur_sol(b.x, b.z) + config.BOSS_OFFSET_MODELE
    for i in range(n):
        if n <= 1:
            a = base_ang
        else:
            a = base_ang - spread / 2 + spread * i / (n - 1)
        vx = math.cos(a) * config.BOSS_PROJECTILE_VITESSE
        vz = math.sin(a) * config.BOSS_PROJECTILE_VITESSE
        projectiles_boss.append([
            b.x, y, b.z, vx, 0.0, vz,
            config.BOSS_PROJECTILE_VIE, b.degats_proj,
        ])


def mettre_a_jour_boss(dt, joueur, temps):
    global boss, prochain_seuil_kills

    # Spawn auto
    if boss is None:
        if joueur.kills >= prochain_seuil_kills:
            spawner_boss(config.cam_x, config.cam_z)
        return

    b = boss
    b.hit = max(0.0, b.hit - dt)

    # Anim de spawn (boss immobile, invulnérable)
    if b.en_spawn:
        b.t_spawn -= dt
        b.invuln = max(0.0, b.invuln - dt)
        if b.t_spawn <= 0:
            b.en_spawn = False
            b.invuln = 0.0
        return

    dx = config.cam_x - b.x
    dz = config.cam_z - b.z
    d = math.hypot(dx, dz) or 1.0

    b.cd_charge  = max(0.0, b.cd_charge  - dt)
    b.cd_saut    = max(0.0, b.cd_saut    - dt)
    b.cd_rafale  = max(0.0, b.cd_rafale  - dt)
    b.cd_contact = max(0.0, b.cd_contact - dt)

    phase = b.phase

    if b.etat == "poursuite":
        if d > config.BOSS_PORTEE_CONTACT:
            b.x += dx / d * b.vitesse * dt
            b.z += dz / d * b.vitesse * dt

        if b.cd_charge <= 0:
            b.etat = "charge"
            b.etat_timer = config.BOSS_CHARGE_DUREE
            b.charge_dir = (dx / d, dz / d)
            b.cd_charge = config.BOSS_COOLDOWN_CHARGE
        elif phase >= 2 and b.cd_saut <= 0:
            b.etat = "saut"
            b.etat_timer = config.BOSS_SAUT_DUREE
            b.saut_cible = (config.cam_x, config.cam_z)
            b.cd_saut = config.BOSS_COOLDOWN_SAUT
        elif phase >= 3 and b.cd_rafale <= 0:
            b.etat = "rafale"
            b.etat_timer = 0.3
            b.cd_rafale = config.BOSS_COOLDOWN_RAFALE
        else:
            if d < config.BOSS_PORTEE_CONTACT and b.cd_contact <= 0:
                joueur.prendre_degats(b.degats_contact)
                b.cd_contact = config.BOSS_COOLDOWN_CONTACT

    elif b.etat == "charge":
        v = b.vitesse * config.BOSS_CHARGE_VITESSE_MULT
        b.x += b.charge_dir[0] * v * dt
        b.z += b.charge_dir[1] * v * dt
        b.etat_timer -= dt
        if d < config.BOSS_PORTEE_CONTACT and b.cd_contact <= 0:
            joueur.prendre_degats(b.degats_contact)
            b.cd_contact = 0.8
        if b.etat_timer <= 0:
            b.etat = "poursuite"

    elif b.etat == "saut":
        b.etat_timer -= dt
        prog = 1.0 - max(0.0, b.etat_timer) / config.BOSS_SAUT_DUREE
        # dérive horizontale vers la cible
        tx, tz = b.saut_cible
        b.x += (tx - b.x) * dt * 3
        b.z += (tz - b.z) * dt * 3
        # arc parabolique (Y négatif = plus haut)
        b.saut_hauteur_courante = -4.0 * config.BOSS_SAUT_HAUTEUR * prog * (1.0 - prog)
        if b.etat_timer <= 0:
            b.x, b.z = b.saut_cible
            b.saut_hauteur_courante = 0.0
            d_aoe = math.hypot(config.cam_x - b.x, config.cam_z - b.z)
            if d_aoe < config.BOSS_SAUT_RAYON_AOE:
                joueur.prendre_degats(b.degats_aoe)
            b.etat = "poursuite"

    elif b.etat == "rafale":
        b.etat_timer -= dt
        if b.etat_timer <= 0:
            _tirer_rafale(b, dx, dz, d)
            b.etat = "poursuite"

    # Mort
    if boss is not None and boss.hp <= 0:
        _tuer_boss(joueur)


def mettre_a_jour_projectiles_boss(dt, joueur):
    r2 = config.PROJECTILE_RAYON ** 2
    vivants = []
    for p in projectiles_boss:
        p[0] += p[3] * dt
        p[1] += p[4] * dt
        p[2] += p[5] * dt
        p[6] -= dt
        if p[6] <= 0 or p[1] > get_hauteur_sol(p[0], p[2]):
            continue
        dx, dy, dz = p[0] - config.cam_x, p[1] - config.cam_y, p[2] - config.cam_z
        if dx * dx + dy * dy + dz * dz < r2:
            joueur.prendre_degats(p[7])
            continue
        vivants.append(p)
    projectiles_boss[:] = vivants


def reinitialiser_boss():
    global boss, bosses_vaincus, prochain_seuil_kills
    boss = None
    bosses_vaincus = 0
    prochain_seuil_kills = config.BOSS_SPAWN_KILLS_1
    projectiles_boss.clear()