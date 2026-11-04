# ciel.py  --  décor synthwave : dégradé de ciel, étoiles, soleil rayé, montagnes
import math
import random
import numpy as np
import pygame
import config

# ----- PALETTE (modifie ici pour changer l'ambiance) -----
# du bas du ciel (horizon) vers le haut
CIEL_STOPS = [(0.00, (255, 120, 90)),
              (0.15, (240, 45, 150)),
              (0.45, (120, 12, 150)),
              (1.00, (8, 0, 28))]
SOLEIL_STOPS = [(0.0, (255, 240, 120)),    # haut du soleil
                (0.5, (255, 110, 150)),
                (1.0, (190, 25, 170))]     # bas du soleil
MONTAGNE_REMPLISSAGE = (24, 0, 54)
MONTAGNE_CONTOUR = (150, 30, 170)
HORIZON_LUEUR = (255, 150, 220)
HORIZON_LUEUR_2 = (255, 70, 170)

SPAN_CIEL = 460        # hauteur (px) du dégradé au-dessus de l'horizon
HAUTEUR_BANDE = 10     # le ciel est dessiné en bandes -> look rétro
SOLEIL_AZIMUT = 0.28   # direction du soleil (radians, 0 = plein devant au départ)
SOLEIL_ELEVATION = 0.21
SOLEIL_RAYON = 105
NB_ETOILES = 110
NB_MONTAGNES = 14


def _lerp(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def _degrade(stops, t):
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            return _lerp(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0.0)
    return stops[-1][1]


class Ciel:
    def __init__(self):
        n = SPAN_CIEL // HAUTEUR_BANDE
        self.bandes = [_degrade(CIEL_STOPS, (i + 0.5) / n) for i in range(n)]   # i = 0 : contre l'horizon
        self.couleur_haut = _degrade(CIEL_STOPS, 1.0)

        rng = random.Random(7)

        # --- étoiles : directions fixes dans le monde ---
        dirs, phases, bright = [], [], []
        for _ in range(NB_ETOILES):
            az = rng.uniform(0, 2 * math.pi)
            el = math.asin(rng.uniform(math.sin(0.10), math.sin(1.45)))
            dirs.append((math.cos(el) * math.sin(az), -math.sin(el), math.cos(el) * math.cos(az)))
            phases.append(rng.uniform(0, 6.28))
            bright.append(rng.uniform(0.45, 1.0))
        self.et_dirs = np.array(dirs, dtype=np.float64)
        self.et_phase = np.array(phases)
        self.et_bright = np.array(bright)

        # --- soleil ---
        e = SOLEIL_ELEVATION
        self.soleil_dir = np.array([[math.cos(e) * math.sin(SOLEIL_AZIMUT), -math.sin(e),
                                     math.cos(e) * math.cos(SOLEIL_AZIMUT)]])
        self.soleil_bandes = self._construire_soleil()

        # --- montagnes lointaines (azimut, demi-largeur angulaire, hauteur px) ---
        self.montagnes = []
        for k in range(NB_MONTAGNES):
            az = (k + rng.uniform(-0.3, 0.3)) * 2 * math.pi / NB_MONTAGNES
            self.montagnes.append((az, rng.uniform(0.05, 0.11), rng.uniform(28, 75)))

    def _construire_soleil(self):
        """Bandes horizontales du soleil, avec des 'coupures' de plus en plus larges vers le bas."""
        r, pas = SOLEIL_RAYON, 4
        bandes = []
        for dy in range(-r, r, pas):
            if dy > 0 and (dy % 18) < 2 + 10 * (dy / r):
                continue                                          # trait noir (ciel visible)
            milieu = dy + pas / 2
            hw = int(math.sqrt(max(0.0, r * r - milieu * milieu)))
            if hw <= 0:
                continue
            col = _degrade(SOLEIL_STOPS, (dy + r) / (2 * r))
            bandes.append((dy, hw, pas, col))
        return bandes

    # ------------------------------------------------------------------
    def _projeter_dirs(self, d):
        cy, sy = config.COS_YAW, config.SIN_YAW
        cp, sp = config.COS_PITCH, config.SIN_PITCH
        rx = d[:, 0] * cy - d[:, 2] * sy
        rz = d[:, 0] * sy + d[:, 2] * cy
        ry = d[:, 1] * cp - rz * sp
        rzf = d[:, 1] * sp + rz * cp
        ok = rzf > 0.05
        rzs = np.where(ok, rzf, 1.0)
        ex = config.LARGEUR * 0.5 + rx * config.FOCALE / rzs
        ey = config.HAUTEUR * 0.5 + ry * config.FOCALE / rzs
        return ex, ey, ok

    def dessiner(self, surf, temps):
        W, H, F = config.LARGEUR, config.HAUTEUR, config.FOCALE
        rect = pygame.draw.rect

        # ligne d'horizon (varie avec l'inclinaison de la caméra)
        tan_p = config.SIN_PITCH / config.COS_PITCH
        hy = int(max(-10000, min(10000, H * 0.5 - tan_p * F)))

        # 1) dégradé du ciel en bandes
        surf.fill(self.couleur_haut)
        for i, col in enumerate(self.bandes):
            bas = hy - i * HAUTEUR_BANDE
            haut = bas - HAUTEUR_BANDE
            if bas <= 0 or haut >= H:
                continue
            rect(surf, col, (0, haut, W, HAUTEUR_BANDE + 1))

        # 2) étoiles (scintillent doucement)
        ex, ey, ok = self._projeter_dirs(self.et_dirs)
        lum = self.et_bright * (0.7 + 0.3 * np.sin(temps * 2.0 + self.et_phase))
        for x, y, o, b in zip(ex.tolist(), ey.tolist(), ok.tolist(), lum.tolist()):
            if o and 0 <= x < W and 0 <= y < hy - 6:
                c = int(255 * b)
                rect(surf, (c, int(c * 0.75), 255), (int(x), int(y), 2, 2))

        # 3) soleil rayé
        sx, sy, sok = self._projeter_dirs(self.soleil_dir)
        if sok[0]:
            sx, sy = int(sx[0]), int(sy[0])
            if -SOLEIL_RAYON < sx < W + SOLEIL_RAYON:
                for dy, hw, h, col in self.soleil_bandes:
                    rect(surf, col, (sx - hw, sy + dy, 2 * hw, h))

        # 4) montagnes à l'horizon
        yaw = math.radians(config.yaw)
        poly, ligne = pygame.draw.polygon, pygame.draw.lines
        for az, ha, h in self.montagnes:
            da = (az - yaw + math.pi) % (2 * math.pi) - math.pi
            if abs(da) > 1.25:
                continue
            x = W * 0.5 + math.tan(da) * F
            xl = W * 0.5 + math.tan(da - ha) * F
            xr = W * 0.5 + math.tan(da + ha) * F
            pts = [(int(xl), hy), (int(x - (x - xl) * 0.4), int(hy - h * 0.55)), (int(x), int(hy - h)),
                   (int(x + (xr - x) * 0.45), int(hy - h * 0.6)), (int(xr), hy)]
            poly(surf, MONTAGNE_REMPLISSAGE, pts)
            ligne(surf, MONTAGNE_CONTOUR, False, pts, 1)

        # 5) sol de base (sous l'horizon) + lueur d'horizon
        if hy < H:
            y0 = max(hy, 0)
            rect(surf, config.COULEUR_REMPLISSAGE, (0, y0, W, H - y0))
        rect(surf, HORIZON_LUEUR_2, (0, hy - 5, W, 4))
        rect(surf, HORIZON_LUEUR, (0, hy - 1, W, 3))
