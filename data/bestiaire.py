# data/bestiaire.py
# ============================================================================
#  AJOUTER UN MONSTRE = ajouter UNE entrée ici (+ son modèle dans data/modeles.py).
#  Rien d'autre à toucher : rendu, IA, barre de vie et spawn sont pilotés par ces champs.
#  Pour qu'il apparaisse : mets sa clé dans "monstres_spawn" d'un biome (data/biomes.py).
#
#  comportement : "melee" (fonce au contact) | "distance" (garde ses distances et tire)
#                 | "striker" | "shield" | "phasme"   (voir les fonctions @comportement de world/entity.py)
#  rendu        : "segments" (défaut : modèle fil de fer) | "rayon" | "shield" | "phasme"   (engine/rendu_monstres.py)
#  score        : points gagnés à la mort (sert aussi aux paliers de boss, data/boss_def.py)
#  rayon_visee  : taille de la zone touchable à l'écran (défaut 40)
#  AJOUTER UN COMPORTEMENT = une fonction @comportement("nom") dans entity.py + (si besoin) un @rendu("nom").
# ============================================================================
from data.modeles import MODELE_ARAIGNEE, MODELE_DRONE, MODELE_TOURELLE, MODELE_GLITCH, MODELE_PHASME

BESTIAIRE = {
    "araignee": {
        "score": 100,
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
        "score": 100,
        "nom": "Drone à Distance",
        "comportement": "distance",
        "modele": MODELE_DRONE, "echelle": 1.0, "couleur": (255, 235, 70),
        "decal_y": -40.0, "anim_freq": 6.0, "anim_amp": 15.0, "hauteur_barre": 98,
        "pv_max": 10, "vitesse": 6.0, "portee_tir": 150.0, "dist_pref": 80.0,
        "aggro": 140.0, "degats": 5, "cooldown": 2.0, "hauteur_centre": -65,
    },
    "tourelle": {
        "score": 150,
        "nom": "Tourelle Sentinelle",
        "comportement": "distance",       # vitesse 0 = reste en place : cache-toi derrière un couvert !
        "modele": MODELE_TOURELLE, "echelle": 1.0, "couleur": (255, 60, 60),
        "decal_y": 0.0, "anim_freq": 3.0, "anim_amp": 0.0, "hauteur_barre": 60,
        "pv_max": 40, "vitesse": 0.0, "portee_tir": 700.0, "dist_pref": 300.0,
        "aggro": 750.0, "degats": 8, "cooldown": 1.6, "hauteur_centre": -20,
    },
    "glitch": {
        "score": 100,
        "nom": "Entité Glitch",
        "comportement": "melee",
        "modele": MODELE_GLITCH, "echelle": 1.0, "couleur": (230, 90, 255),
        "decal_y": 0.0, "anim_freq": 25.0, "anim_amp": 4.0, "hauteur_barre": 40,
        "pv_max": 15, "vitesse": 9.0, "portee": 3.5, "aggro": 150.0,
        "degats": 6, "cooldown": 0.8, "hauteur_centre": -12,
    },

    # ------------------------------------------------------------------
    #  NOUVEAUX ENNEMIS (game design : Ennemis Réguliers)
    # ------------------------------------------------------------------
    "striker": {
        "nom": "Striker (Ligne Électrique)",
        "comportement": "striker", "rendu": "rayon",
        "modele": None, "couleur": (60, 240, 255),          # pas de volume : un simple rayon d'énergie
        "decal_y": -26.0, "anim_freq": 0.0, "anim_amp": 0.0, "hauteur_barre": 46,
        "pv_max": 4, "score": 120, "rayon_visee": 34, "hauteur_centre": -26,
        "aggro": 1000.0, "duree_vise": 0.85, "verrou": 0.22,   # il se verrouille 0.22 s avant de partir : esquive possible
        "vitesse_charge": 1150.0, "duree_charge": 1.0, "rayon_contact": 48.0,
        "degats": 14, "cooldown": 1.6,
        "longueur_repos": 36.0, "longueur_vise": 170.0, "longueur_charge": 300.0,
    },
    "polygone_shield": {
        "nom": "Polygone Shield",
        "comportement": "shield", "rendu": "shield",
        "modele": None, "couleur": (255, 200, 40),
        "nb_faces": 6, "rayon_faces": 34.0, "y_bas": -4.0, "y_haut": -62.0,
        "decal_y": 0.0, "anim_freq": 0.0, "anim_amp": 0.0, "hauteur_barre": 78,
        "pv_max": 8, "score": 250, "rayon_visee": 62, "hauteur_centre": -32,   # pv_max = PV du CŒUR (les faces absorbent 1 tir chacune)
        "aggro": 900.0, "vitesse": 55.0, "portee": 95.0, "vit_rot": 0.75,    # vit_rot (rad/s) : plus lent que le joueur qui tourne autour
        "degats": 12, "cooldown": 1.5,
    },
    "phasme": {
        "nom": "Phasme (Traqueur de Grille)",
        "comportement": "phasme", "rendu": "phasme",
        "modele": MODELE_PHASME, "echelle": 1.0, "couleur": (255, 70, 200),
        "decal_y": 0.0, "anim_freq": 0.0, "anim_amp": 0.0, "hauteur_barre": 90,
        "pv_max": 10, "score": 200, "rayon_visee": 46, "hauteur_centre": -35,
        "etats_ciblables": ("surgit", "surgi"),             # invulnérable tant qu'il est sous la grille
        "distorsion": {"amp": 38.0, "sigma": 105.0},         # bosse qui se déplace dans le maillage du sol
        "aggro": 1100.0, "vitesse": 170.0, "bonus_proche": 1.9, "dist_rush": 420.0,
        "dist_surgir": 150.0, "duree_surgit": 0.30, "duree_expose": 2.0, "duree_plonge": 0.45,
        "portee_attaque": 125.0, "degats": 16, "cooldown": 1.3, "cooldown_attaque": 0.9,
    },
}
