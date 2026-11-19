# main.py -- FENÊTRE et ÉVÉNEMENTS. Rien d'autre.
#   règles du jeu : world/jeu.py   |   affichage : engine/   |   interface : ui/   |   contenu : data/
import gc
import sys
import time

import pygame

from data import config, controles, reglages
from engine.affichage import Affichage
from world.jeu import Jeu

T = controles.TOUCHES


def creer_fenetre():
    """pygame.SCALED : la résolution interne reste fixe, SDL met à l'échelle (plein écran / vsync gratuits)."""
    flags = pygame.RESIZABLE | getattr(pygame, "SCALED", 0)
    if reglages.get("plein_ecran"):
        flags |= pygame.FULLSCREEN
    taille = (config.LARGEUR, config.HAUTEUR)
    try:
        return pygame.display.set_mode(taille, flags, vsync=1 if reglages.get("vsync") else 0)
    except (pygame.error, TypeError):
        try:
            return pygame.display.set_mode(taille, flags)
        except pygame.error:
            return pygame.display.set_mode(taille, pygame.RESIZABLE)


def definir_pause(jeu, pause):
    jeu.pause = pause
    pygame.mouse.set_visible(pause)
    pygame.event.set_grab(not pause)


def lire_entrees():
    k = pygame.key.get_pressed()
    return (k[T["avancer"]] - k[T["reculer"]], k[T["droite"]] - k[T["gauche"]], k[T["saut"]], k[T["sprint"]])


def traiter_evenement(event, jeu, affichage):
    """Traduit UN événement pygame en action. -> False pour quitter."""
    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == T["quitter"]):
        return False
    terminal = affichage.interface.terminal

    if not jeu.pause:
        if event.type == pygame.KEYDOWN and event.key == T["terminal"]:
            definir_pause(jeu, True)
        elif event.type == pygame.MOUSEMOTION:
            jeu.regarder(*event.rel)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == controles.BOUTON_TIR:
            jeu.tirer()
        elif event.type == pygame.KEYDOWN:
            if event.key == T["interagir"]:
                jeu.interagir()
            elif event.key == T["dash"]:
                jeu.dash()
            elif event.key == T["recharger"]:
                jeu.recharger()
            elif event.key in (T["onde_vectorielle"], T["corruption_virulente"], T["ultime"]):
                jeu.competence(next(a for a in ("onde_vectorielle", "corruption_virulente", "ultime") if T[a] == event.key))
            elif event.key == T["debug"]:
                affichage.interface.debug = not affichage.interface.debug
            elif event.key == T["plein_ecran"]:
                reglages.definir("plein_ecran", not reglages.get("plein_ecran"))
            elif event.key == T["valider"]:
                jeu.recommencer_si_fini()
    elif terminal.handle_event(event) == "CLOSE_TERMINAL":
        definir_pause(jeu, False)
    return True


def main():
    pygame.init()
    fenetre = creer_fenetre()
    pygame.display.set_caption("FPS Rétro Synthwave")
    horloge = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)

    jeu = Jeu()
    affichage = Affichage(fenetre, jeu)

    def recreer_fenetre(_valeur=None):
        affichage.nouvelle_surface(creer_fenetre())

    # options appliquées en direct (terminal : cd option ; set <nom> <valeur>)
    reglages.sur_changement("distance", lambda v: affichage.appliquer_distance())
    reglages.sur_changement("qualite", lambda v: affichage.appliquer_distance())
    reglages.sur_changement("vsync", recreer_fenetre)
    reglages.sur_changement("plein_ecran", recreer_fenetre)
    affichage.appliquer_distance()

    gc.collect()                      # ramasse-miettes : objets de démarrage figés, passes espacées (moins de saccades)
    gc.freeze()
    gc.set_threshold(20000, 20, 20)

    en_cours, chrono_titre = True, 0.0
    while en_cours:
        t0 = time.perf_counter()
        dt = min(horloge.get_time() / 1000.0, 0.05) or 1.0 / 60.0
        temps = pygame.time.get_ticks() / 1000.0

        for event in pygame.event.get():
            en_cours = traiter_evenement(event, jeu, affichage) and en_cours

        if not jeu.pause:
            jeu.mettre_a_jour(dt, temps, *lire_entrees())
        affichage.dessiner(temps)

        t_travail = time.perf_counter() - t0          # CPU réellement utilisé (hors attente vsync / limiteur)
        pygame.display.flip()
        fps_max = reglages.get("fps_max")
        horloge.tick(fps_max)                          # 0 = illimité
        affichage.adapter_qualite(horloge.get_time() / 1000.0, t_travail, fps_max)

        chrono_titre += dt
        if chrono_titre >= 0.5:
            chrono_titre = 0.0
            pygame.display.set_caption(f"FPS Rétro Synthwave - {horloge.get_fps():.0f} FPS")

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
