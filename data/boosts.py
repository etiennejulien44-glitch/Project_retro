# boosts.py
# ============================================================================
#  AJOUTER UN BOOST / ITEM = ajouter UNE entrée dans BOOSTS (plus bas). Rien d'autre.
#
#   nom, rarete   : affichage
#   effet         : "stat" | "vie_max" | "auto_regen" | "munitions" | "soin" | "arme" (+ arme="<id>")
#                   (nouveau type d'effet = une petite fonction dans EFFETS)
#   valeur        : intensité (+0.15 = +15% pour "stat")
#   stat, cap, label, hud : pour effet "stat" (nom de la stat, plafond, texte, couleur HUD)
#   tables        : {"classique": poids, "prismatique": poids, ...} -> dans quels coffres il tombe
#   pickup        : (optionnel) objet tournant au sol : modele, echelle, couleur, drop (chance
#                   de drop par monstre tué). Sans "pickup" -> pyramide de la couleur de rareté.
#  Lire une stat côté jeu : stats.mult("vitesse") -> 1.0 + bonus cumulé.
# ============================================================================
from enum import Enum
import math
import random
import time
import numpy as np

from . import config
from .modeles import MODELE_MUNITIONS, MODELE_SOINS
from .coffres import COFFRES
from . import armes


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


# =============================================================
#  Registre des boosts
# =============================================================
BOOSTS = {
    "MUNITIONS_V": dict(
        nom=f"Munitions +{config.PACK_MUNITIONS}", rarete=Rarete.VERT, effet="munitions",
        valeur=config.PACK_MUNITIONS, tables={"classique": config.POIDS_CS_MUNITIONS},
        pickup=dict(modele=MODELE_MUNITIONS, echelle=3.0, couleur=(60, 240, 255),
                    drop=config.DROP_MUNITIONS)),
    "SOIN_V": dict(
        nom=f"Soin +{config.PACK_SOIN} PV", rarete=Rarete.VERT, effet="soin",
        valeur=config.PACK_SOIN, tables={"classique": config.POIDS_CS_SOIN},
        pickup=dict(modele=MODELE_SOINS, echelle=3.0, couleur=(120, 255, 150),
                    drop=config.DROP_SOIN)),
    "VIE_V": dict(nom=f"Vie max +{config.FORCE_VIE_V*100:.0f}%", rarete=Rarete.VERT,
                  effet="vie_max", valeur=config.FORCE_VIE_V,
                  tables={"classique": config.POIDS_CS_VIE_V}),
    "VIE_B": dict(nom=f"Vie max +{config.FORCE_VIE_B*100:.0f}%", rarete=Rarete.BLEU,
                  effet="vie_max", valeur=config.FORCE_VIE_B,
                  tables={"classique": config.POIDS_CS_VIE_B}),
    "VIE_J": dict(nom=f"Vie max +{config.FORCE_VIE_J*100:.0f}%", rarete=Rarete.JAUNE,
                  effet="vie_max", valeur=config.FORCE_VIE_J,
                  tables={"prismatique": config.POIDS_PS_VIE_J}),
    "VITESSE_J": dict(nom=f"Vitesse +{config.FORCE_VITESSE_J*100:.0f}%", rarete=Rarete.JAUNE,
                      effet="stat", stat="vitesse", label="VITESSE", hud="CYAN",
                      valeur=config.FORCE_VITESSE_J, cap=config.CAP_VITESSE,
                      tables={"prismatique": config.POIDS_PS_VITESSE_J}),
    "SAUT_J": dict(nom=f"Saut +{config.FORCE_SAUT_J*100:.0f}%", rarete=Rarete.JAUNE,
                   effet="stat", stat="saut", label="SAUT", hud="CYAN",
                   valeur=config.FORCE_SAUT_J, cap=config.CAP_SAUT,
                   tables={"prismatique": config.POIDS_PS_SAUT_J}),
    "DEGATS_J": dict(nom=f"Dégâts +{config.FORCE_DEGATS_J*100:.0f}%", rarete=Rarete.JAUNE,
                     effet="stat", stat="degats", label="DEGATS", hud="ROSE",
                     valeur=config.FORCE_DEGATS_J, cap=config.CAP_DEGATS,
                     tables={"prismatique": config.POIDS_PS_DEGATS_J}),
    "AUTO_REGEN_R": dict(nom="Auto-régénération", rarete=Rarete.ROUGE, effet="auto_regen",
                         valeur=config.AUTOREGEN_PV,
                         tables={"prismatique": config.POIDS_PS_AUTOREGEN_R}),
    "ARME_PLASMA": dict(nom="Plasma Rifle", rarete=Rarete.ROUGE, effet="arme", arme="plasma",
                        valeur=0, tables={"prismatique": 6}),
    "ARME_SMG": dict(nom="Pulse SMG", rarete=Rarete.JAUNE, effet="arme", arme="pulse_smg",
                     valeur=0, tables={"classique": 6, "prismatique": 6}),
}

