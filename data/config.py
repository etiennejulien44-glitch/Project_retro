# config.py
import math
from data import reglages

# ---------------------------------------------------------------------------
# Caméra / écran
# ---------------------------------------------------------------------------
DEPART_X = 0.0
DEPART_Z = -500.0

cam_x = DEPART_X
cam_y = 0.0
cam_z = DEPART_Z
yaw = 0.0
pitch = 0.0
vitesse_y = 0.0
gravite = 600.0

# Résolution INTERNE du rendu (option "resolution", appliquée au lancement). La fenêtre est mise à
# l'échelle par SDL (pygame.SCALED) : baisser la résolution = gros gain de FPS sans toucher au gameplay.
LARGEUR, HAUTEUR = (int(v) for v in reglages.get("resolution").split("x"))
FOCALE_BASE = 500.0 * HAUTEUR / 1080.0     # la focale suit la hauteur : même champ de vision à toute résolution
FOCALE = FOCALE_BASE                       # modulée en direct par engine/effets.FovDynamique
DIST_AFFICHAGE_MAX = float(reglages.get("distance"))
NEAR = 20.0

COS_YAW = 1.0
SIN_YAW = 0.0
COS_PITCH = 1.0
SIN_PITCH = 0.0

TAILLE_CHUNKS = 20
ECHELLE_GRILLE = 50
EVAL_HAUTEUR = 140

PAS_GRILLE = 2
PORTEE_CHUNKS = max(1, math.ceil(DIST_AFFICHAGE_MAX / (TAILLE_CHUNKS * ECHELLE_GRILLE)))


def appliquer_distance(distance):
    """Change la distance d'affichage en direct (option "distance" / qualité auto).
    Moins de distance => moins de chunks à générer/projeter/trier => plus de FPS."""
    global DIST_AFFICHAGE_MAX, PORTEE_TIR, PORTEE_CHUNKS
    DIST_AFFICHAGE_MAX = float(max(600.0, distance))
    PORTEE_TIR = DIST_AFFICHAGE_MAX
    PORTEE_CHUNKS = max(1, math.ceil(DIST_AFFICHAGE_MAX / (TAILLE_CHUNKS * ECHELLE_GRILLE)))

# ---------------------------------------------------------------------------
# COULEURS SYNTHWAVE
# ---------------------------------------------------------------------------
COULEUR_FOND = (8, 0, 28)
COULEUR_REMPLISSAGE = (14, 0, 34)

FOG_STEPS = 16
TERRAIN_PROCHE = (255, 55, 200)
TERRAIN_LOIN = (34, 4, 70)

# ---------------------------------------------------------------------------
# GAMEPLAY : joueur & armes
# ---------------------------------------------------------------------------
JOUEUR_PV_MAX_BASE = 100
JOUEUR_PV_MAX = JOUEUR_PV_MAX_BASE
CHARGEUR_TAILLE = 15
MUNITIONS_RESERVE_DEPART = 45
MUNITIONS_RESERVE_MAX = 120
RECHARGE_DUREE = 1.4
CADENCE_TIR = 0.18
DEGATS_TIR = 1
PORTEE_TIR = DIST_AFFICHAGE_MAX

PACK_MUNITIONS = 15
PACK_SOIN = 25
DROP_MUNITIONS = 0.45
DROP_SOIN = 0.20
RAYON_RAMASSAGE = 70

# ---------------------------------------------------------------------------
# GAMEPLAY : ennemis
# ---------------------------------------------------------------------------
ZONE_SECURITE_DEPART = 800

ARAIGNEE_PV = 3
ARAIGNEE_VITESSE = 150
ARAIGNEE_AGGRO = 1000
ARAIGNEE_PORTEE = 75
ARAIGNEE_DEGATS = 10
ARAIGNEE_COOLDOWN = 0.9

DRONE_PV = 2
DRONE_VITESSE = 120
DRONE_AGGRO = 1200
DRONE_DIST_PREF = 550
DRONE_PORTEE_TIR = 1000
DRONE_COOLDOWN = 2.2
PROJECTILE_VITESSE = 420
PROJECTILE_DEGATS = 8
PROJECTILE_VIE = 4.0
PROJECTILE_RAYON = 40

