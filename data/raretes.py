# data/raretes.py -- raretés des équipements (armes / armures)
#   taux   : probabilité de tirage (relative)   mult : multiplicateur appliqué à la stat principale / aux dégâts
#   icone  : préfixe des fichiers d'icônes dans assets/  ->  assets/<icone>_<objet>.png  (ex: leg_helm.png)
#   couleur: couleur d'affichage partout (HUD, terminal, popups)   tout_substats : toutes les substats sont données
RARETES = {
    "commun":   {"taux": 0.45, "mult": 0.75, "couleur": (190, 190, 205), "icone": "common"},
    "rare":     {"taux": 0.35, "mult": 0.85, "couleur": (80, 180, 255), "icone": "rare"},
    "leg":      {"taux": 0.10, "mult": 1.00, "couleur": (255, 220, 80), "icone": "leg"},
    "mythique": {"taux": 0.07, "mult": 1.50, "couleur": (255, 70, 100), "icone": "mythique"},
    "special":  {"taux": 0.03, "mult": 1.25, "couleur": (200, 90, 255), "icone": "special", "tout_substats": True},
}

ICONE_SLOT_VIDE = "empty_slot.png"     # icône d'un slot sans équipement (dans assets/)
