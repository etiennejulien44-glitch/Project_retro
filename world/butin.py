# world/butin.py -- butins au sol, application des effets de boosts, stats cumulées du joueur
#   (les DÉFINITIONS sont dans data/boosts.py)
import math
import random
import time

from data import config
from data.boosts import BOOSTS, PICKUP_IDS, COULEURS_RARETE, DELAI_GRACE_BUTIN, table_butin
from data.coffres import COFFRES
from data.raretes import RARETES
from world import inventaire


# =============================================================
#  Butin au sol
# =============================================================
class Butin:
    __slots__ = ("x", "z", "def_id", "type", "rarete", "valeur", "nom",
                 "phase", "spawn_time", "couleur", "instance", "notifie")
    def __init__(self, x, z, def_id, biais_rarete=None):
        self.x = float(x)
        self.z = float(z)
        self.def_id = def_id
        d = BOOSTS[def_id]
        self.type = d["effet"]
        self.rarete = d["rarete"]
        self.valeur = d["valeur"]
        self.nom = d["nom"]
        self.couleur = COULEURS_RARETE[d["rarete"]]
        self.instance = None          # équipement : exemplaire déjà tiré (rareté + stats)
        self.notifie = False          # message "trop lourd" déjà affiché
        if d["effet"] == "equipement":
            self.instance = inventaire.generer_instance_item(d["item"], biais=biais_rarete)
            self.nom = self.instance["nom"]
            self.couleur = RARETES[self.instance["rarete"]]["couleur"]
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


def _eff_munitions(stats, joueur, d, butin=None):
    if joueur.reserve >= config.MUNITIONS_RESERVE_MAX:
        return False
    avant = joueur.reserve
    joueur.ajouter_munitions(d["valeur"])
    _msg(stats, d, f"MUNITIONS {avant} -> {joueur.reserve}")
    return True


def _eff_soin(stats, joueur, d, butin=None):
    if joueur.pv >= config.JOUEUR_PV_MAX:
        return False
    avant = joueur.pv
    joueur.soigner(d["valeur"])
    _msg(stats, d, f"SOIN {avant} -> {joueur.pv}")
    return True


def _eff_vie_max(stats, joueur, d, butin=None):
    ancien_max = config.JOUEUR_PV_MAX
    stats.vie_max_pct += d["valeur"]
    stats.recalculer_pv_max()
    joueur.pv = min(config.JOUEUR_PV_MAX, joueur.pv + int(d["valeur"] * stats._base_pv_max))
    _msg(stats, d, f"VIE MAX : {ancien_max} -> {config.JOUEUR_PV_MAX}")
    return True


def _eff_stat(stats, joueur, d, butin=None):
    s = d["stat"]
    avant = stats._bonus.get(s, 0.0)
    if avant >= d["cap"]:
        return False
    stats._bonus[s] = min(d["cap"], avant + d["valeur"])
    gain = int((stats._bonus[s] - avant) * 100)
    _msg(stats, d, f"{d['label']} +{gain}%  (total +{int(stats._bonus[s]*100)}%)")
    return True


def _eff_auto_regen(stats, joueur, d, butin=None):
    if stats.auto_regen:
        return False
    stats.auto_regen = True
    stats.regen_timer = 0.0
    _msg(stats, d, "AUTO-REGEN ACTIVEE (1 PV / 2 s)")
    return True


def _eff_equipement(stats, joueur, d, butin=None):
    """Arme / armure : ajoutée à l'inventaire si le poids max le permet, équipée d'office si le slot est vide."""
    inst = butin.instance if butin is not None and butin.instance else \
        inventaire.generer_instance_item(d["item"])
    couleur = RARETES[inst["rarete"]]["couleur"]
    ok, res = inventaire.ajouter(inst)
    if not ok:
        if butin is None or not butin.notifie:      # un seul message par objet au sol
            if butin is not None:
                butin.notifie = True
            stats.messages_ramassage.append(
                (f"TROP LOURD ({inventaire.poids_porte()}/{inventaire.poids_max()} MB) : {inst['nom']}",
                 (255, 80, 80)))
        return False                                # reste au sol
    texte = f"{inst['nom']} [{inst['rarete'].upper()}]"
    if inventaire.equipees[inst["type"]] is None:
        inventaire.equiper(res)
        texte += "  EQUIPE"
    else:
        texte += f"  ->  [TAB] equip {res}"
    stats.messages_ramassage.append((texte, couleur))
    return True


