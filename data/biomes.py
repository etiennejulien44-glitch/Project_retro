BIOMES = {
    "neon_grid": {
        "nom": "Grille Néon Standard",
        "echelle_bruit_1": 0.03,
        "echelle_bruit_2": 0.12,
        "eval_hauteur": 5.0,
        "type_relief": "lisse",          # Relief vagues douces
        "densite_arbres_max": 2,
        "chances_coffre_prismatique": 0.15,
        "monstres_spawn": ["araignee", "drone"],
        "couleur_grille": (255, 0, 128),
        "couleur_brouillard": (20, 0, 40),
        "couleur_ciel": (10, 0, 20),
        "couleur_arbres": (0, 255, 255),
    },
    "cyber_wasteland": {
        "nom": "Badlands Synthwave",
        "echelle_bruit_1": 0.05,
        "echelle_bruit_2": 0.15,
        "eval_hauteur": 8.0,
        "type_relief": "abrupte",        # Relief cassé, géométrique, marches d'escalier
        "densite_arbres_max": 0,
        "chances_coffre_prismatique": 0.30,
        "monstres_spawn": ["drone"],
        "couleur_grille": (0, 255, 200),
        "couleur_brouillard": (10, 30, 20),
        "couleur_ciel": (5, 15, 10),
        "couleur_arbres": (255, 128, 0),
    },
    "glitch_zone": {
        "nom": "Secteur Endommagé",
        "echelle_bruit_1": 0.07,
        "echelle_bruit_2": 0.22,
        "eval_hauteur": 7.0,
        "type_relief": "abrupte",
        "densite_arbres_max": 1,
        "chances_coffre_prismatique": 0.20,
        "monstres_spawn": ["drone", "drone", "araignee"],
        "couleur_grille": (200, 60, 255),
        "couleur_brouillard": (30, 0, 50),
        "couleur_ciel": (18, 0, 30),
        "couleur_arbres": (255, 0, 127),
    },
    "overclock_zone": {
        "nom": "Mémoire Cache",
        "echelle_bruit_1": 0.04,
        "echelle_bruit_2": 0.18,
        "eval_hauteur": 9.0,
        "type_relief": "lisse",
        "densite_arbres_max": 1,
        "chances_coffre_prismatique": 0.35,
        "monstres_spawn": ["araignee", "araignee", "drone"],
        "couleur_grille": (255, 140, 0),
        "couleur_brouillard": (40, 18, 0),
        "couleur_ciel": (25, 10, 0),
        "couleur_arbres": (255, 220, 0),
    },
    "silent_void": {
        "nom": "Le Vide",
        "echelle_bruit_1": 0.02,
        "echelle_bruit_2": 0.10,
        "eval_hauteur": 11.0,
        "type_relief": "abrupte",
        "densite_arbres_max": 0,
        "chances_coffre_prismatique": 0.50,
        "monstres_spawn": ["drone", "araignee"],
        "couleur_grille": (0, 255, 100),
        "couleur_brouillard": (0, 12, 6),
        "couleur_ciel": (0, 4, 2),
        "couleur_arbres": (0, 255, 100),
    },
}

# ---------------------------------------------------------------------------
#  PROGRESSION : 5 couches concentriques autour du point de départ.
#  Couche i = biome principal COUCHES[i]. Plus on s'éloigne, plus c'est dur.
#  Une part de hasard (seed du monde) :
#    - les frontières entre couches sont irrégulières (JITTER_FRONTIERE)
#    - une région a une chance de prendre le biome d'une couche voisine (CHANCE_VARIANTE)
# ---------------------------------------------------------------------------
COUCHES = ["neon_grid", "glitch_zone", "cyber_wasteland", "overclock_zone", "silent_void"]
NB_COUCHES = len(COUCHES)

COUCHE_LARGEUR_REGIONS = 2.0    # épaisseur d'une couche, en régions (1 région = 6 chunks)
JITTER_FRONTIERE = 0.45         # +- irrégularité des frontières, en régions
CHANCE_VARIANTE = 0.25          # proba qu'une région prenne un biome voisin
RAYON_COUCHE_0 = 1.0            # rayon (en régions) autour du départ forcé en couche 0, sans variante

