# boosts.py
from enum import Enum
import math
import random
import time
import numpy as np

import config


# =============================================================
#  Raretés
# =============================================================
class Rarete(Enum):
    VERT = 0
    BLEU = 1
    JAUNE = 2
    ROUGE = 3


COULEURS_RARETE = {
    Rarete.VERT:  (80, 255, 120),
    Rarete.BLEU:  (80, 180, 255),
    Rarete.JAUNE: (255, 220, 80),
    Rarete.ROUGE: (255, 70, 100),
}


class TypeBoost(Enum):
    MUNITIONS = 0
    SOIN = 1
    VIE_MAX = 2
    VITESSE = 3
    SAUT = 4
    DEGATS = 5
    AUTO_REGEN = 6


class DefBoost:
    __slots__ = ("type", "rarete", "valeur", "nom")
    def __init__(self, type_, rarete, valeur, nom):
        self.type = type_
        self.rarete = rarete
        self.valeur = valeur
        self.nom = nom


DEFS = {
    "MUNITIONS_V":  DefBoost(TypeBoost.MUNITIONS,  Rarete.VERT,  0,
                             f"Munitions +{config.PACK_MUNITIONS}"),
    "SOIN_V":       DefBoost(TypeBoost.SOIN,       Rarete.VERT,  0,
                             f"Soin +{config.PACK_SOIN} PV"),

    "VIE_V":        DefBoost(TypeBoost.VIE_MAX,    Rarete.VERT,
                             config.FORCE_VIE_V,
                             f"Vie max +{config.FORCE_VIE_V*100:.0f}%"),
    "VIE_B":        DefBoost(TypeBoost.VIE_MAX,    Rarete.BLEU,
                             config.FORCE_VIE_B,
                             f"Vie max +{config.FORCE_VIE_B*100:.0f}%"),
    "VIE_J":        DefBoost(TypeBoost.VIE_MAX,    Rarete.JAUNE,
                             config.FORCE_VIE_J,
                             f"Vie max +{config.FORCE_VIE_J*100:.0f}%"),
    "VITESSE_J":    DefBoost(TypeBoost.VITESSE,    Rarete.JAUNE,
                             config.FORCE_VITESSE_J,
                             f"Vitesse +{config.FORCE_VITESSE_J*100:.0f}%"),
    "SAUT_J":       DefBoost(TypeBoost.SAUT,       Rarete.JAUNE,
                             config.FORCE_SAUT_J,
                             f"Saut +{config.FORCE_SAUT_J*100:.0f}%"),
    "DEGATS_J":     DefBoost(TypeBoost.DEGATS,     Rarete.JAUNE,
                             config.FORCE_DEGATS_J,
                             f"Dégâts +{config.FORCE_DEGATS_J*100:.0f}%"),
    "AUTO_REGEN_R": DefBoost(TypeBoost.AUTO_REGEN, Rarete.ROUGE,
                             config.AUTOREGEN_PV, "Auto-régénération"),
}


TABLE_CLASSIQUE = [
    ("MUNITIONS_V", config.POIDS_CS_MUNITIONS),
    ("SOIN_V",      config.POIDS_CS_SOIN),
    ("VIE_V",       config.POIDS_CS_VIE_V),
    ("VIE_B",       config.POIDS_CS_VIE_B),
]

TABLE_PRISMATIQUE = [
    ("VIE_J",        config.POIDS_PS_VIE_J),
    ("VITESSE_J",    config.POIDS_PS_VITESSE_J),
    ("SAUT_J",       config.POIDS_PS_SAUT_J),
    ("DEGATS_J",     config.POIDS_PS_DEGATS_J),
    ("AUTO_REGEN_R", config.POIDS_PS_AUTOREGEN_R),
]


# =============================================================
#  Butin
# =============================================================
class Butin:
    __slots__ = ("x", "z", "def_id", "type", "rarete", "valeur", "nom", "phase",
                 "spawn_time")
    def __init__(self, x, z, def_id):
        self.x = float(x)
        self.z = float(z)
        self.def_id = def_id
        d = DEFS[def_id]
        self.type = d.type
        self.rarete = d.rarete
        self.valeur = d.valeur
        self.nom = d.nom
        self.phase = random.random() * math.tau
        self.spawn_time = time.time()


butins_au_sol = []

def vider_butins():
    butins_au_sol.clear()


