# engine/assets.py -- chargement (paresseux + cache) des images de assets/
#   assets.image("empty_slot.png", hauteur=64)  -> Surface | None   (pixel art : agrandissement sans lissage)
#   assets.chemin_icone(definition, rarete)     -> "leg_helm.png" | None   (selon data/raretes.py + champ "icone")
#   Tout est tolérant : un fichier absent renvoie None (l'interface dessine alors une icône vectorielle).
import os
import pygame
from data.raretes import RARETES

RACINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
_images = {}


def image(rel, hauteur=None):
    cle = (rel, hauteur)
    if cle not in _images:
        try:
            img = pygame.image.load(os.path.join(RACINE, rel)).convert_alpha()
            if hauteur and img.get_height() != hauteur:
                img = pygame.transform.scale(img, (max(1, round(img.get_width() * hauteur / img.get_height())), int(hauteur)))
            _images[cle] = img
        except (pygame.error, OSError):
            _images[cle] = None
    return _images[cle]


def chemin_icone(definition, rarete):
    """Fichier d'icône d'un équipement : assets/<préfixe de rareté>_<icone>.png (noms alternatifs acceptés)."""
    noms = definition.get("icone")
    if not noms:
        return None
    for nom in ((noms,) if isinstance(noms, str) else noms):
        rel = f"{RARETES[rarete]['icone']}_{nom}.png"
        if os.path.exists(os.path.join(RACINE, rel)):
            return rel
    return None
