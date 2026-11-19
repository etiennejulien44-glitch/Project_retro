# data/controles.py -- TOUCHES et réglages de la souris (modifiables ici, rien d'autre à toucher)
import pygame

TOUCHES = {
    "avancer": pygame.K_z, "reculer": pygame.K_s, "gauche": pygame.K_q, "droite": pygame.K_d,
    "saut": pygame.K_SPACE, "sprint": pygame.K_LSHIFT,
    "interagir": pygame.K_f, "dash": pygame.K_a, "recharger": pygame.K_r,
    # compétences (data/competences.py -> champ "touche") ; "ultime" = l'ultime équipé
    "onde_vectorielle": pygame.K_e, "corruption_virulente": pygame.K_c, "ultime": pygame.K_v,
    "terminal": pygame.K_TAB, "debug": pygame.K_F3, "plein_ecran": getattr(pygame, "K_F11", 1073741892),
    "valider": pygame.K_RETURN, "quitter": pygame.K_ESCAPE,
}
BOUTON_TIR = 1
SENSIBILITE_SOURIS = 0.2