# =============================================================
#  Tirage & spawn
# =============================================================
DELAI_GRACE_BUTIN = 0.6


def tirer_butin(type_coffre, x, z, rand_gen=None):
    rng = rand_gen or random
    table = TABLE_PRISMATIQUE if type_coffre == "PRISMATIC_CHEST" else TABLE_CLASSIQUE
    total = sum(w for _, w in table)
    r = rng.random() * total
    acc = 0.0
    for def_id, w in table:
        acc += w
        if r <= acc:
            return Butin(x, z, def_id)
    return Butin(x, z, table[-1][0])


def spawner_butin(butin):
    if butin.type == TypeBoost.MUNITIONS:
        import entity
        entity.pickups.append([butin.x, butin.z, 0, butin.spawn_time])
        return
    if butin.type == TypeBoost.SOIN:
        import entity
        entity.pickups.append([butin.x, butin.z, 1, butin.spawn_time])
        return
    butins_au_sol.append(butin)


# =============================================================
#  Ramassage auto (avec délai de grâce)
# =============================================================
def ramasser_butins(joueur, stats, joueur_x, joueur_z, distance=120):
    now = time.time()
    survivants = []
    for b in butins_au_sol:
        if now - b.spawn_time < DELAI_GRACE_BUTIN:
            survivants.append(b)
            continue
        if math.hypot(b.x - joueur_x, b.z - joueur_z) < distance:
            stats.appliquer(b, joueur)
        else:
            survivants.append(b)
    butins_au_sol[:] = survivants


# =============================================================
#  Modèle pyramide
# =============================================================
def creer_pyramide_inversee(taille=1.0):
    r = taille * 0.5
    base = [(-r, 0.0, -r), (r, 0.0, -r), (r, 0.0, r), (-r, 0.0, r)]
    apex = (0.0, -taille, 0.0)
    segs = []
    for i in range(4):
        segs.append((base[i], base[(i + 1) % 4]))
    for p in base:
        segs.append((p, apex))
    return segs


MODELE_PYRAMIDE = creer_pyramide_inversee(1.0)


# =============================================================
#  Stats du joueur
# =============================================================
class StatsBoostes:
    def __init__(self):
        self.vitesse_bonus = 0.0
        self.saut_bonus = 0.0
        self.degats_bonus = 0.0

        self._base_pv_max = config.JOUEUR_PV_MAX_BASE
        config.JOUEUR_PV_MAX = self._base_pv_max
        self.vie_max_pct = 0.0

        self.auto_regen = False
        self.regen_timer = 0.0

    @property
    def vitesse_mult(self):
        return 1.0 + self.vitesse_bonus

    @property
    def saut_mult(self):
        return 1.0 + self.saut_bonus

    @property
    def degats_mult(self):
        return 1.0 + self.degats_bonus

    def update(self, dt, joueur):
        if self.auto_regen and joueur.pv < config.JOUEUR_PV_MAX:
            self.regen_timer += dt
            if self.regen_timer >= config.AUTOREGEN_DELAI:
                self.regen_timer -= config.AUTOREGEN_DELAI
                joueur.pv = min(config.JOUEUR_PV_MAX,
                                joueur.pv + config.AUTOREGEN_PV)

    def appliquer(self, butin, joueur):
        t = butin.type
        v = butin.valeur

        if t == TypeBoost.VIE_MAX:
            self.vie_max_pct += v
            config.JOUEUR_PV_MAX = int(round(
                self._base_pv_max * (1.0 + self.vie_max_pct)))
            joueur.pv = min(config.JOUEUR_PV_MAX,
                            joueur.pv + int(v * self._base_pv_max))

        elif t == TypeBoost.VITESSE:
            self.vitesse_bonus = min(config.CAP_VITESSE, self.vitesse_bonus + v)

        elif t == TypeBoost.SAUT:
            self.saut_bonus = min(config.CAP_SAUT, self.saut_bonus + v)

        elif t == TypeBoost.DEGATS:
            self.degats_bonus = min(config.CAP_DEGATS, self.degats_bonus + v)

        elif t == TypeBoost.AUTO_REGEN:
            self.auto_regen = True
            self.regen_timer = 0.0

        elif t == TypeBoost.SOIN:
            joueur.soigner(config.PACK_SOIN)

        elif t == TypeBoost.MUNITIONS:
            joueur.ajouter_munitions(config.PACK_MUNITIONS)