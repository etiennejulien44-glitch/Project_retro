# ui/interface.py -- TOUTE l'interface par-dessus la scène 3D : HUD, panneau d'équipement (droite), barre de boss,
#   messages, invite d'interaction, debug (F3) et terminal.  Texte à liseré sombre : AUCUN fond noir.
import math
import pygame
from data import config, reglages
from engine import effets
from engine.qualite import qualite
from engine.textes import ecrire, texte
from ui.barre_competences import BarreCompetences
from ui.hud import HUD
from ui.panneau_equipement import PanneauEquipement
from ui.terminal import TerminalInventory
from world import inventaire
from world import boss as boss_module
from world import coffre, competences


class Interface:
    def __init__(self, jeu):
        k = config.HAUTEUR / 1080.0
        self.k = k
        self.hud = HUD()
        self.panneau = PanneauEquipement()
        self.competences = BarreCompetences()
        self.terminal = TerminalInventory()
        self.terminal.jeu = jeu
        self.debug = False
        self.nb_items = 0                     # renseigné par engine/affichage.py (stats F3)
        self.t_popup, self.t_invite = max(28, int(56 * k)), max(20, int(36 * k))

    # -- terminal --------------------------------------------------------------
    def dessiner_terminal(self, surf):
        self.terminal.dessiner(surf)

    # -- par-dessus la scène ------------------------------------------------------
    def dessiner(self, surf, jeu, temps):
        j = jeu.joueur
        if not j.mort:
            if jeu.tir_t > 0:                                   # éclair du tir
                from ui.hud import MUZZLE, CYAN, BLANC
                fin = jeu.tir_fin or (config.LARGEUR // 2, config.HAUTEUR // 2)
                arme = inventaire.definition(inventaire.possedees.get(inventaire.equipees["arme"]))
                c = arme.get("couleur_tir", CYAN)
                pygame.draw.line(surf, tuple(int(v * 0.5) for v in c), MUZZLE, fin, 7)
                pygame.draw.line(surf, c, MUZZLE, fin, 3)
                pygame.draw.line(surf, BLANC, MUZZLE, fin, 1)
                pygame.draw.circle(surf, BLANC, MUZZLE, 10)
                pygame.draw.circle(surf, c, MUZZLE, 20, 2)
            self.hud.dessiner_arme(surf, j, jeu.tir_t / 0.10)

        info_boss = None
        if boss_module.boss is None and not boss_module.run_gagnee:
            info_boss = f"PROCHAIN BOSS : {boss_module.prochain_seuil}"
        self.hud.dessiner(surf, j, temps, jeu.stats, info_boss)
        self.panneau.dessiner(surf, jeu, temps)
        self.competences.dessiner(surf, jeu, temps)
        self.barre_boss(surf, temps)

        if jeu.stats.messages_ramassage:
            txt, couleur = jeu.stats.messages_ramassage[-1]
            jeu.stats.messages_ramassage.clear()
            jeu.annoncer(txt, couleur, 2.5)

        if not j.mort and not boss_module.run_gagnee:
            cible = jeu.cible_interaction()
            if cible is not None:
                ecrire(surf, f"[F]  {cible[2]}", self.t_invite, cible[3], config.LARGEUR // 2,
                       config.HAUTEUR // 2 + 110, "c")

        if jeu.popup_timer > 0 and jeu.popup_text:
            img = texte(jeu.popup_text, self.t_popup, jeu.popup_color, True)
            img.set_alpha(int(255 * min(1.0, jeu.popup_timer / 0.4)))
            surf.blit(img, (config.LARGEUR // 2 - img.get_width() // 2,
                            config.HAUTEUR - int(260 * self.k) - img.get_height() // 2))
            img.set_alpha(255)

        if self.debug:
            self.debug_stats(surf, jeu)

        if j.mort:
            self.hud.dessiner_game_over(surf, j, temps)
        elif boss_module.run_gagnee:
            self.hud.dessiner_victoire(surf, j, temps, jeu.temps_run)

    # -- barre de boss (cadre néon, sans fond noir) ---------------------------------
    def barre_boss(self, surf, temps):
        b = boss_module.boss
        if b is None:
            return
        if b.en_spawn:
            frac = min(1.0, max(0.0, 1.0 - max(0.0, b.t_spawn) / config.BOSS_SPAWN_ANIM_DUREE))
        else:
            frac = b.hp / b.hp_max if b.hp_max > 0 else 0.0
        largeur, hauteur = int(config.LARGEUR * 0.46), max(22, int(40 * self.k))
        x0, y0 = (config.LARGEUR - largeur) // 2 - int(60 * self.k), int(40 * self.k)
        puls = 0.6 + 0.4 * math.sin(temps * 6)
        rempli = int((largeur - 6) * frac)
        if rempli > 0:
            if b.en_spawn:
                col = (int(255 * (0.3 + 0.7 * frac)), int(80 * frac), int(80 * frac))
            else:
                inten = 0.5 + 0.5 * (1 - (b.hp / b.hp_max if b.hp_max > 0 else 0))
                col = (int(255 * inten), int(50 * puls), int(50 * puls))
            pygame.draw.rect(surf, col, (x0 + 3, y0 + 3, rempli, hauteur - 6))
        pygame.draw.rect(surf, (int(255 * puls), 50, 70), (x0, y0, largeur, hauteur), 3)
        for i in range(1, 10):
            sx = x0 + 3 + (largeur - 6) * i // 10
            pygame.draw.line(surf, (20, 0, 30), (sx, y0 + 4), (sx, y0 + hauteur - 4), 2)
        ecrire(surf, f"{b.nom}  -  NIVEAU {b.niveau + 1}", max(20, int(40 * self.k)), (255, 210, 210),
               x0 + largeur // 2, y0 + hauteur + 6, "c")
        if b.en_spawn and int(temps * 8) % 2 == 0:
            ecrire(surf, "DANGER", max(40, int(96 * self.k)), (255, 40, 40), config.LARGEUR // 2,
                   config.HAUTEUR // 2 - 120, "c")

    # -- debug F3 (texte seul) ------------------------------------------------------
    def debug_stats(self, surf, jeu):
        j, s, q = jeu.joueur, jeu.stats, qualite.profil()
        arme = inventaire.possedees.get(inventaire.equipees["arme"], {})
        lignes = [
            f"Score {j.score}   Kills {j.kills}   PV {j.pv}/{config.JOUEUR_PV_MAX}",
            f"Arme {arme.get('nom', '-')} dgt {config.DEGATS_TIR:.2f}   Armure -{int(config.REDUCTION_DEGATS * 100)}%",
            f"Vitesse x{s.vitesse_mult:.2f}   Saut x{s.saut_mult:.2f}   Dégâts x{s.degats_mult:.2f}",
            f"Qualité {reglages.get('qualite')} ({q.nom})   dist {int(config.DIST_AFFICHAGE_MAX)}   "
            f"chunks {2 * config.PORTEE_CHUNKS + 1}²",
            f"Particules {effets.particules.n}   items/frame {self.nb_items}",
        ]
        lignes.append(f"PC {competences.points}   ultime : {competences.ultime or '-'}   vitesse réelle {jeu.vitesse_reelle:.0f}")
        y = config.HAUTEUR - int(120 * self.k) - len(lignes) * 22
        for i, l in enumerate(lignes):
            ecrire(surf, l, 22, (200, 255, 200), 24, y + i * 22)