PICKUP_IDS = [k for k, d in BOOSTS.items() if "pickup" in d]   # index = type dans entity.pickups


def table_butin(nom_table):
    """[(id, poids)] de tous les boosts présents dans la table `nom_table`."""
    return [(k, d["tables"][nom_table]) for k, d in BOOSTS.items() if nom_table in d.get("tables", {})]


# =============================================================
#  Butin au sol
# =============================================================
class Butin:
    __slots__ = ("x", "z", "def_id", "type", "rarete", "valeur", "nom",
                 "phase", "spawn_time")
    def __init__(self, x, z, def_id):
        self.x = float(x)
        self.z = float(z)
        self.def_id = def_id
        d = BOOSTS[def_id]
        self.type = d["effet"]
        self.rarete = d["rarete"]
        self.valeur = d["valeur"]
        self.nom = d["nom"]
        self.phase = random.random() * math.tau
        self.spawn_time = time.time()


butins_au_sol = []

def vider_butins():
    butins_au_sol.clear()


# =============================================================
#  Effets (retournent True si appliqué, False si impossible : plein / plafond atteint)
# =============================================================
def _msg(stats, d, texte):
    stats.messages_ramassage.append((texte, COULEURS_RARETE[d["rarete"]]))


def _eff_munitions(stats, joueur, d):
    if joueur.reserve >= config.MUNITIONS_RESERVE_MAX:
        return False
    avant = joueur.reserve
    joueur.ajouter_munitions(d["valeur"])
    _msg(stats, d, f"MUNITIONS {avant} -> {joueur.reserve}")
    return True


def _eff_soin(stats, joueur, d):
    if joueur.pv >= config.JOUEUR_PV_MAX:
        return False
    avant = joueur.pv
    joueur.soigner(d["valeur"])
    _msg(stats, d, f"SOIN {avant} -> {joueur.pv}")
    return True


def _eff_vie_max(stats, joueur, d):
    ancien_max = config.JOUEUR_PV_MAX
    stats.vie_max_pct += d["valeur"]
    config.JOUEUR_PV_MAX = int(round(stats._base_pv_max * (1.0 + stats.vie_max_pct)))
    joueur.pv = min(config.JOUEUR_PV_MAX, joueur.pv + int(d["valeur"] * stats._base_pv_max))
    _msg(stats, d, f"VIE MAX : {ancien_max} -> {config.JOUEUR_PV_MAX}")
    return True


def _eff_stat(stats, joueur, d):
    s = d["stat"]
    avant = stats._bonus.get(s, 0.0)
    if avant >= d["cap"]:
        return False
    stats._bonus[s] = min(d["cap"], avant + d["valeur"])
    gain = int((stats._bonus[s] - avant) * 100)
    _msg(stats, d, f"{d['label']} +{gain}%  (total +{int(stats._bonus[s]*100)}%)")
    return True


def _eff_auto_regen(stats, joueur, d):
    if stats.auto_regen:
        return False
    stats.auto_regen = True
    stats.regen_timer = 0.0
    _msg(stats, d, "AUTO-REGEN ACTIVEE (1 PV / 2 s)")
    return True


def _eff_arme(stats, joueur, d):
    if not armes.donner(d["arme"]):
        return False                    # déjà possédée : reste au sol
    _msg(stats, d, f"ARME : {armes.ARMES[d['arme']]['nom']}  ->  [TAB] inventaire, equip {d['arme']}")
    return True


