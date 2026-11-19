# data/monstres.py
# ============================================================================
#  UN MONSTRE = UN BLOC  monstre("cle", ...)  ci-dessous.  C'est TOUT : modèle, stats, comportement,
#  score, et OÙ IL APPARAÎT (champ `biomes`). Aucun autre fichier à modifier.
#
#  Champs obligatoires : nom, comportement, couleur, pv_max   (+ modele pour le rendu "segments")
#  Tout le reste a une valeur par défaut (voir DEFAUTS_COMMUNS et DEFAUTS_COMPORTEMENT plus bas).
#
#    comportement : melee | distance | striker | shield | phasme      (IA : world/entity.py, @comportement)
#    rendu        : segments (défaut, modèle fil de fer) | rayon | shield | phasme   (engine/rendu_monstres.py)
#    modele       : liste de segments ((x,y,z),(x,y,z)) -- écrite ici, ou assemblée avec les outils de
#                   data/modeles.py :  pointe() octaedre() boite() cube() icosaedre() decaler()   (y négatif = haut)
#    biomes       : {"id_biome": poids}  -> apparaît dans ces biomes (poids relatif)
#    score        : points à la mort (aussi les paliers de boss, data/boss.py)
#    hauteur_barre / hauteur_centre / rayon_visee : déduits de la taille du modèle si absents
# ============================================================================
from data import modeles as M

MONSTRES = {}

DEFAUTS_COMMUNS = dict(
    rendu=None, modele=None, echelle=1.0, decal_y=0.0, anim_freq=0.0, anim_amp=0.0,
    score=100, rayon_visee=40.0, biomes={},
)

# Paramètres par défaut de chaque comportement : un monstre n'indique que ce qui change.
DEFAUTS_COMPORTEMENT = {
    "melee":    dict(vitesse=80, portee=3.5, aggro=120.0, degats=10, cooldown=1.2),
    "distance": dict(vitesse=80, portee_tir=150.0, dist_pref=80.0, aggro=140.0, degats=5, cooldown=2.0),
    "striker":  dict(aggro=1000.0, duree_vise=0.85, verrou=0.22, vitesse_charge=1150.0, duree_charge=1.0,
                     rayon_contact=48.0, degats=14, cooldown=1.6,
                     longueur_repos=36.0, longueur_vise=170.0, longueur_charge=300.0),
    "shield":   dict(nb_faces=6, rayon_faces=34.0, y_bas=-4.0, y_haut=-62.0, aggro=900.0, vitesse=55.0,
                     portee=95.0, vit_rot=0.75, degats=12, cooldown=1.5),
    "phasme":   dict(etats_ciblables=("surgit", "surgi"), distorsion={"amp": 38.0, "sigma": 105.0},
                     aggro=1100.0, vitesse=170.0, bonus_proche=1.9, dist_rush=420.0, dist_surgir=150.0,
                     duree_surgit=0.30, duree_expose=2.0, duree_plonge=0.45, portee_attaque=125.0,
                     degats=16, cooldown=1.3, cooldown_attaque=0.9),
}
RENDU_PAR_COMPORTEMENT = {"striker": "rayon", "shield": "shield", "phasme": "phasme"}
REQUIS = ("nom", "comportement", "couleur", "pv_max")
RENDUS_CONNUS = ("segments", "rayon", "shield", "phasme")


def monstre(cle, **champs):
    """Déclare un monstre : applique les défauts, déduit ce qui peut l'être, valide, enregistre."""
    for r in REQUIS:
        if r not in champs:
            raise ValueError(f"data/monstres.py -> '{cle}' : champ obligatoire manquant : '{r}'")
    comp = champs["comportement"]
    if comp not in DEFAUTS_COMPORTEMENT:
        raise ValueError(f"data/monstres.py -> '{cle}' : comportement inconnu '{comp}' "
                         f"(connus : {', '.join(DEFAUTS_COMPORTEMENT)})")
    d = {**DEFAUTS_COMMUNS, **DEFAUTS_COMPORTEMENT[comp], **champs}
    d["rendu"] = d["rendu"] or RENDU_PAR_COMPORTEMENT.get(comp, "segments")
    if d["rendu"] not in RENDUS_CONNUS:
        raise ValueError(f"data/monstres.py -> '{cle}' : rendu inconnu '{d['rendu']}' ({', '.join(RENDUS_CONNUS)})")
    if d["rendu"] == "segments" and not d["modele"]:
        raise ValueError(f"data/monstres.py -> '{cle}' : le rendu 'segments' demande un 'modele'")
    h = M.hauteur_modele(d["modele"]) * d["echelle"] if d["modele"] else 40.0
    if comp == "shield":
        h = -d["y_haut"]
    d.setdefault("hauteur_barre", int(h + 14))
    d.setdefault("hauteur_centre", -h / 2.0)
    MONSTRES[cle] = d
    return d


