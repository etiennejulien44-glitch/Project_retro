# data/coffres.py
# ============================================================================
#  AJOUTER UN COFFRE = ajouter UNE entrée ici. Rien d'autre.
#    modele / echelle  : géométrie (liste de segments, voir data/modeles.py)
#    couleur           : couleur fermé ; si "couleur_pulse" existe, le coffre pulse entre les deux
#    table             : nom de la table de butin (voir "tables" dans data/boosts.py)
#  Pour qu'il apparaisse : ajoute son poids dans "poids_coffres" d'un biome (data/biomes.py).
# ============================================================================
from data.modeles import MODELE_CHEST, PRISMATIC_CHEST

COFFRES = {
    "classique": {
        "modele": MODELE_CHEST, "echelle": 1.0,
        "couleur": (255, 210, 90), "couleur_ouvert": (255, 255, 255),
        "table": "classique",
    },
    "prismatique": {
        "modele": PRISMATIC_CHEST, "echelle": 1.0,
        "couleur": (60, 60, 255), "couleur_pulse": (240, 190, 255),
        "couleur_ouvert": (255, 255, 255),
        "table": "prismatique",
    },
    "military": {
        "modele": PRISMATIC_CHEST, "echelle": 1.2,
        "couleur": (255, 25, 25), "couleur_pulse": (200, 150, 255),
        "couleur_ouvert": (0, 0, 0),
        "table": "military"
    }
}
