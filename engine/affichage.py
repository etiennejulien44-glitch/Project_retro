# engine/affichage.py -- COMPOSE UNE IMAGE : scène 3D + interface (+ pause figée quand le terminal est ouvert)
#   Aussi : adaptation automatique de la qualité (engine/qualite.py) selon le temps de calcul réel.
from data import config, reglages
from engine import textes
from engine.qualite import qualite, distance_effective
from engine.scene import Scene
from ui.interface import Interface


class Affichage:
    def __init__(self, surface, jeu):
        self.surf = surface
        self.jeu = jeu
        self.scene = Scene()
        self.interface = Interface(jeu)
        self._snapshot = None

    def nouvelle_surface(self, surface):
        """La fenêtre a été recréée (plein écran / vsync) : on change de surface cible."""
        self.surf = surface
        self._snapshot = None

    def dessiner(self, temps):
        surf, jeu, ui = self.surf, self.jeu, self.interface
        if jeu.pause:
            # Pause : la scène est rendue UNE fois puis figée ; seul le terminal est redessiné.
            if self._snapshot is None:
                self._dessiner_scene(temps)
                surf.blit(textes.voile(config.LARGEUR, config.HAUTEUR, (0, 0, 0), 120), (0, 0))
                self._snapshot = surf.copy()
            else:
                surf.blit(self._snapshot, (0, 0))
            ui.dessiner_terminal(surf)
            return
        self._snapshot = None
        self._dessiner_scene(temps)

    def _dessiner_scene(self, temps):
        self.scene.dessiner(self.surf, self.jeu, temps)
        self.interface.nb_items = self.scene.nb_items
        self.interface.dessiner(self.surf, self.jeu, temps)

    # -- qualité adaptative ------------------------------------------------------
    def appliquer_distance(self):
        config.appliquer_distance(distance_effective())

    def adapter_qualite(self, dt_reel, t_travail, fps_cible):
        """À appeler à chaque frame. -> True si le niveau de qualité a changé."""
        if self.jeu.pause:
            return False
        if qualite.observer(dt_reel, t_travail, 1.0 / (fps_cible or 60)):
            self.appliquer_distance()
            return True
        return False
