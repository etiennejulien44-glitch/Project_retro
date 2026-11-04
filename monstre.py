# monstre.py
import math
import config


class Monstre:
    """tipo 0 = araignée (corps à corps), tipo 1 = drone (tire à distance)."""
    __slots__ = ("x", "z", "tipo", "hp", "hp_max", "cd", "hit", "phase")

    def __init__(self, x, z, tipo, rng):
        self.x = x
        self.z = z
        self.tipo = tipo
        self.hp_max = config.ARAIGNEE_PV if tipo == 0 else config.DRONE_PV
        self.hp = self.hp_max
        self.cd = 0.5 + rng.random()          # délai avant la 1re attaque
        self.hit = 0.0                         # > 0 : clignote en blanc (touché)
        self.phase = rng.random() * 2 * math.pi
