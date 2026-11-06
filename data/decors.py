# data/decors.py
# ============================================================================
#  AJOUTER UN DÉCOR = ajouter UNE entrée ici (+ son modèle dans data/modeles.py).
#    rayon     : taille de l'obstacle au sol (collision + espacement)
#    solide    : True (défaut) = bloque le joueur ET les tirs ennemis -> sert de COUVERT
#    flottant  : décalage en hauteur (cristaux...)
#    couleur / couleur_2 : bas / haut du modèle
#  Pour qu'il apparaisse : "decors": {"id": nombre_par_chunk} dans un biome (data/biomes.py).
# ============================================================================
from data.modeles import (MODELE_ARBRE, MODELE_BLOC, MODELE_MONOLITHE, MODELE_MUR,
                          MODELE_RACK, MODELE_TOUR, MODELE_OBELISQUE, MODELE_CRISTAL)

DECORS = {
    "arbre":        dict(modele=MODELE_ARBRE, echelle=4.0, couleur=(120, 70, 255), couleur_2=(40, 240, 255), rayon=24),
    "bloc_data":    dict(modele=MODELE_BLOC, couleur=(0, 200, 255), couleur_2=(255, 0, 160), rayon=58),
    "monolithe":    dict(modele=MODELE_MONOLITHE, couleur=(220, 70, 255), couleur_2=(255, 255, 255), rayon=34),
    "mur_ruine":    dict(modele=MODELE_MUR, couleur=(255, 128, 0), couleur_2=(255, 60, 20), rayon=72),
    "rack_serveur": dict(modele=MODELE_RACK, couleur=(255, 140, 0), couleur_2=(255, 230, 120), rayon=48),
    "tour_chauffe": dict(modele=MODELE_TOUR, couleur=(255, 200, 0), couleur_2=(255, 70, 0), rayon=32),
    "obelisque":    dict(modele=MODELE_OBELISQUE, couleur=(0, 255, 100), couleur_2=(210, 255, 225), rayon=34),
    "cristal":      dict(modele=MODELE_CRISTAL, couleur=(0, 255, 170), rayon=18, solide=False, flottant=70),
}

for _d in DECORS.values():       # champs dérivés automatiquement
    _d.setdefault("echelle", 1.0)
    _d.setdefault("solide", True)
    _d.setdefault("flottant", 0.0)
    _d.setdefault("couleur_2", _d["couleur"])
    _d["hauteur"] = -min(min(a[1], b[1]) for a, b in _d["modele"]) * _d["echelle"]