# ---------------------------------------------------------------------------
# BUTINS / BOOSTS
# ---------------------------------------------------------------------------
POIDS_CS_MUNITIONS   = 40
POIDS_CS_SOIN        = 35
POIDS_CS_VIE_V       = 20
POIDS_CS_VIE_B       = 5

POIDS_PS_VIE_J       = 30
POIDS_PS_VITESSE_J   = 22
POIDS_PS_SAUT_J      = 22
POIDS_PS_DEGATS_J    = 21
POIDS_PS_AUTOREGEN_R = 5

FORCE_VIE_V     = 0.10       # +10% au lieu de 3%
FORCE_VIE_B     = 0.20       # +20%
FORCE_VIE_J     = 0.35       # +35%
FORCE_VITESSE_J = 0.15       # +15%
FORCE_SAUT_J    = 0.12       # +12%
FORCE_DEGATS_J  = 0.25       # +25%  ← 4 boosts suffisent pour passer de 1 à 2 dégâts
AUTOREGEN_PV    = 1
AUTOREGEN_DELAI = 2.0

CAP_VITESSE = 2           # laisse 3 boosts avant plafond
CAP_SAUT    = 0.36
CAP_DEGATS  = 0.75 

# Ramassage : touche F (plus d'aimant). RAMASSAGE_AUTO = True -> ramassage au contact, sans touche.
RAMASSAGE_AUTO = False
RAYON_RAMASSAGE_BUTINS = 40      # distance de contact (mode auto)
RAYON_INTERACTION = 160          # distance max pour ramasser / ouvrir un coffre avec F

# ---------------------------------------------------------------------------
# BOSS — SPIDER BOSS
# ---------------------------------------------------------------------------
# Apparition
# Les boss normaux apparaissent à des PALIERS DE SCORE -> voir data/boss.py (PALIERS)
BOSS_SCORE_BONUS        = 1000     # score gagné en tuant un boss
SATELLITE_SCORE         = 50       # score d'une tourelle satellite détruite
BOSS_ECHELLE_MODELE     = 4.0      # échelle du modèle Spider Boss
BOSS_ONDE_EPAISSEUR     = 45       # demi-épaisseur d'une onde néon (zone qui blesse)
BOSS_ONDE_SAUT_MIN      = 45       # hauteur de saut (unités) qui permet de passer par-dessus une onde
BOSS_FINAL_PV_MULT      = 2.0     # boss final = spider boss x2 PV
BOSS_SPAWN_DISTANCE      = 700     # distance de spawn (unités monde)
BOSS_SPAWN_ANIM_DUREE    = 2.0     # durée de la barre qui se remplit
BOSS_HAUTEUR_CENTRE      = 100     # hauteur du centre du boss (visée)
BOSS_OFFSET_MODELE       = -60     # offset vertical du modèle (à ajuster)

# Stats de base (niveau 0)
BOSS_PV               = 300
BOSS_VITESSE          = 180
BOSS_DEGATS_CONTACT   = 20
BOSS_AGGRO            = 2500
BOSS_PORTEE_CONTACT   = 120

# Scaling à chaque respawn
BOSS_PV_MULT          = 1.50
BOSS_VITESSE_MULT     = 1.15
BOSS_DEGATS_MULT      = 1.30

# Pattern CHARGE (dès phase 1)
BOSS_COOLDOWN_CHARGE     = 3.5
BOSS_CHARGE_DUREE        = 1.2
BOSS_CHARGE_VITESSE_MULT = 3.0
BOSS_COOLDOWN_CONTACT    = 1.0

# Pattern SAUT AOE (phase 2)
BOSS_COOLDOWN_SAUT    = 5.0
BOSS_SAUT_DUREE       = 1.0
BOSS_SAUT_HAUTEUR     = 300
BOSS_SAUT_RAYON_AOE   = 200
BOSS_SAUT_DEGATS_AOE  = 25

# Pattern RAFALE (phase 3)
BOSS_COOLDOWN_RAFALE      = 4.0
BOSS_RAFALE_NB_PROJ       = 5
BOSS_RAFALE_ANGLE         = 45      # degrés d'éventail
BOSS_PROJECTILE_VITESSE   = 380
BOSS_PROJECTILE_DEGATS    = 12
BOSS_PROJECTILE_VIE       = 5.0