EFFETS = {"arme": _eff_arme, "munitions": _eff_munitions, "soin": _eff_soin, "vie_max": _eff_vie_max,
          "stat": _eff_stat, "auto_regen": _eff_auto_regen}


def appliquer(def_id, stats, joueur):
    d = BOOSTS[def_id]
    return EFFETS[d["effet"]](stats, joueur, d)


# =============================================================
#  Tirage & spawn
# =============================================================
DELAI_GRACE_BUTIN = 1.5


def tirer_butin(type_coffre, x, z, rand_gen=None):
    rng = rand_gen or random
    table = table_butin(COFFRES[type_coffre]["table"])
    total = sum(w for _, w in table)
    r = rng.random() * total
    acc = 0.0
    for def_id, w in table:
        acc += w
        if r <= acc:
            return Butin(x, z, def_id)
    return Butin(x, z, table[-1][0])


def spawner_butin(butin):
    if butin.def_id in PICKUP_IDS:
        from world import entity
        entity.pickups.append([butin.x, butin.z, PICKUP_IDS.index(butin.def_id), butin.spawn_time])
        return
    butins_au_sol.append(butin)


# =============================================================
#  Ramassage auto (aimant + cap check)
# =============================================================
def ramasser_butins(joueur, stats, joueur_x, joueur_z, dt):
    now = time.time()
    survivants = []
    for b in butins_au_sol:
        if now - b.spawn_time < DELAI_GRACE_BUTIN:
            survivants.append(b)
            continue

        d = math.hypot(b.x - joueur_x, b.z - joueur_z)

        if d < config.RAYON_RAMASSAGE_BUTINS:
            if not appliquer(b.def_id, stats, joueur):
                survivants.append(b)      # plein / plafond : reste au sol
            continue

        if d < config.RAYON_AIMANT_BUTINS:
            step = config.VITESSE_AIMANT_BUTINS * dt
            if step > d:
                step = d
            b.x += (joueur_x - b.x) / d * step
            b.z += (joueur_z - b.z) / d * step

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
        self._bonus = {}                 # stat -> bonus cumulé (ex: "vitesse": 0.3)
        self._base_pv_max = config.JOUEUR_PV_MAX_BASE
        config.JOUEUR_PV_MAX = self._base_pv_max
        self.vie_max_pct = 0.0
        self.auto_regen = False
        self.regen_timer = 0.0
        self.messages_ramassage = []     # [(texte, couleur)]

    def bonus(self, stat):
        return self._bonus.get(stat, 0.0)

    def mult(self, stat):
        return 1.0 + self._bonus.get(stat, 0.0)

    # raccourcis utilisés par main / debug
    vitesse_bonus = property(lambda s: s.bonus("vitesse"))
    saut_bonus = property(lambda s: s.bonus("saut"))
    degats_bonus = property(lambda s: s.bonus("degats"))
    vitesse_mult = property(lambda s: s.mult("vitesse"))
    saut_mult = property(lambda s: s.mult("saut"))
    degats_mult = property(lambda s: s.mult("degats"))

    def update(self, dt, joueur):
        if self.auto_regen and joueur.pv < config.JOUEUR_PV_MAX:
            self.regen_timer += dt
            if self.regen_timer >= config.AUTOREGEN_DELAI:
                self.regen_timer -= config.AUTOREGEN_DELAI
                joueur.pv = min(config.JOUEUR_PV_MAX, joueur.pv + config.AUTOREGEN_PV)

    def appliquer(self, butin, joueur):
        return appliquer(butin.def_id, self, joueur)

    def lignes_hud(self):
        """[(texte, nom_couleur)] des bonus permanents, généré depuis BOOSTS."""
        lignes = []
        if self.vie_max_pct > 0:
            lignes.append((f"VIE MAX +{int(self.vie_max_pct*100)}%", "JAUNE"))
        vus = set()
        for d in BOOSTS.values():
            s = d.get("stat")
            if s and s not in vus:
                vus.add(s)
                if self.bonus(s) > 0:
                    lignes.append((f"{d['label']} +{int(self.bonus(s)*100)}%", d["hud"]))
        if self.auto_regen:
            lignes.append(("REGEN 1 PV/2s", "BLANC"))
        return lignes
