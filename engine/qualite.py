# engine/qualite.py -- niveaux de qualité + adaptation AUTOMATIQUE aux FPS
#  Le niveau agit sur : halos (glow), épaisseur des arêtes, distance d'affichage, nombre de particules.
#  L'option "qualite" = auto | bas | moyen | haut (cd option ; set qualite auto).
from types import SimpleNamespace
from data import reglages

PROFILS = {
    #            halo terrain / halo entités / arêtes épaisses jusqu'à / ratio distance / ratio particules
    "bas":   SimpleNamespace(nom="bas",   glow_terrain=0,   glow_entites=0,   bord_epais=0,   distance_ratio=0.60, particules_ratio=0.30),
    "moyen": SimpleNamespace(nom="moyen", glow_terrain=350, glow_entites=550, bord_epais=300, distance_ratio=0.80, particules_ratio=0.60),
    "haut":  SimpleNamespace(nom="haut",  glow_terrain=600, glow_entites=900, bord_epais=400, distance_ratio=1.00, particules_ratio=1.00),
}
ORDRE = ["bas", "moyen", "haut"]


class Qualite:
    FENETRE = 60                     # frames mesurées avant de décider
    def __init__(self):
        self.niveau = len(ORDRE) - 1
        self._n = 0
        self._somme_dt = 0.0
        self._somme_travail = 0.0
        self._lent = 0               # fenêtres consécutives trop lentes
        self._large = 0              # fenêtres consécutives avec de la marge
        self._cooldown = 0

    @property
    def auto(self):
        return reglages.get("qualite") == "auto"

    def profil(self):
        choix = reglages.get("qualite")
        return PROFILS[ORDRE[self.niveau]] if choix == "auto" else PROFILS[choix]

    def observer(self, dt_reel, t_travail, budget):
        """À appeler à chaque frame. dt_reel = durée réelle de la frame, t_travail = CPU utilisé (sans attente
        de vsync/limiteur), budget = 1/fps_cible. -> True si le niveau vient de changer (re-appliquer la distance)."""
        if not self.auto:
            return False
        self._n += 1
        self._somme_dt += dt_reel
        self._somme_travail += t_travail
        if self._n < self.FENETRE:
            return False
        dt_moy, tr_moy = self._somme_dt / self._n, self._somme_travail / self._n
        self._n, self._somme_dt, self._somme_travail = 0, 0.0, 0.0
        if self._cooldown > 0:
            self._cooldown -= 1
            return False
        if dt_moy > budget * 1.18 or tr_moy > budget * 0.97:        # on rate la cible
            self._lent += 1
            self._large = 0
            if self._lent >= 1 and self.niveau > 0:
                self.niveau -= 1
                self._lent = 0
                self._cooldown = 2
                return True
        elif tr_moy < budget * 0.55:                                 # beaucoup de marge
            self._large += 1
            self._lent = 0
            if self._large >= 4 and self.niveau < len(ORDRE) - 1:
                self.niveau += 1
                self._large = 0
                self._cooldown = 3
                return True
        else:
            self._lent = self._large = 0
        return False


qualite = Qualite()


def profil():
    return qualite.profil()


def distance_effective():
    return reglages.get("distance") * profil().distance_ratio
