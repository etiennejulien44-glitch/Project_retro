# ui/panneau_equipement.py -- panneau permanent À DROITE : pièces équipées (icône de rareté + boosts), boosts actifs, poids.
#   Pas de cadre ni de fond noir : texte à liseré sombre, filet fin coloré par rareté.
#   Icônes : assets/<rareté>_<objet>.png (data/armes.py, armures.py : champ "icone") ; slot vide : empty_slot.png ;
#   fichier absent -> icône vectorielle de secours.
#   Le panneau est composé UNE fois dans une surface en cache et recomposé seulement quand quelque chose change.
import pygame
from data import config
from data.raretes import RARETES, ICONE_SLOT_VIDE
from data.stats import formater
from engine import assets
from engine.textes import texte
from world import inventaire

CYAN, BLANC, GRIS, ROSE, JAUNE = (60, 240, 255), (240, 240, 255), (150, 150, 175), (255, 70, 170), (255, 220, 80)
NOMS_SLOTS = {"arme": "ARME", "casque": "CASQUE", "torse": "TORSE", "jambieres": "JAMBIÈRES", "bottes": "BOTTES", "ram": "RAM"}
LIBELLES_ARME = (("degats", "Dégâts", "{:.2f}"), ("cadence", "Cadence", "{:.2f}s"), ("chargeur", "Chargeur", "{:.0f}"),
                 ("recharge", "Recharge", "{:.1f}s"), ("portee", "Portée", "{:.0f}"))


# ---------------------------------------------------------------------------
#  Contenu (pur : testable sans pygame)
# ---------------------------------------------------------------------------
def lignes_stats(slot, item):
    """[(libellé, valeur)] des boosts d'une pièce équipée."""
    if item is None:
        return []
    if slot == "arme":
        return [(lib, fmt.format(item["stats"][k])) for k, lib, fmt in LIBELLES_ARME if k in item["stats"]]
    return [formater(stat, v) for stat, v in item["stats"].items()]


def lignes_boosts(stats):
    """Boosts temporaires (ramassés) : [(libellé, valeur)]."""
    res = []
    for cle, lib in (("vitesse", "Vitesse"), ("saut", "Saut"), ("degats", "Dégâts")):
        b = stats.bonus(cle)
        if b:
            res.append((lib, f"+{b * 100:.0f}%"))
    if stats.vie_max_pct:
        res.append(("PV max", f"+{stats.vie_max_pct * 100:.0f}%"))
    if stats.auto_regen:
        res.append(("Auto-régénération", "ON"))
    return res


# ---------------------------------------------------------------------------
#  Icônes vectorielles (fil de fer, couleur de la rareté)
# ---------------------------------------------------------------------------
def _icone(surf, slot, x, y, t, c):
    """Dessine l'icône du slot dans le carré (x, y, t, t)."""
    L, P = pygame.draw.lines, pygame.draw.polygon
    u = t / 10.0
    p = lambda *pts: [(x + a * u, y + b * u) for a, b in pts]
    if slot == "arme":
        L(surf, c, False, p((0, 4), (7, 4), (7, 2), (10, 2), (10, 6), (6, 6), (5, 9), (3, 9), (3, 6), (0, 6), (0, 4)), 2)
    elif slot == "casque":
        L(surf, c, False, p((1, 7), (1, 4), (3, 1.5), (7, 1.5), (9, 4), (9, 7), (1, 7)), 2)
        L(surf, c, False, p((2.5, 5), (7.5, 5)), 2)
    elif slot == "torse":
        L(surf, c, True, p((2, 1), (8, 1), (10, 3), (8, 4), (8, 9), (2, 9), (2, 4), (0, 3)), 2)
    elif slot == "jambieres":
        L(surf, c, True, p((2, 1), (8, 1), (8, 9), (5.6, 9), (5, 4), (4.4, 9), (2, 9)), 2)
    elif slot == "bottes":
        L(surf, c, True, p((2, 1), (5, 1), (5, 6), (9, 8), (9, 9), (2, 9)), 2)
    else:                                              # ram : puce
        P(surf, c, p((2, 2), (8, 2), (8, 8), (2, 8)), 2)
        for i in (3, 5, 7):
            L(surf, c, False, p((i, 0), (i, 2)), 1)
            L(surf, c, False, p((i, 8), (i, 10)), 1)


