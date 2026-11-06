# data/biomes.py
# ============================================================================
#  AJOUTER UN BIOME = ajouter UNE entrée dans BIOMES. Rien d'autre.
#    couche          : profondeur (0 = départ, puis 1, 2, 3...) -> sa place dans la progression
#    monstres_spawn  : clés de data/bestiaire.py
#    poids_coffres   : clés de data/coffres.py
#    decors          : {id_decor: nombre par chunk} (data/decors.py) -> relief, couverts, identité
#  Les couches/numéros se règlent en bas du fichier.
# ============================================================================
BIOMES = {
    "neon_grid": {
        "couche": 0,
        "nom": "Grille Néon Standard",
        "echelle_bruit_1": 0.03,
        "echelle_bruit_2": 0.12,
        "eval_hauteur": 5.0,
        "type_relief": "lisse",          # Relief vagues douces
        "decors": {"arbre": 2, "bloc_data": 3},
        "poids_coffres": {"classique": 0.85, "prismatique": 0.15, "military": 0.2},
        "monstres_spawn": ["araignee", "drone"],
        "couleur_grille": (255, 0, 128),
        "couleur_brouillard": (20, 0, 40),
        "couleur_ciel": (10, 0, 20),
        "couleur_arbres": (0, 255, 255),
    },
    "cyber_wasteland": {
        "couche": 2,
        "nom": "Badlands Synthwave",
        "echelle_bruit_1": 0.05,
        "echelle_bruit_2": 0.15,
        "eval_hauteur": 8.0,
        "type_relief": "abrupte",        # Relief cassé, géométrique, marches d'escalier
        "decors": {"mur_ruine": 5, "arbre": 1},
        "poids_coffres": {"classique": 0.7, "prismatique": 0.30},
        "monstres_spawn": ["drone", "tourelle"],
        "couleur_grille": (0, 255, 200),
        "couleur_brouillard": (10, 30, 20),
        "couleur_ciel": (5, 15, 10),
        "couleur_arbres": (255, 128, 0),
    },
    "glitch_zone": {
        "couche": 1,
        "nom": "Secteur Endommagé",
        "echelle_bruit_1": 0.07,
        "echelle_bruit_2": 0.22,
        "eval_hauteur": 7.0,
        "type_relief": "abrupte",
        "decors": {"monolithe": 4, "bloc_data": 2},
        "poids_coffres": {"classique": 0.8, "prismatique": 0.20},
        "monstres_spawn": ["glitch", "glitch", "drone", "araignee"],
        "couleur_grille": (200, 60, 255),
        "couleur_brouillard": (30, 0, 50),
        "couleur_ciel": (18, 0, 30),
        "couleur_arbres": (255, 0, 127),
    },
    "overclock_zone": {
        "couche": 3,
        "nom": "Mémoire Cache",
        "echelle_bruit_1": 0.04,
        "echelle_bruit_2": 0.18,
        "eval_hauteur": 9.0,
        "type_relief": "lisse",
        "decors": {"rack_serveur": 4, "tour_chauffe": 2},
        "poids_coffres": {"classique": 0.65, "prismatique": 0.35},
        "monstres_spawn": ["tourelle", "araignee", "araignee", "drone"],
        "couleur_grille": (255, 140, 0),
        "couleur_brouillard": (40, 18, 0),
        "couleur_ciel": (25, 10, 0),
        "couleur_arbres": (255, 220, 0),
    },
    "silent_void": {
        "couche": 4,
        "nom": "Le Vide",
        "echelle_bruit_1": 0.02,
        "echelle_bruit_2": 0.10,
        "eval_hauteur": 11.0,
        "type_relief": "abrupte",
        "decors": {"obelisque": 3, "cristal": 6},
        "poids_coffres": {"classique": 0.5, "prismatique": 0.50, "military": 0.2},
        "monstres_spawn": ["glitch", "tourelle", "drone"],
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
# Ordre des couches dérivé automatiquement du champ "couche" de chaque biome (0 = départ).
COUCHES = [k for k, _ in sorted(BIOMES.items(), key=lambda kv: kv[1]["couche"])]
NB_COUCHES = len(COUCHES)

COUCHE_LARGEUR_REGIONS = 2.0    # épaisseur d'une couche, en régions (1 région = 6 chunks)
JITTER_FRONTIERE = 0.45         # +- irrégularité des frontières, en régions
CHANCE_VARIANTE = 0.25          # proba qu'une région prenne un biome voisin
RAYON_COUCHE_0 = 1.0            # rayon (en régions) autour du départ forcé en couche 0, sans variante

