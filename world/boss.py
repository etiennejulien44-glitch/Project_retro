# world/boss.py  --  Boss : paliers de SCORE, Spider Boss, Cube rotatif, Icosaèdre
#   data/boss.py : paliers + définitions.   Un boss = une classe avec maj() / segments_monde() / centre().
import math
import random
import numpy as np
from data import config
from data import boss as boss_def
from data.modeles import SPIDER_BOSS, modele_cube, modele_icosaedre, MODELE_SATELLITE
from engine import effets
from engine import geometrie as G
from .terrain import get_hauteur_sol
from . import balistique

boss = None
projectiles_boss = []     # [x, y, z, vx, vy, vz, duree, degats]
ondes_boss = []           # ondes néon au sol (objets Onde)
bosses_vaincus = 0
index_palier = 0
prochain_seuil = boss_def.palier(0)[0]       # score à atteindre pour le prochain boss
prochain_type = boss_def.palier(0)[1]
boss_final_lance = False     # le boss final apparait en atteignant la dernière couche
run_gagnee = False           # True quand le boss final est vaincu -> fin de run

_SPIDER_P1, _SPIDER_P2 = G.aplatir_modele(SPIDER_BOSS, config.BOSS_ECHELLE_MODELE)
_SAT_P1, _SAT_P2 = G.aplatir_modele(MODELE_SATELLITE, 1.0)


# ===========================================================================
#  Base commune
# ===========================================================================
class BossBase:
    nom = "BOSS"
    final = False

    def __init__(self, x, z, niveau):
        self.x, self.z, self.niveau = x, z, niveau
        self.hit = 0.0
        self.t_spawn = config.BOSS_SPAWN_ANIM_DUREE
        self.en_spawn = True
        self.invuln = config.BOSS_SPAWN_ANIM_DUREE
        self.etat = "poursuite"
        self.hauteur_centre = config.BOSS_HAUTEUR_CENTRE
        self.rayon_visee = config.BOSS_HAUTEUR_CENTRE
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

    def facteur_degats(self):
        return 1.0

    def centre(self):
        """Point de visée (monde)."""
        return (self.x, float(get_hauteur_sol(self.x, self.z)) - self.hauteur_centre, self.z)

    def couleur(self, temps):
        if self.en_spawn:
            puls = 0.5 + 0.5 * math.sin(temps * 15)
            return (int(255 * puls), int(80 * puls), int(80 * puls))
        puls = 0.6 + 0.4 * math.sin(temps * 8)
        frac = self.hp / self.hp_max if self.hp_max > 0 else 1.0
        intensite = 0.5 + 0.5 * (1 - frac)
        return (int(255 * intensite), int(60 * puls), int(60 * puls))

    def facteurs(self):
        mult = lambda base: base ** self.niveau
        return (mult(config.BOSS_PV_MULT), mult(config.BOSS_VITESSE_MULT), mult(config.BOSS_DEGATS_MULT))