# Seuils de phase (fraction HP)
BOSS_PHASE_2 = 0.66
BOSS_PHASE_3 = 0.33

# Drop
BOSS_NB_DROPS     = 2
BOSS_DROPS_POOL   = ["VIE_J", "VITESSE_J", "SAUT_J", "DEGATS_J", "AUTO_REGEN_R"]

# ---------------------------------------------------------------------------
# ÉQUIPEMENTS (armures, poids transportable, effets) -- recalculés par world/inventaire.appliquer_config()
# ---------------------------------------------------------------------------
POIDS_MAX_BASE_MB = 100         # poids max transportable sans RAM (chaque objet pèse 5 à 20 MB)

# Valeurs actives (ne pas modifier ici : écrasées à chaque changement d'équipement)
REDUCTION_DEGATS = 0.0
BONUS_HP = 0.0
BONUS_VITESSE = 0.0
BONUS_DEGATS_BASE = 0.0
BONUS_CADENCE = 0.0
GRAVITE_MULT = 1.0              # modifié par la compétence Propagation létale
BUFF_POIDS_MAX = 0.0
REGEN_EQUIP = 0.0
AUTO_AIM = 0.0
MULT_DEGATS_EQUIP = 0.0
BONUS_DEGATS_SPRINT = 0.0
ZAP_NB = 0
DASH_CELLULES = 0.0

# Réglages des effets
REDUCTION_MAX = 0.80            # plafond de réduction de dégâts cumulée
SPRINT_MULT = 1.5               # LSHIFT : vitesse x1.5
AUTO_AIM_RAYON = 2.0            # rayon de touche x(1 + AUTO_AIM * AUTO_AIM_RAYON) pour une aide à 100%
ZAP_PORTEE = 650                # distance max d'un éclair autour de la cible
ZAP_BONUS_DEGATS = 0.10         # un éclair inflige dégâts x1.10
DASH_COOLDOWN = 30.0
DASH_UNITES_PAR_CELLULE = 150   # 1 cellule de dash = 150 unités (le joueur court à 250/s)
DASH_RAYON = 110                # largeur de la zone touchée le long du dash
DASH_DEGATS_MIN = 1.5           # dash 1 cellule  -> 150% des dégâts
DASH_DEGATS_MAX = 3.0           # dash 3 cellules -> 300% des dégâts

# "all_stats" (+N points partout) : N est converti ainsi
ALL_STATS_HP = 1.0              # +1 PV par point
ALL_STATS_DEGATS = 0.01         # +1% dégâts de base par point
ALL_STATS_REDUCTION = 0.005     # +0.5% réduction par point
ALL_STATS_VITESSE = 0.005       # +0.5% vitesse par point

def mettre_a_jour_rayons():
    global COS_YAW, SIN_YAW, COS_PITCH, SIN_PITCH
    rad_yaw = math.radians(yaw)
    rad_pitch = math.radians(pitch)
    COS_YAW = math.cos(rad_yaw)
    SIN_YAW = math.sin(rad_yaw)
    COS_PITCH = math.cos(rad_pitch)
    SIN_PITCH = math.sin(rad_pitch)

# ---------------------------------------------------------------------------
# GAME JUICE (engine/effets.py)
# ---------------------------------------------------------------------------
FOV_DASH_BOOST = 0.30        # +30% de focale au pic d'un dash (étire la perspective). Négatif = effet inverse
FOV_DASH_DUREE = 0.55        # durée de l'impulsion (s)
FOV_SPRINT_BOOST = 0.06      # +6% de focale en sprint
FOV_LISSAGE = 9.0            # vitesse de rattrapage vers la valeur cible

GRAVITE_PARTICULES = 520.0   # (Y vers le bas)
ONDE_TIR_AMP = 7.0           # amplitude (unités) de l'ondulation de grille à l'impact d'un tir
ONDE_MORT_AMP = 28.0         # ... à la mort d'un ennemi
ONDE_DASH_AMP = 22.0         # ... à l'arrivée d'un dash
