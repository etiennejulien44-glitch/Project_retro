# engine/textes.py -- polices / textes / surfaces EN CACHE (jamais de Font ni de Surface créés à chaque frame)
import pygame

_POLICES, _TEXTES, _SURFS = {}, {}, {}
OMBRE = (6, 0, 16)


def police(taille):
    f = _POLICES.get(taille)
    if f is None:
        f = _POLICES[taille] = pygame.font.Font(None, taille)
    return f


def texte(txt, taille, couleur, ombre=False):
    """Surface de texte mise en cache. ombre=True : liseré sombre (lisible sans fond noir)."""
    cle = (txt, taille, couleur, ombre)
    img = _TEXTES.get(cle)
    if img is None:
        if len(_TEXTES) > 600:
            _TEXTES.clear()
        img = police(taille).render(txt, True, couleur)
        if ombre:
            fond = police(taille).render(txt, True, OMBRE)
            w, h = img.get_size()
            out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2), (2, 2), (0, 0)):
                out.blit(fond, (dx, dy))
            out.blit(img, (1, 1))
            img = out
        _TEXTES[cle] = img
    return img


def ecrire(surf, txt, taille, couleur, x, y, ancre="g", ombre=True):
    """Écrit un texte ; ancre : g (gauche) | d (droite) | c (centre). Retourne la largeur dessinée."""
    img = texte(txt, taille, couleur, ombre)
    w = img.get_width()
    if ancre == "d":
        x -= w
    elif ancre == "c":
        x -= w // 2
    surf.blit(img, (x, y))
    return w


def voile(w, h, couleur, alpha):
    """Rectangle plein semi-transparent (alpha global : bien plus rapide que SRCALPHA). Pour les voiles plein écran."""
    cle = (w, h, couleur)
    s = _SURFS.get(cle)
    if s is None:
        s = _SURFS[cle] = pygame.Surface((w, h))
        s.fill(couleur)
    s.set_alpha(alpha)
    return s