# ===========================================================================
#  Spider Boss (inchangé, conservé dans les paliers)
# ===========================================================================
class SpiderBoss(BossBase):
    nom = "SPIDER BOSS"

    def __init__(self, x, z, niveau):
        super().__init__(x, z, niveau)
        self.final = False
        mult_pv, mult_vit, mult_deg = self.facteurs()
        self.hp_max = int(config.BOSS_PV * mult_pv)
        self.hp = self.hp_max
        self.vitesse = config.BOSS_VITESSE * mult_vit
        self.degats_contact = config.BOSS_DEGATS_CONTACT * mult_deg
        self.degats_aoe = config.BOSS_SAUT_DEGATS_AOE * mult_deg
        self.degats_proj = config.BOSS_PROJECTILE_DEGATS * mult_deg
        self.cd_charge, self.cd_saut, self.cd_rafale, self.cd_contact = 2.0, 3.0, 2.5, 0.0
        self.etat_timer = 0.0
        self.charge_dir = (0.0, 0.0)
        self.saut_cible = (0.0, 0.0)

    def segments_monde(self, temps):
        y = get_hauteur_sol(self.x, self.z) + config.BOSS_OFFSET_MODELE + self.saut_hauteur_courante
        if self.etat == "charge":
            yaw = math.atan2(self.charge_dir[0], self.charge_dir[1])
        else:
            dx, dz = config.cam_x - self.x, config.cam_z - self.z
            yaw = math.atan2(dx, dz) if (dx != 0 or dz != 0) else 0.0
        base = np.array([self.x, y, self.z], dtype=np.float32)
        P1, P2 = G.tourner_y(_SPIDER_P1, yaw) + base, G.tourner_y(_SPIDER_P2, yaw) + base
        return P1, P2, [self.couleur(temps)] * len(P1)

    def maj(self, dt, joueur, temps):
        b = self
        dx, dz = config.cam_x - b.x, config.cam_z - b.z
        d = math.hypot(dx, dz) or 1.0
        b.cd_charge = max(0.0, b.cd_charge - dt)
        b.cd_saut = max(0.0, b.cd_saut - dt)
        b.cd_rafale = max(0.0, b.cd_rafale - dt)
        b.cd_contact = max(0.0, b.cd_contact - dt)
        phase = b.phase

        if b.etat == "poursuite":
            if d > config.BOSS_PORTEE_CONTACT:
                b.x += dx / d * b.vitesse * dt
                b.z += dz / d * b.vitesse * dt
            if b.cd_charge <= 0:
                b.etat, b.etat_timer = "charge", config.BOSS_CHARGE_DUREE
                b.charge_dir = (dx / d, dz / d)
                b.cd_charge = config.BOSS_COOLDOWN_CHARGE
            elif phase >= 2 and b.cd_saut <= 0:
                b.etat, b.etat_timer = "saut", config.BOSS_SAUT_DUREE
                b.saut_cible = (config.cam_x, config.cam_z)
                b.cd_saut = config.BOSS_COOLDOWN_SAUT
            elif phase >= 3 and b.cd_rafale <= 0:
                b.etat, b.etat_timer = "rafale", 0.3
                b.cd_rafale = config.BOSS_COOLDOWN_RAFALE
            elif d < config.BOSS_PORTEE_CONTACT and b.cd_contact <= 0:
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
            tx, tz = b.saut_cible
            b.x += (tx - b.x) * dt * 3
            b.z += (tz - b.z) * dt * 3
            b.saut_hauteur_courante = -4.0 * config.BOSS_SAUT_HAUTEUR * prog * (1.0 - prog)
            if b.etat_timer <= 0:
                b.x, b.z = b.saut_cible
                b.saut_hauteur_courante = 0.0
                effets.onde(b.x, b.z, amp=config.ONDE_MORT_AMP, vitesse=520.0, longueur=360.0, duree=1.0)
                if math.hypot(config.cam_x - b.x, config.cam_z - b.z) < config.BOSS_SAUT_RAYON_AOE:
                    joueur.prendre_degats(b.degats_aoe)
                b.etat = "poursuite"

        elif b.etat == "rafale":
            b.etat_timer -= dt
            if b.etat_timer <= 0:
                _tirer_rafale(b, dx, dz)
                b.etat = "poursuite"


def _tirer_rafale(b, dx, dz):
    base_ang = math.atan2(dz, dx)
    n = config.BOSS_RAFALE_NB_PROJ
    spread = math.radians(config.BOSS_RAFALE_ANGLE)
    y = get_hauteur_sol(b.x, b.z) + config.BOSS_OFFSET_MODELE
    for i in range(n):
        a = base_ang if n <= 1 else base_ang - spread / 2 + spread * i / (n - 1)
        projectiles_boss.append([b.x, y, b.z, math.cos(a) * config.BOSS_PROJECTILE_VITESSE, 0.0,
                                 math.sin(a) * config.BOSS_PROJECTILE_VITESSE,
                                 config.BOSS_PROJECTILE_VIE, b.degats_proj])


# ===========================================================================
#  Boss géométriques (Cube rotatif / Icosaèdre) : ondes néons + tourelles satellites
# ===========================================================================
class Onde:
    """Anneau d'énergie qui s'étend depuis le boss. Le joueur l'évite en SAUTANT par-dessus."""
    __slots__ = ("x", "z", "r", "v", "rmax", "degats", "touche", "fx", "couleur")

    def __init__(self, x, z, r0, v, rmax, degats, couleur):
        self.x, self.z, self.r, self.v, self.rmax = x, z, r0, v, rmax
        self.degats, self.touche, self.fx, self.couleur = degats, False, False, couleur


class Satellite:
    __slots__ = ("angle", "hp", "cd", "hit", "deploy", "x", "y", "z")

    def __init__(self, angle, hp, cd):
        self.angle, self.hp, self.cd, self.hit, self.deploy = angle, hp, cd, 0.0, 0.0
        self.x = self.y = self.z = 0.0


