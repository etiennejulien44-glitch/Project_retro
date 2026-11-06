# data/armes.py
# ============================================================================
#  AJOUTER UNE ARME = ajouter UNE entrée dans ARMES. Pour la rendre trouvable :
#  une entrée dans data/boosts.py avec effet="arme", arme="<id>" et "tables".
#  stats modifiables en jeu depuis le terminal (TAB) :  set <arme> <stat> <valeur>
# ============================================================================
from data import config

ARMES = {
    "laser_v1": dict(nom="Laser Blaster v1", taille="12MB",
                     stats=dict(degats=200.0, cadence=0.18, chargeur=15, recharge=1.4, portee=1800)),
    "plasma":   dict(nom="Plasma Rifle", taille="15MB",
                     stats=dict(degats=4.0, cadence=0.55, chargeur=6, recharge=2.2, portee=1800)),
    "pulse_smg": dict(nom="Pulse SMG", taille="9MB",
                      stats=dict(degats=0.5, cadence=0.07, chargeur=40, recharge=1.8, portee=1200)),
}
ARME_DEPART = "laser_v1"

# bornes des stats modifiables (min, max)
BORNES = {"degats": (0.1, 50.0), "cadence": (0.03, 2.0), "chargeur": (1, 200),
          "recharge": (0.2, 6.0), "portee": (300, 1800)}
STAT_CONFIG = {"degats": "DEGATS_TIR", "cadence": "CADENCE_TIR", "chargeur": "CHARGEUR_TAILLE",
               "recharge": "RECHARGE_DUREE", "portee": "PORTEE_TIR"}

possedees = {}        # id -> stats courantes (modifiables)
equipee = None


def reinitialiser():
    global equipee
    possedees.clear()
    donner(ARME_DEPART)
    equiper(ARME_DEPART)


def donner(arme_id):
    """Ajoute l'arme à l'inventaire. False si déjà possédée."""
    if arme_id in possedees:
        return False
    possedees[arme_id] = dict(ARMES[arme_id]["stats"])
    return True


def appliquer_config():
    for stat, cle in STAT_CONFIG.items():
        setattr(config, cle, possedees[equipee][stat])


def equiper(arme_id):
    global equipee
    if arme_id not in possedees:
        return False
    equipee = arme_id
    appliquer_config()
    return True


def modifier(arme_id, stat, valeur):
    """Retourne (ok, message)."""
    if arme_id not in possedees:
        return False, f"arme inconnue : {arme_id}"
    if stat not in BORNES:
        return False, f"stat inconnue ({', '.join(BORNES)})"
    lo, hi = BORNES[stat]
    if not lo <= valeur <= hi:
        return False, f"{stat} doit être entre {lo} et {hi}"
    possedees[arme_id][stat] = int(valeur) if stat in ("chargeur", "portee") else float(valeur)
    if arme_id == equipee:
        appliquer_config()
    return True, f"{arme_id}.{stat} = {possedees[arme_id][stat]}"


def reset_arme(arme_id):
    if arme_id not in possedees:
        return False
    possedees[arme_id] = dict(ARMES[arme_id]["stats"])
    if arme_id == equipee:
        appliquer_config()
    return True
