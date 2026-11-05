# world/monstre.py
import math
from data.bestiaire import BESTIAIRE


class Monstre:
    """Monstre générique piloté par les données du bestiaire."""
    __slots__ = ("x", "z", "type_cle", "data", "tipo", "hp", "hp_max", "cd", "hit", "phase")

    def __init__(self, x, z, type_cle, rng):
        self.x = x
        self.z = z
        self.type_cle = type_cle
        self.data = BESTIAIRE[type_cle]
        
        # Rétrocompatibilité avec le moteur existant (tipo 0 ou 1)
        self.tipo = self.data["tipo"]
        
        self.hp_max = self.data["pv_max"]
        self.hp = self.hp_max
        self.cd = 0.5 + rng.random()          # Délai avant la 1ère action
        self.hit = 0.0                         # Effet visuel de dégât
        self.phase = rng.random() * 2 * math.pi