class BossGeo(BossBase):
    def __init__(self, x, z, niveau, cle):
        super().__init__(x, z, niveau)
        d = self.d = boss_def.BOSS_GEO[cle]
        self.cle, self.nom = cle, d["nom"]
        mult_pv, mult_vit, mult_deg = self.facteurs()
        self.hp_max = int(d["pv"] * mult_pv)
        self.hp = self.hp_max
        self.vitesse = d["vitesse"] * mult_vit
        self.degats_contact = d["degats_contact"] * mult_deg
        self.degats_onde = d["onde_degats"] * mult_deg
        self.degats_proj = config.BOSS_PROJECTILE_DEGATS * mult_deg
        self.hauteur_centre, self.rayon_visee = d["hauteur_vol"], d["rayon_visee"]
        self.couleur_base = d["couleur"]
        self.angle = 0.0
        self.t_anim = 0.0
        self.cd_onde = 2.0
        self.cd_sat = 1.5
        self.cd_contact = 0.0
        self.satellites = []
        gen = modele_cube if d["modele"] == "cube" else modele_icosaedre
        self._ext = G.aplatir_modele(gen(d["rayon"]))
        self._int = G.aplatir_modele(gen(d["rayon"] * 0.45))          # noyau qui tourne en sens inverse
        self.etat = "flotte"

    # -- aide ----------------------------------------------------------------
    def facteur_degats(self):
        if any(s.hp > 0 for s in self.satellites):
            return self.d.get("reduction_satellites", 1.0)
        return 1.0

    def centre(self):
        y = float(get_hauteur_sol(self.x, self.z)) - self.hauteur_centre + 10.0 * math.sin(self.t_anim * 1.5)
        return (self.x, y, self.z)

    def couleur(self, temps):
        base = self.couleur_base
        if self.hit > 0:
            return (255, 255, 255)
        k = 0.65 + 0.35 * math.sin(temps * 6)
        return (int(base[0] * k), int(base[1] * k), int(base[2] * k))

    def segments_monde(self, temps):
        cx, cy, cz = self.centre()
        k = 1.0
        if self.en_spawn:
            k = 0.25 + 0.75 * (1.0 - max(0.0, self.t_spawn) / config.BOSS_SPAWN_ANIM_DUREE)
        R1 = G.matrice_xy(self.angle * 0.6, self.angle)
        R2 = G.matrice_xy(-self.angle * 0.8, -self.angle * 1.3)
        base = np.array([cx, cy, cz], dtype=np.float32)
        E1, E2 = self._ext
        I1, I2 = self._int
        P1 = np.concatenate((E1 @ R1.T * k, I1 @ R2.T * k)) + base
        P2 = np.concatenate((E2 @ R1.T * k, I2 @ R2.T * k)) + base
        c = self.couleur(temps)
        cn = (255, 255, 255) if self.hit > 0 else (min(255, c[0] + 80), min(255, c[1] + 80), min(255, c[2] + 80))
        return P1, P2, [c] * len(E1) + [cn] * len(I1)

    def segments_satellites(self, temps):
        """-> liste de (satellite, P1, P2, couleur) en coordonnées monde."""
        res = []
        for s in self.satellites:
            if s.hp <= 0:
                continue
            c = (255, 255, 255) if s.hit > 0 else (255, 160 if s.deploy >= 1 else 80, 60)
            R = G.matrice_xy(temps * 1.7 + s.angle, temps * 2.3)
            base = np.array([s.x, s.y, s.z], dtype=np.float32)
            res.append((s, _SAT_P1 @ R.T + base, _SAT_P2 @ R.T + base, c))
        return res

    # -- IA --------------------------------------------------------------------
    def maj(self, dt, joueur, temps):
        d = self.d
        self.t_anim += dt
        ph = self.phase
        self.angle += d["rot_vitesse"][ph - 1] * dt
        self.cd_contact = max(0.0, self.cd_contact - dt)
        dx, dz = config.cam_x - self.x, config.cam_z - self.z
        dist = math.hypot(dx, dz) or 1.0
        pref = d["dist_pref"]
        if dist > pref + 120:                                   # il garde ses distances : flotte autour du joueur
            self.x += dx / dist * self.vitesse * dt
            self.z += dz / dist * self.vitesse * dt
        elif dist < pref - 160:
            self.x -= dx / dist * self.vitesse * 0.7 * dt
            self.z -= dz / dist * self.vitesse * 0.7 * dt
        if dist < self.rayon_visee + 40 and self.cd_contact <= 0:
            joueur.prendre_degats(self.degats_contact)
            self.cd_contact = config.BOSS_COOLDOWN_CONTACT
        for nom in d["patterns"]:
            _PATTERNS[nom](self, dt, joueur, ph)
        for s in self.satellites:                               # les satellites vivent même sans pattern actif
            s.hit = max(0.0, s.hit - dt)


