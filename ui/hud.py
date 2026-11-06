# hud.py  --  interface néon : PV, munitions, score, arme, game over
import math
import pygame
from data import config

CYAN = (60, 240, 255)
ROSE = (255, 60, 200)
JAUNE = (255, 230, 90)
ROUGE = (255, 50, 90)
BLANC = (255, 255, 255)
SOMBRE = (14, 0, 34)
VIDE = (60, 25, 100)

MUZZLE = (config.LARGEUR // 2 + 40, config.HAUTEUR - 110)


class HUD:
    def __init__(self):
        self.f_petit = pygame.font.Font(None, 26)
        self.f_moyen = pygame.font.Font(None, 40)
        self.f_grand = pygame.font.Font(None, 110)
        self._cache = {}
        self.voile = pygame.Surface((config.LARGEUR, config.HAUTEUR), pygame.SRCALPHA)
        self.voile.fill((10, 0, 25, 175))

    # -- texte (cache) --
    def _texte(self, txt, police, couleur):
        cle = (txt, id(police), couleur)
        img = self._cache.get(cle)
        if img is None:
            if len(self._cache) > 300:
                self._cache.clear()
            img = police.render(txt, True, couleur)
            self._cache[cle] = img
        return img

    def _ecrire(self, surf, txt, police, couleur, x, y, ancre="g"):
        img = self._texte(txt, police, couleur)
        w = img.get_width()
        if ancre == "d":
            x -= w
        elif ancre == "c":
            x -= w // 2
        surf.blit(img, (x, y))

    # -- arme filaire en bas de l'écran --
    def dessiner_arme(self, surf, j, recul):
        oy = recul * 16
        p = j.progression_recharge()
        if p > 0:
            oy += 90 * math.sin(math.pi * p)
        x0, y0 = MUZZLE[0], MUZZLE[1] + oy
        H = config.HAUTEUR
        corps = [(x0 - 16, y0), (x0 + 16, y0), (x0 + 36, H + 4 + oy), (x0 - 36, H + 4 + oy)]
        pygame.draw.polygon(surf, SOMBRE, corps)
        pygame.draw.polygon(surf, CYAN, corps, 2)
        pygame.draw.line(surf, ROSE, (x0 - 26, y0 + 60), (x0 + 26, y0 + 60), 3)
        pygame.draw.line(surf, ROSE, (x0 - 30, y0 + 80), (x0 + 30, y0 + 80), 3)

    # -- bonus permanents (haut droite) --
    def _dessiner_bonus(self, surf, stats):
        if stats is None:
            return
        coul = {"JAUNE": JAUNE, "CYAN": CYAN, "ROSE": ROSE, "BLANC": BLANC}
        lignes = [(t, coul[c]) for t, c in stats.lignes_hud()]
        x = config.LARGEUR - 24
        y = 22
        for txt, col in lignes:
            self._ecrire(surf, txt, self.f_petit, col, x, y, "d")
            y += 26

    # -- HUD principal --
    def dessiner(self, surf, j, temps, stats=None):
        W, H = config.LARGEUR, config.HAUTEUR
        rect, ligne = pygame.draw.rect, pygame.draw.line

        if j.flash_degats > 0:
            k = min(1.0, j.flash_degats / 0.35)
            for i in range(4):
                f = k * (1 - i / 4)
                rect(surf, (int(255 * f), 0, int(90 * f)),
                     (i * 7, i * 7, W - 2 * i * 7, H - 2 * i * 7), 7)

        # réticule
        cx, cy = W // 2, H // 2
        for a, b in (((cx - 12, cy), (cx - 4, cy)), ((cx + 4, cy), (cx + 12, cy)),
                     ((cx, cy - 12), (cx, cy - 4)), ((cx, cy + 4), (cx, cy + 12))):
            ligne(surf, CYAN, a, b, 2)

        # marqueurs hit / kill
        if j.t_kill > 0:
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                ligne(surf, ROSE, (cx + dx * 8, cy + dy * 8),
                      (cx + dx * 20, cy + dy * 20), 3)
        elif j.t_hit > 0:
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                ligne(surf, BLANC, (cx + dx * 8, cy + dy * 8),
                      (cx + dx * 16, cy + dy * 16), 2)

        # --- PV (bas gauche) : lit config.JOUEUR_PV_MAX dynamiquement ---
        x, y = 24, H - 42
        ratio = j.pv / config.JOUEUR_PV_MAX if config.JOUEUR_PV_MAX > 0 else 0.0
        if ratio > 0.5:
            col = CYAN
        elif ratio > 0.25:
            col = JAUNE
        else:
            col = ROSE if math.sin(temps * 12) > 0 else ROUGE
        self._ecrire(surf, "PV", self.f_petit, col, x, y + 2)
        rect(surf, col, (x + 36, y, 204, 20), 2)
        if j.pv > 0:
            rect(surf, col, (x + 40, y + 4, int(196 * ratio), 12))
        self._ecrire(surf, f"{j.pv}/{config.JOUEUR_PV_MAX}", self.f_petit, col, x + 250, y + 2)

        # --- munitions (bas droite) ---
        xd = W - 24
        pip_w, pip_g = 7, 3
        recharge = j.t_recharge > 0
        for i in range(config.CHARGEUR_TAILLE):
            px = xd - (i + 1) * (pip_w + pip_g)
            if i < j.chargeur:
                rect(surf, CYAN, (px, H - 40, pip_w, 20))
            else:
                rect(surf, VIDE, (px, H - 40, pip_w, 20), 1)
        if recharge:
            larg = config.CHARGEUR_TAILLE * (pip_w + pip_g)
            rect(surf, JAUNE, (xd - larg, H - 16, int(larg * j.progression_recharge()), 4))
            self._ecrire(surf, "RECHARGEMENT", self.f_petit, JAUNE, xd, H - 98, "d")
        elif j.chargeur == 0 and j.reserve == 0:
            if math.sin(temps * 10) > 0:
                self._ecrire(surf, "SANS MUNITIONS", self.f_petit, ROSE, xd, H - 98, "d")
        elif j.chargeur == 0 or (j.chargeur <= 3 and j.reserve > 0):
            self._ecrire(surf, "[R] RECHARGER", self.f_petit, JAUNE, xd, H - 98, "d")
        self._ecrire(surf, f"{j.chargeur} / {j.reserve}", self.f_moyen, CYAN, xd, H - 72, "d")

        # --- score (haut gauche) ---
        self._ecrire(surf, f"SCORE  {j.kills * 100}", self.f_moyen, ROSE, 24, 18)

        # --- message temporaire (centre) ---
        if j.t_message > 0:
            self._ecrire(surf, j.message, self.f_moyen, JAUNE, W // 2, H // 2 + 60, "c")

        # --- bonus cumulés (haut droite) ---
        self._dessiner_bonus(surf, stats)

    def dessiner_game_over(self, surf, j, temps):
        W, H = config.LARGEUR, config.HAUTEUR
        surf.blit(self.voile, (0, 0))
        self._ecrire(surf, "GAME OVER", self.f_grand, CYAN, W // 2 + 4, H // 2 - 96, "c")
        self._ecrire(surf, "GAME OVER", self.f_grand, ROSE, W // 2, H // 2 - 100, "c")
        self._ecrire(surf, f"SCORE  {j.kills * 100}   ({j.kills} ennemis)",
                     self.f_moyen, JAUNE, W // 2, H // 2 + 10, "c")
        if math.sin(temps * 4) > -0.3:
            self._ecrire(surf, "[R] REJOUER      [ECHAP] QUITTER",
                         self.f_petit, BLANC, W // 2, H // 2 + 70, "c")

    def dessiner_victoire(self, surf, j, temps, duree):
        W, H = config.LARGEUR, config.HAUTEUR
        surf.blit(self.voile, (0, 0))
        self._ecrire(surf, "SYSTEME PURGE", self.f_grand, CYAN, W // 2 + 4, H // 2 - 116, "c")
        self._ecrire(surf, "SYSTEME PURGE", self.f_grand, JAUNE, W // 2, H // 2 - 120, "c")
        m, sec = int(duree // 60), int(duree % 60)
        self._ecrire(surf, f"RUN TERMINEE  -  {m:02d}:{sec:02d}", self.f_moyen, BLANC, W // 2, H // 2 - 30, "c")
        self._ecrire(surf, f"SCORE  {j.kills * 100 + 1000}   ({j.kills} ennemis)",
                     self.f_moyen, JAUNE, W // 2, H // 2 + 20, "c")
        if math.sin(temps * 4) > -0.3:
            self._ecrire(surf, "[R] NOUVELLE RUN      [ECHAP] QUITTER",
                         self.f_petit, BLANC, W // 2, H // 2 + 80, "c")
