# data/coffres.py
# ============================================================================
#  AJOUTER UN COFFRE = ajouter UNE entrée ici. Rien d'autre.
#    modele / echelle  : géométrie (liste de segments, voir data/modeles.py)
#    couleur           : couleur fermé ; si "couleur_pulse" existe, le coffre pulse entre les deux
#    table             : nom de la table de butin (voir "tables" dans data/boosts.py)
#    nb_butins         : (optionnel, défaut 1) nombre d'objets dans le coffre
#    rarete_biais      : (optionnel) {rarete: multiplicateur} pour les équipements tirés ici
#                        (rarete = commun / rare / leg / mythique / special, voir data/raretes.py)
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
        "rarete_biais": {"commun": 0.6, "leg": 1.5, "mythique": 1.5},
    },
    "military": {
        "modele": PRISMATIC_CHEST, "echelle": 1.2,
        "couleur": (255, 0, 120), "couleur_pulse": (231, 0, 255),
        "couleur_ouvert": (0, 0, 0),
        "table": "military",
        "nb_butins": 2,
        "rarete_biais": {"commun": 0.2, "rare": 0.7, "leg": 2.0, "mythique": 3.0, "special": 4.0},
    }
}
