# ui/barre_competences.py -- compétences ACTIVES débloquées : touche, nom, niveau, recharge. Colonne à gauche, sans cadre.
import pygame
from data import config
from data.competences import BRANCHES, COMPETENCES
from data.controles import TOUCHES
from engine.textes import ecrire
from world import competences

PRET, ATTENTE = (120, 255, 150), (110, 110, 135)


def lignes():
    """[(touche, nom, couleur_branche, niveau, cd_restant, cd_total)] des compétences actives utilisables."""
    res = []
    for cid, d in COMPETENCES.items():
        if "cd" in d and competences.actif(cid):
            touche = d.get("touche", "")
            res.append((pygame.key.name(TOUCHES[touche]).upper() if touche in TOUCHES else "?", d["nom"],
                        BRANCHES[d["branche"]]["couleur"], competences.niveau(cid), competences.cd.get(cid, 0.0), d["cd"]))
    return res


class BarreCompetences:
    def __init__(self):
        k = config.HAUTEUR / 1080.0
        self.k = k
        self.t = max(16, int(24 * k))

    def dessiner(self, surf, jeu, temps):
        k, t = self.k, self.t
        x, y = int(26 * k), int(config.HAUTEUR * 0.34)
        if competences.points > 0:
            ecrire(surf, f"{competences.points} PC DISPONIBLES", t, (255, 230, 90), x, y)
            ecrire(surf, "terminal : cd skills", max(14, t - 6), (150, 150, 175), x, y + t + 2)
            y += 2 * t + int(14 * k)
        for touche, nom, couleur, niv, reste, total in lignes():
            ecrire(surf, f"[{touche}]", t, PRET if reste <= 0 else ATTENTE, x, y)
            ecrire(surf, f"{nom}  Nv{niv}", t, couleur, x + int(54 * k), y)
            largeur = int(190 * k)
            fait = 1.0 if reste <= 0 else 1.0 - reste / total
            yb = y + t + 1
            pygame.draw.line(surf, (50, 45, 80), (x, yb), (x + largeur, yb), 2)
            pygame.draw.line(surf, PRET if reste <= 0 else couleur, (x, yb), (x + int(largeur * fait), yb), 2)
            if reste > 0:
                ecrire(surf, f"{reste:.0f}s", max(14, t - 6), ATTENTE, x + largeur + 8, y + 2)
            y += t + int(16 * k)
        if competences.suppression is not None:
            ecrire(surf, f"SUPPRESSION : {competences.suppression['restant']} sauts", t, (60, 240, 255), x, y)
            y += t + 4
        if competences.dome is not None:
            ecrire(surf, f"DÔME : {max(0.0, competences.dome['fin'] - competences.t):.1f}s", t, (255, 200, 60), x, y)
            y += t + 4
        if competences.propagation is not None:
            ecrire(surf, f"PROPAGATION : {max(0.0, competences.propagation['fin'] - competences.t):.1f}s", t, (190, 100, 255), x, y)
