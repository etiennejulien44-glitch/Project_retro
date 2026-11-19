# world/coffre.py -- interaction avec les coffres (ouverture, butin)
import math
import random
from data.coffres import COFFRES
from world import butin
from world.terrain import chest_caches

DISTANCE_INTERACTION_COFFRE = 160


def coffre_proche(zone, joueur_x, joueur_z, distance=DISTANCE_INTERACTION_COFFRE):
    """(coffre, distance) du coffre fermé le plus proche, ou (None, inf)."""
    meilleur, meilleure_dist = None, distance
    for cle in zone["cles"]:
        for chest in chest_caches[cle]:
            if chest["ouvert"]:
                continue
            d = math.hypot(chest["x"] - joueur_x, chest["z"] - joueur_z)
            if d < meilleure_dist:
                meilleure_dist = d
                meilleur = chest
    return meilleur, (meilleure_dist if meilleur else float("inf"))


def ouvrir_coffre_proche(zone, joueur_x, joueur_z, distance=DISTANCE_INTERACTION_COFFRE):
    meilleur, _ = coffre_proche(zone, joueur_x, joueur_z, distance)
    if meilleur is None:
        return None
    meilleur["ouvert"] = True
    butins = []
    for i in range(COFFRES[meilleur["type"]].get("nb_butins", 1)):
        dx, dz = (0.0, 0.0) if i == 0 else (random.uniform(-70, 70), random.uniform(-70, 70))
        b = butin.tirer_butin(meilleur["type"], meilleur["x"] + dx, meilleur["z"] + dz)
        butin.spawner_butin(b)
        butins.append(b)
    return butins