# ---------------------------------------------------------------------------
#  CATALOGUE
# ---------------------------------------------------------------------------
monstre("araignee", nom="Araignée Corps-à-Corps", comportement="melee",
        modele=M.MODELE_ARAIGNEE, couleur=(255, 130, 30), anim_freq=12.0, anim_amp=6.0,
        pv_max=30, vitesse=4.5, portee=3.5, aggro=120.0, degats=10, cooldown=1.2,
        hauteur_barre=42, hauteur_centre=-15, score=100,
        biomes={"neon_grid": 2, "glitch_zone": 1, "cyber_wasteland": 0, "overclock_zone": 2})

monstre("drone", nom="Drone à Distance", comportement="distance",
        modele=M.MODELE_DRONE, couleur=(255, 235, 70), decal_y=-40.0, anim_freq=6.0, anim_amp=15.0,
        pv_max=20, vitesse=6.0, portee_tir=150.0, dist_pref=80.0, aggro=140.0, degats=5, cooldown=2.0,
        hauteur_barre=98, hauteur_centre=-65, score=100,
        biomes={"neon_grid": 1, "cyber_wasteland": 1, "glitch_zone": 1, "overclock_zone": 1, "silent_void": 1})

# vitesse 0 = reste en place : cache-toi derrière un couvert !
monstre("tourelle", nom="Tourelle Sentinelle", comportement="distance",
        modele=M.MODELE_TOURELLE, couleur=(255, 60, 60), anim_freq=3.0,
        pv_max=40, vitesse=0.0, portee_tir=700.0, dist_pref=300.0, aggro=750.0, degats=8, cooldown=1.6,
        hauteur_barre=60, hauteur_centre=-20, score=150,
        biomes={"cyber_wasteland": 1, "overclock_zone": 1, "silent_void": 1})

monstre("glitch", nom="Entité Glitch", comportement="melee",
        modele=M.MODELE_GLITCH, couleur=(230, 90, 255), anim_freq=25.0, anim_amp=4.0,
        pv_max=15, vitesse=9.0, portee=3.5, aggro=150.0, degats=6, cooldown=0.8,
        hauteur_barre=40, hauteur_centre=-12, score=100,
        biomes={"glitch_zone": 2, "silent_void": 1})

# Striker : AUCUN volume 3D, un simple rayon d'énergie qui fonce en ligne droite. Se verrouille 0.22 s avant de partir.
monstre("striker", nom="Striker (Ligne Électrique)", comportement="striker",
        couleur=(60, 240, 255), pv_max=4, score=120, rayon_visee=34,
        decal_y=-26.0, hauteur_barre=46, hauteur_centre=-26,
        biomes={"neon_grid": 1, "cyber_wasteland": 1, "glitch_zone": 1, "silent_void": 1})

# Polygone Shield : chaque tir détruit une face ; il pivote lentement -> tourner autour pour toucher le coeur.
# pv_max = PV du COEUR.
monstre("polygone_shield", nom="Polygone Shield", comportement="shield",
        couleur=(255, 200, 40), pv_max=8, score=250, rayon_visee=62, hauteur_barre=78, hauteur_centre=-32,
        biomes={"cyber_wasteland": 1, "overclock_zone": 1, "silent_void": 1})

# Phasme : voyage sous la grille (invulnérable), surgit au dernier moment. Le modèle ci-dessous est SA forme sortie.
monstre("phasme", nom="Phasme (Traqueur de Grille)", comportement="phasme",
        modele=M.pointe(22, 70, anneaux=1) + M.decaler(M.pointe(14, 46), -22, 0, 6) + M.decaler(M.pointe(14, 40), 20, 0, -8),
        couleur=(255, 70, 200), pv_max=10, score=200, rayon_visee=46, hauteur_barre=90, hauteur_centre=-35,
        biomes={"glitch_zone": 1, "overclock_zone": 1, "silent_void": 1})

# Pour ajouter un monstre : copie un bloc ci-dessus, change les valeurs, indique ses `biomes`. C'est fini.

BESTIAIRE = MONSTRES      # ancien nom (compatibilité)
