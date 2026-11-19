# world/monstre.py
import math
from data.monstres import MONSTRES
from engine.geometrie import diff_angle

ABSORBE, DEGATS = 0, 1       # résultat de Monstre.encaisser()


class Monstre:
    """Monstre générique piloté par les données du bestiaire (data/monstres.py).
    Les champs etat/t_etat/dir/faces/rot/y_haut servent aux comportements à états (striker, shield, phasme)."""
    __slots__ = ("x", "z", "type_cle", "data", "tipo", "hp", "hp_max", "cd", "hit", "phase",
                 "etat", "t_etat", "dir_x", "dir_z", "faces", "rot", "y_haut", "face_touchee",
                 "ralenti", "vuln", "mult_inf", "fx", "allie", "tag")

    def __init__(self, x, z, type_cle, rng):
        self.x = x
        self.z = z
        self.type_cle = type_cle
        self.data = MONSTRES[type_cle]
        self.tipo = list(MONSTRES).index(type_cle)           # rétrocompatibilité (tipo 0 ou 1)

        self.hp_max = self.data["pv_max"]
        self.hp = self.hp_max
        self.cd = 0.5 + rng.random()                          # Délai avant la 1ère action
        self.hit = 0.0                                        # Effet visuel de dégât
        self.phase = rng.random() * 2 * math.pi

        comportement = self.data["comportement"]
        self.etat = "traque" if comportement == "phasme" else "repos"
        self.t_etat = self.cd
        a = rng.random() * 2 * math.pi
        self.dir_x, self.dir_z = math.sin(a), math.cos(a)
        self.faces = [True] * self.data.get("nb_faces", 0)    # Polygone Shield : faces encore debout
        self.rot = rng.random() * 2 * math.pi                 # orientation du bouclier
        self.y_haut = 0.0                                     # Phasme : 0 = sous la grille, 1 = sorti
        self.face_touchee = -1
        # --- effets des compétences (world/competences.py recalcule ralenti/vuln/mult_inf chaque frame) ---
        self.ralenti = 1.0       # facteur de temps de l'IA : 1 normal, 0.7 ralenti, 0 étourdi
        self.vuln = 1.0          # multiplicateur de dégâts SUBIS
        self.mult_inf = 1.0      # multiplicateur de dégâts INFLIGÉS au joueur
        self.fx = {}             # effets actifs : controle, etourdi, corr, repousse...
        self.allie = False       # piraté (Contrôle total) : combat pour le joueur
        self.tag = 0             # marqueur anti-boucle de Suppression rapide

    # -- ciblage -----------------------------------------------------------
    @property
    def ciblable(self):
        if self.allie:
            return False
        etats = self.data.get("etats_ciblables")
        return etats is None or self.etat in etats

    # -- dégâts ------------------------------------------------------------
    def encaisser(self, degats, ox, oz):
        """Applique un tir venant du point (ox, oz). Un Polygone Shield perd UNE face par tir si la face
        touchée est encore debout ; sinon le coeur encaisse. -> ABSORBE ou DEGATS."""
        n = len(self.faces)
        if n:
            pas = 2 * math.pi / n
            phi = math.atan2(ox - self.x, oz - self.z)          # direction du tireur
            i = int(round(diff_angle(phi, self.rot) / pas)) % n
            if self.faces[i]:
                self.faces[i] = False
                self.face_touchee = i
                return ABSORBE
        self.hp -= degats
        return DEGATS
