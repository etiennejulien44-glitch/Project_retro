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
JOUEUR_PV_MAX_BASE = 100         # valeur de référence (ne pas modifier en jeu)
JOUEUR_PV_MAX = JOUEUR_PV_MAX_BASE  # valeur courante, recalculée par les boosts
CHARGEUR_TAILLE = 15
MUNITIONS_RESERVE_DEPART = 45
MUNITIONS_RESERVE_MAX = 120
RECHARGE_DUREE = 1.4
CADENCE_TIR = 0.18
DEGATS_TIR = 1
PORTEE_TIR = DIST_AFFICHAGE_MAX

# Butin laissé par les monstres tués
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
# BUTINS / BOOSTS (coffres)
# ---------------------------------------------------------------------------
# Taux (poids relatifs)
POIDS_CS_MUNITIONS   = 40
POIDS_CS_SOIN        = 35
POIDS_CS_VIE_V       = 20
POIDS_CS_VIE_B       = 5

POIDS_PS_VIE_J       = 30
POIDS_PS_VITESSE_J   = 22
POIDS_PS_SAUT_J      = 22
POIDS_PS_DEGATS_J    = 21
POIDS_PS_AUTOREGEN_R = 5

# Force des boosts
FORCE_VIE_V     = 0.03
FORCE_VIE_B     = 0.06
FORCE_VIE_J     = 0.10
FORCE_VITESSE_J = 0.08
FORCE_SAUT_J    = 0.06
FORCE_DEGATS_J  = 0.05
AUTOREGEN_PV    = 1
AUTOREGEN_DELAI = 2.0

# Caps (cumul additif)
CAP_VITESSE = 0.32
CAP_SAUT    = 0.24
CAP_DEGATS  = 0.25


def mettre_a_jour_rayons():
    global COS_YAW, SIN_YAW, COS_PITCH, SIN_PITCH
    rad_yaw = math.radians(yaw)
    rad_pitch = math.radians(pitch)
    COS_YAW = math.cos(rad_yaw)
    SIN_YAW = math.sin(rad_yaw)
    COS_PITCH = math.cos(rad_pitch)
    SIN_PITCH = math.sin(rad_pitch)