# ---- patterns (registre) : AJOUTER UN PATTERN = une fonction @pattern("nom") ---------------
_PATTERNS = {}


def pattern(nom):
    def deco(f):
        _PATTERNS[nom] = f
        return f
    return deco


@pattern("ondes")
def _pat_ondes(b, dt, joueur, ph):
    """Vagues d'anneaux néons qui s'étendent au sol (on saute par-dessus)."""
    d = b.d
    n = d["ondes_par_phase"][ph - 1]
    if n <= 0:
        return
    b.cd_onde -= dt
    if b.cd_onde <= 0:
        for k in range(n):                                      # anneaux décalés : rayon de départ négatif = retard
            ondes_boss.append(Onde(b.x, b.z, -k * d["onde_espacement"], d["onde_vitesse"],
                                   d["onde_rayon_max"], b.degats_onde, b.couleur_base))
        b.cd_onde = d["cd_onde"][ph - 1]


@pattern("satellites")
def _pat_satellites(b, dt, joueur, ph):
    """Déploie des tourelles satellites en orbite. Tant qu'il en reste, le boss prend très peu de dégâts."""
    d = b.d
    cx, cy, cz = b.centre()
    for s in b.satellites:
        s.angle += d["sat_vitesse_orbite"] * dt
        s.deploy = min(1.0, s.deploy + dt / 1.2)
        r = d["sat_orbite"] * (1.0 - (1.0 - s.deploy) ** 3)
        s.x = cx + math.cos(s.angle) * r
        s.z = cz + math.sin(s.angle) * r
        s.y = cy + math.sin(s.angle * 2.0 + 1.0) * 25.0
        s.cd -= dt
        if s.cd <= 0 and s.deploy >= 1.0 and not joueur.mort:
            dx, dy, dz = config.cam_x - s.x, config.cam_y - s.y, config.cam_z - s.z
            n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            v = config.BOSS_PROJECTILE_VITESSE * 0.9
            projectiles_boss.append([s.x, s.y, s.z, dx / n * v, dy / n * v, dz / n * v,
                                     config.BOSS_PROJECTILE_VIE, b.degats_proj * d["sat_degats_mult"]])
            s.cd = d["sat_cd_tir"] * (0.8 + random.random() * 0.6)
    b.satellites = [s for s in b.satellites if s.hp > 0]
    if not b.satellites:
        b.cd_sat -= dt
        if b.cd_sat <= 0:
            nb = d["nb_satellites"][ph - 1]
            for k in range(nb):
                b.satellites.append(Satellite(2 * math.pi * k / nb, d["sat_pv"], 1.0 + random.random()))
            b.cd_sat = d["cd_deploiement"]
            effets.onde(b.x, b.z, amp=config.ONDE_MORT_AMP * 0.6, vitesse=500.0, longueur=340.0, duree=0.9)


# ===========================================================================
#  API du module
# ===========================================================================
def prochain_palier():
    return prochain_seuil, prochain_type


def spawner_boss(joueur_x, joueur_z, cle="araignee"):
    global boss
    base_yaw = math.radians(config.yaw)
    a = base_yaw + random.uniform(-math.pi / 4, math.pi / 4)
    x = joueur_x + math.sin(a) * config.BOSS_SPAWN_DISTANCE
    z = joueur_z + math.cos(a) * config.BOSS_SPAWN_DISTANCE
    if cle in boss_def.BOSS_GEO:
        boss = BossGeo(x, z, bosses_vaincus, cle)
    else:
        boss = SpiderBoss(x, z, bosses_vaincus)
    effets.onde(x, z, amp=config.ONDE_MORT_AMP, vitesse=600.0, longueur=400.0, duree=1.4)
    return boss


def lancer_boss_final(joueur_x, joueur_z):
    """Boss de fin de run (Spider Boss plus costaud). Appelé 1 seule fois."""
    global boss_final_lance
    if boss_final_lance:
        return False
    boss_final_lance = True
    b = spawner_boss(joueur_x, joueur_z, "araignee")
    b.final = True
    b.nom = "BOSS FINAL"
    b.hp_max = b.hp = int(b.hp_max * config.BOSS_FINAL_PV_MULT)
    return True


def toucher_boss(degats):
    """Appelé par le système de tir du joueur."""
    if boss is None or boss.invuln > 0:
        return False
    boss.hp -= degats * boss.facteur_degats()
    boss.hit = 0.15
    return True


def satellites_ciblables():
    b = boss
    if b is None or not isinstance(b, BossGeo) or b.en_spawn:
        return ()
    return [s for s in b.satellites if s.hp > 0 and s.deploy >= 1.0]