def _icone_item(surf, slot, item, x, y, t):
    """Icône d'un objet équipé (PNG de sa rareté) ou du slot vide, sinon icône vectorielle de secours."""
    if item is None:
        img = assets.image(ICONE_SLOT_VIDE, t)
        couleur = (70, 70, 90)
    else:
        rel = assets.chemin_icone(inventaire.definition(item), item["rarete"])
        img = assets.image(rel, t) if rel else None
        couleur = RARETES[item["rarete"]]["couleur"]
    if img is not None:
        surf.blit(img, (x, y))
    else:
        _icone(surf, slot, x + t * 0.1, y + t * 0.1, t * 0.8, couleur)


# ---------------------------------------------------------------------------
class PanneauEquipement:
    def __init__(self):
        k = config.HAUTEUR / 1080.0
        self.k = k
        self.largeur = int(330 * k)
        self.marge = int(22 * k)
        self.t_nom, self.t_stat, self.t_titre = max(16, int(26 * k)), max(14, int(21 * k)), max(14, int(22 * k))
        self.icone = max(32, int(64 * k) // 32 * 32 or 32)        # multiple de 32 : pixel art net (32 -> 64 -> 96)
        self._cache, self._signature = None, None

    def _signature_courante(self, stats):
        return (inventaire.version, tuple(sorted(stats._bonus.items())), stats.vie_max_pct, stats.auto_regen,
                inventaire.poids_porte(), inventaire.poids_max())

    @staticmethod
    def _ligne(surf, W, y, lib, val, taille, c_val, c_lib, x_droite):
        v = texte(val, taille, c_val, True)
        surf.blit(v, (x_droite - v.get_width(), y))
        l = texte(lib, taille, c_lib, True)
        surf.blit(l, (x_droite - v.get_width() - 10 - l.get_width(), y))

    def _composer(self, stats, compact):
        k, W, S = self.k, self.largeur, self.icone
        blocs = [(s, it, lignes_stats(s, it)) for s, it in inventaire.pieces_equipees()]
        boosts = lignes_boosts(stats)
        pas_nom, pas_stat, ecart = self.t_nom + 2, self.t_stat + 2, int(8 * k)

        def hauteur_bloc(ls):
            return max(S, pas_nom + (0 if compact else len(ls) * pas_stat)) + ecart

        h = pas_nom + sum(hauteur_bloc(ls) for _, _, ls in blocs)
        if boosts:
            h += pas_nom + len(boosts) * pas_stat + ecart
        surf = pygame.Surface((W, h + ecart), pygame.SRCALPHA)

        poids = texte(f"RAM  {inventaire.poids_porte()} / {inventaire.poids_max()} MB", self.t_titre, CYAN, True)
        surf.blit(poids, (W - poids.get_width(), 0))
        y = pas_nom
        x_txt = W - S - 10                       # les textes sont alignés à droite, contre l'icône
        for slot, it, ls in blocs:
            _icone_item(surf, slot, it, W - S, y, S)
            if it is None:
                txt = texte(f"— {NOMS_SLOTS[slot].lower()} —", self.t_stat, (90, 90, 115), True)
                surf.blit(txt, (x_txt - txt.get_width(), y + (S - txt.get_height()) // 2))
            else:
                col = RARETES[it["rarete"]]["couleur"]
                nom = texte(it["nom"], self.t_nom, col, True)
                surf.blit(nom, (x_txt - nom.get_width(), y))
                if not compact:
                    for i, (lib, val) in enumerate(ls):
                        self._ligne(surf, W, y + pas_nom + i * pas_stat, lib, val, self.t_stat, BLANC, GRIS, x_txt)
            y += hauteur_bloc(ls)
            if it is not None:                                                   # filet fin couleur de rareté
                pygame.draw.line(surf, RARETES[it["rarete"]]["couleur"], (W - int(170 * k), y - ecart // 2), (W, y - ecart // 2), 1)
        if boosts:
            t = texte("BOOSTS ACTIFS", self.t_titre, JAUNE, True)
            surf.blit(t, (W - t.get_width(), y))
            y += pas_nom
            for lib, val in boosts:
                self._ligne(surf, W, y, lib, val, self.t_stat, JAUNE, GRIS, W)
                y += pas_stat
        return surf

    # -- public ----------------------------------------------------------------
    def dessiner(self, surf, jeu, temps):
        W, H = config.LARGEUR, config.HAUTEUR
        y = int(18 * self.k)
        sig = self._signature_courante(jeu.stats)
        if sig != self._signature:
            self._cache = self._composer(jeu.stats, False)
            if y + self._cache.get_height() > H - int(150 * self.k):        # trop haut (petite résolution) : version compacte
                self._cache = self._composer(jeu.stats, True)
            self._signature = sig
        surf.blit(self._cache, (W - self.marge - self.largeur, y))