EFFETS = {"equipement": _eff_equipement, "munitions": _eff_munitions, "soin": _eff_soin, "vie_max": _eff_vie_max,
          "stat": _eff_stat, "auto_regen": _eff_auto_regen}


def appliquer(def_id, stats, joueur, butin=None):
    d = BOOSTS[def_id]
    return EFFETS[d["effet"]](stats, joueur, d, butin)


# =============================================================
#  Tirage & spawn
# =============================================================


def tirer_butin(type_coffre, x, z, rand_gen=None):
    rng = rand_gen or random
    cdef = COFFRES[type_coffre]
    biais = cdef.get("rarete_biais")
    table = table_butin(cdef["table"])
    total = sum(w for _, w in table)
    r = rng.random() * total
    acc = 0.0
    for def_id, w in table:
        acc += w
        if r <= acc:
            return Butin(x, z, def_id, biais)
    return Butin(x, z, table[-1][0], biais)


def spawner_butin(butin):
    if butin.def_id in PICKUP_IDS:
        from world import entity
        entity.pickups.append([butin.x, butin.z, PICKUP_IDS.index(butin.def_id), butin.spawn_time])
        return
    butins_au_sol.append(butin)


# =============================================================
#  Ramassage : touche F (voir Jeu.interagir dans main.py).
#  Mode auto (config.RAMASSAGE_AUTO) : ramassage au contact, SANS aimant.
# =============================================================
def ramasser_butins(joueur, stats, joueur_x, joueur_z, dt):
    if not config.RAMASSAGE_AUTO:
        return
    now = time.time()
    survivants = []
    for b in butins_au_sol:
        if now - b.spawn_time < DELAI_GRACE_BUTIN:
            survivants.append(b)
            continue
        d = math.hypot(b.x - joueur_x, b.z - joueur_z)
        if d < config.RAYON_RAMASSAGE_BUTINS and appliquer(b.def_id, stats, joueur, b):
            continue                      # ramassé
        survivants.append(b)              # trop loin / plein / trop lourd : reste au sol
    butins_au_sol[:] = survivants


# =============================================================
#  Stats du joueur
# =============================================================
class StatsBoostes:
    def __init__(self):
        self._bonus = {}                 # stat -> bonus cumulé (ex: "vitesse": 0.3)
        self._base_pv_max = config.JOUEUR_PV_MAX_BASE
        self.vie_max_pct = 0.0
        self.recalculer_pv_max()
        self.auto_regen = False
        self.regen_timer = 0.0
        self._regen_equip = 0.0
        self.messages_ramassage = []     # [(texte, couleur)]

    def recalculer_pv_max(self, joueur=None):
        """PV max = (base + PV de l'équipement) x (1 + boosts de vie max)."""
        ancien = config.JOUEUR_PV_MAX
        config.JOUEUR_PV_MAX = int(round((self._base_pv_max + config.BONUS_HP) * (1.0 + self.vie_max_pct)))
        if joueur is not None:
            if config.JOUEUR_PV_MAX > ancien:
                joueur.pv += config.JOUEUR_PV_MAX - ancien     # gagner de la vie max donne aussi la vie
            joueur.pv = min(joueur.pv, config.JOUEUR_PV_MAX)

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
        if joueur.mort:
            return
        if self.auto_regen and joueur.pv < config.JOUEUR_PV_MAX:
            self.regen_timer += dt
            if self.regen_timer >= config.AUTOREGEN_DELAI:
                self.regen_timer -= config.AUTOREGEN_DELAI
                joueur.pv = min(config.JOUEUR_PV_MAX, joueur.pv + config.AUTOREGEN_PV)
        # Régénération du casque (X PV/s) : on accumule les fractions, les PV restent entiers
        if config.REGEN_EQUIP > 0 and joueur.pv < config.JOUEUR_PV_MAX:
            self._regen_equip += config.REGEN_EQUIP * dt
            n = int(self._regen_equip)
            if n:
                self._regen_equip -= n
                joueur.pv = min(config.JOUEUR_PV_MAX, joueur.pv + n)

    def appliquer(self, butin, joueur):
        return appliquer(butin.def_id, self, joueur, butin)

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