def toucher_satellite(s, degats, joueur):
    s.hp -= degats
    s.hit = 0.12
    effets.etincelles((s.x, s.y, s.z), (255, 30, 30), n=5)
    if s.hp <= 0:
        t = effets.temps
        R = G.matrice_xy(t * 1.7 + s.angle, t * 2.3)
        base = np.array([s.x, s.y, s.z], dtype=np.float32)
        effets.eclater(_SAT_P1 @ R.T + base, _SAT_P2 @ R.T + base, (255, 160, 60),
                       float(get_hauteur_sol(s.x, s.z)), morceaux=2)
        joueur.score += config.SATELLITE_SCORE
    return True


def _tuer_boss(joueur):
    global boss, bosses_vaincus, index_palier, prochain_seuil, prochain_type, run_gagnee
    from world import butin
    b = boss
    if b is None:
        return
    P1, P2, _ = b.segments_monde(effets.temps)
    effets.eclater(P1, P2, getattr(b, "couleur_base", (255, 60, 60)), float(get_hauteur_sol(b.x, b.z)),
                   force=1.4, morceaux=3)
    effets.onde(b.x, b.z, amp=config.ONDE_MORT_AMP * 1.5, vitesse=600.0, longueur=420.0, duree=1.4)
    bosses_vaincus += 1
    joueur.score += config.BOSS_SCORE_BONUS
    index_palier += 1
    seuil, prochain_type = boss_def.palier(index_palier)
    prochain_seuil = max(seuil, joueur.score + boss_def.ECART_MIN)
    for _ in range(config.BOSS_NB_DROPS):           # 2 boosts uniformes (indépendant des tables pondérées)
        def_id = random.choice(config.BOSS_DROPS_POOL)
        butin.spawner_butin(butin.Butin(b.x + random.uniform(-80, 80), b.z + random.uniform(-80, 80), def_id))
    if b.final:
        run_gagnee = True
    joueur.dire("BOSS FINAL VAINCU !" if b.final else "BOSS VAINCU !")
    boss = None


def _maj_ondes(dt, joueur):
    if not ondes_boss:
        return
    sol_j = None
    for o in ondes_boss:
        o.r += o.v * dt
        if o.r >= 0 and not o.fx:                       # l'anneau naît : la grille ondule en même temps
            effets.onde(o.x, o.z, amp=config.ONDE_MORT_AMP, vitesse=o.v, longueur=300.0, duree=min(2.5, o.rmax / o.v))
            o.fx = True
        if o.r > 0 and not o.touche and not joueur.mort:
            if abs(math.hypot(config.cam_x - o.x, config.cam_z - o.z) - o.r) < config.BOSS_ONDE_EPAISSEUR:
                if sol_j is None:
                    sol_j = float(get_hauteur_sol(config.cam_x, config.cam_z)) - 30.0     # cam_y quand on est au sol
                if config.cam_y > sol_j - config.BOSS_ONDE_SAUT_MIN:                      # pas assez haut : touché
                    joueur.prendre_degats(o.degats)
                o.touche = True
    ondes_boss[:] = [o for o in ondes_boss if o.r < o.rmax]


def mettre_a_jour_boss(dt, joueur, temps):
    global boss
    _maj_ondes(dt, joueur)

    if boss is None:                                    # spawn auto à un PALIER DE SCORE
        if joueur.score >= prochain_seuil:
            spawner_boss(config.cam_x, config.cam_z, prochain_type)
        return

    b = boss
    b.hit = max(0.0, b.hit - dt)

    if b.en_spawn:                                      # anim de spawn (boss immobile, invulnérable)
        b.t_spawn -= dt
        b.invuln = max(0.0, b.invuln - dt)
        if isinstance(b, BossGeo):
            b.angle += 2.0 * dt
            b.t_anim += dt
        if b.t_spawn <= 0:
            b.en_spawn = False
            b.invuln = 0.0
        return

    b.maj(dt, joueur, temps)

    if boss is not None and boss.hp <= 0:
        _tuer_boss(joueur)


def mettre_a_jour_projectiles_boss(dt, joueur):
    balistique.avancer(projectiles_boss, dt, joueur, config.PROJECTILE_RAYON ** 2)


def reinitialiser_boss():
    global boss, bosses_vaincus, index_palier, prochain_seuil, prochain_type, boss_final_lance, run_gagnee
    boss_final_lance = False
    run_gagnee = False
    boss = None
    bosses_vaincus = 0
    index_palier = 0
    prochain_seuil, prochain_type = boss_def.palier(0)
    projectiles_boss.clear()
    ondes_boss.clear()
