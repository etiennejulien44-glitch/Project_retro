# config.py
import math

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

LARGEUR = 1920
HAUTEUR = 1080
FOCALE = 500.0
DIST_AFFICHAGE_MAX = 1800.0
NEAR = 20.0

COS_YAW = 1.0
SIN_YAW = 0.0
COS_PITCH = 1.0
SIN_PITCH = 0.0

TAILLE_CHUNKS = 20
ECHELLE_GRILLE = 50
EVAL_HAUTEUR = 140

PAS_GRILLE = 2
PORTEE_CHUNKS = 2

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

#rammasage des boostes
RAYON_AIMANT_BUTINS = 200
VITESSE_AIMANT_BUTINS = 900
RAYON_RAMASSAGE_BUTINS = 40

# ---------------------------------------------------------------------------
# BOSS — SPIDER BOSS
# ---------------------------------------------------------------------------
# Apparition
BOSS_SPAWN_KILLS_1       = 15      # premier spawn à ce nombre de kills
BOSS_SPAWN_KILLS_INCREMENT = 25    # kills supplémentaires pour le suivant
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

def mettre_a_jour_rayons():
    global COS_YAW, SIN_YAW, COS_PITCH, SIN_PITCH
    rad_yaw = math.radians(yaw)
    rad_pitch = math.radians(pitch)
    COS_YAW = math.cos(rad_yaw)
    SIN_YAW = math.sin(rad_yaw)
    COS_PITCH = math.cos(rad_pitch)
    SIN_PITCH = math.sin(rad_pitch)