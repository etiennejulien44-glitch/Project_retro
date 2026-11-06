# data/bestiaire.py
# ============================================================================
#  AJOUTER UN MONSTRE = ajouter UNE entrée ici (+ son modèle dans data/modeles.py).
#  Rien d'autre à toucher : rendu, IA, barre de vie et spawn sont pilotés par ces champs.
#  Pour qu'il apparaisse : mets sa clé dans "monstres_spawn" d'un biome (data/biomes.py).
#
#  comportement : "melee" (fonce au contact) | "distance" (garde ses distances et tire)
# ============================================================================
from data.modeles import MODELE_ARAIGNEE, MODELE_DRONE, MODELE_TOURELLE, MODELE_GLITCH

BESTIAIRE = {
    "araignee": {
        "nom": "Araignée Corps-à-Corps",
        "comportement": "melee",
        # --- rendu ---
        "modele": MODELE_ARAIGNEE, "echelle": 1.0, "couleur": (255, 130, 30),
        "decal_y": 0.0, "anim_freq": 12.0, "anim_amp": 6.0, "hauteur_barre": 42,
        # --- stats ---
        "pv_max": 30, "vitesse": 4.5, "portee": 3.5, "aggro": 120.0,
        "degats": 10, "cooldown": 1.2, "hauteur_centre": -15,
    },
    "drone": {
        "nom": "Drone à Distance",
        "comportement": "distance",
        "modele": MODELE_DRONE, "echelle": 1.0, "couleur": (255, 235, 70),
        "decal_y": -40.0, "anim_freq": 6.0, "anim_amp": 15.0, "hauteur_barre": 98,
        "pv_max": 20, "vitesse": 6.0, "portee_tir": 150.0, "dist_pref": 80.0,
        "aggro": 140.0, "degats": 5, "cooldown": 2.0, "hauteur_centre": -65,
    },
    "tourelle": {
        "nom": "Tourelle Sentinelle",
        "comportement": "distance",       # vitesse 0 = reste en place : cache-toi derrière un couvert !
        "modele": MODELE_TOURELLE, "echelle": 1.0, "couleur": (255, 60, 60),
        "decal_y": 0.0, "anim_freq": 3.0, "anim_amp": 0.0, "hauteur_barre": 60,
        "pv_max": 40, "vitesse": 0.0, "portee_tir": 700.0, "dist_pref": 300.0,
        "aggro": 750.0, "degats": 8, "cooldown": 1.6, "hauteur_centre": -20,
    },
    "glitch": {
        "nom": "Entité Glitch",
        "comportement": "melee",
        "modele": MODELE_GLITCH, "echelle": 1.0, "couleur": (230, 90, 255),
        "decal_y": 0.0, "anim_freq": 25.0, "anim_amp": 4.0, "hauteur_barre": 40,
        "pv_max": 15, "vitesse": 9.0, "portee": 3.5, "aggro": 150.0,
        "degats": 6, "cooldown": 0.8, "hauteur_centre": -12,
    },
}
