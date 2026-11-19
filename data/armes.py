# data/armes.py
# ============================================================================
#  ARMES.  AJOUTER UNE ARME = UNE entrée dans ARMES. Elle tombera dans les coffres de la table "coffres".
#    nom, taille ("12MB" = poids dans le sac)
#    stats   : degats, cadence (s entre 2 tirs), chargeur, recharge (s), portee   (la rareté multiplie "degats")
#    couleur : couleur de l'arme dans le HUD / la liste d'équipement      couleur_tir : couleur du rayon
#    icone   : nom de l'icône -> assets/<rareté>_<icone>.png (ex: "weapon" -> common_weapon.png, leg_weapon.png...)
#              un tuple donne des noms alternatifs : ("helmet", "helm"). Sans fichier : icône vectorielle.
#    coffres : {table_de_coffre: poids}  -> où elle peut tomber (data/coffres.py) ; absent = ne tombe jamais
# ============================================================================
ARMES = {
    "laser_v1": dict(
        nom="Laser Blaster v1", type="arme", icone="weapon", taille="12MB", couleur=(60, 240, 255), couleur_tir=(60, 240, 255),
        stats=dict(degats=1.0, cadence=0.18, chargeur=15, recharge=1.4, portee=1800)),
    "plasma": dict(
        nom="Plasma Rifle", type="arme", icone="weapon", taille="15MB", couleur=(255, 90, 220), couleur_tir=(255, 70, 190),
        stats=dict(degats=4.0, cadence=0.55, chargeur=6, recharge=2.2, portee=1800),
        coffres={"prismatique": 6, "military": 8}),
    "pulse_smg": dict(
        nom="Pulse SMG", type="arme", icone="weapon", taille="9MB", couleur=(120, 255, 140), couleur_tir=(120, 255, 140),
        stats=dict(degats=0.5, cadence=0.07, chargeur=40, recharge=1.8, portee=1200),
        coffres={"classique": 6, "prismatique": 6, "military": 8}),
}

ARME_DEPART = "laser_v1"

# bornes de la console (terminal : set <arme> <stat> <valeur>) et lien stat -> attribut de config
BORNES_ARMES = {"degats": (0.1, 50.0), "cadence": (0.03, 2.0), "chargeur": (1, 200),
                "recharge": (0.2, 6.0), "portee": (300, 1800)}
STAT_CONFIG_ARME = {"degats": "DEGATS_TIR", "cadence": "CADENCE_TIR", "chargeur": "CHARGEUR_TAILLE",
                    "recharge": "RECHARGE_DUREE", "portee": "PORTEE_TIR"}
