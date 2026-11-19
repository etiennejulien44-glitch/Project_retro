# data/boss.py
# ============================================================================
#  BOSS : paliers de SCORE + définitions des boss géométriques.
#  AJOUTER UN BOSS GÉOMÉTRIQUE = une entrée dans BOSS_GEO + une ligne dans PALIERS.
#    modele       : "cube" | "icosaedre"   (data/modeles.py : modele_cube / modele_icosaedre)
#    patterns     : liste de patterns ("ondes", "satellites") -> world/boss.py (registre _PATTERNS)
#    *_par_phase  : valeurs pour les phases 1 / 2 / 3 (seuils de PV dans config.BOSS_PHASE_2 / _3)
#  "araignee" = l'ancien Spider Boss (config.py, BOSS_*), il reste dispo dans les paliers.
# ============================================================================
BOSS_GEO = {
    "cube": {
        "nom": "CUBE ROTATIF", "modele": "cube", "rayon": 80.0, "couleur": (255, 40, 160),
        "pv": 360, "vitesse": 75.0, "dist_pref": 640.0, "hauteur_vol": 150.0, "rayon_visee": 150.0,
        "degats_contact": 15, "rot_vitesse": (0.7, 1.1, 1.7),
        "patterns": ("ondes",),
        "ondes_par_phase": (1, 2, 3), "onde_espacement": 280.0, "cd_onde": (4.5, 3.6, 3.0),
        "onde_vitesse": 400.0, "onde_rayon_max": 1300.0, "onde_degats": 18,
    },
    "icosaedre": {
        "nom": "ICOSAEDRE", "modele": "icosaedre", "rayon": 95.0, "couleur": (60, 240, 255),
        "pv": 420, "vitesse": 60.0, "dist_pref": 720.0, "hauteur_vol": 170.0, "rayon_visee": 160.0,
        "degats_contact": 15, "rot_vitesse": (0.5, 0.9, 1.4),
        "patterns": ("satellites", "ondes"),
        # tourelles satellites : tant qu'il en reste, le boss ne prend que `reduction_satellites` des dégâts
        "nb_satellites": (2, 3, 4), "sat_pv": 6, "sat_orbite": 290.0, "sat_vitesse_orbite": 0.9,
        "sat_cd_tir": 2.4, "sat_degats_mult": 0.6, "cd_deploiement": 7.0, "reduction_satellites": 0.25,
        "ondes_par_phase": (0, 0, 1), "onde_espacement": 280.0, "cd_onde": (9.0, 9.0, 6.0),
        "onde_vitesse": 380.0, "onde_rayon_max": 1200.0, "onde_degats": 16,
    },
}

# (score à atteindre, type de boss). Au-delà : on boucle sur BOUCLE_TYPES, tous les BOUCLE_INCREMENT points.
PALIERS = [
    (1500, "cube"),
    (4200, "icosaedre"),
    (8000, "araignee"),
]
BOUCLE_TYPES = ["cube", "icosaedre", "araignee"]
BOUCLE_INCREMENT = 3500
ECART_MIN = 800        # écart minimum entre la mort d'un boss et le suivant (même si le palier est déjà dépassé)


def palier(i):
    """(score_requis, type) du i-ème boss (0 = premier)."""
    if i < len(PALIERS):
        return PALIERS[i]
    n = i - len(PALIERS) + 1
    return PALIERS[-1][0] + n * BOUCLE_INCREMENT, BOUCLE_TYPES[i % len(BOUCLE_TYPES)]
