# data/armures.py
# ============================================================================
#  ARMURES (1 pièce par slot).  AJOUTER UNE ARMURE = UNE entrée dans ARMURES.
#    type            : slot = "casque" | "torse" | "jambieres" | "bottes" | "ram"
#    nom, taille     : affichage / poids dans le sac ("12MB")
#    couleur         : couleur de l'icône vectorielle (secours)
#    icone           : assets/<rareté>_<icone>.png ; tuple = noms alternatifs (le casque légendaire s'appelle leg_helm.png)
#    stat_principale : (stat, min, max)   -> toujours présente, tirée dans [min,max] puis x multiplicateur de rareté
#    substats_possibles : [(stat, min, max)]  -> 1 tirée au hasard (toutes si rareté "special")
#    coffres         : {table_de_coffre: poids}  -> où elle peut tomber (data/coffres.py)
#  Les stats disponibles sont celles de data/stats.py.
# ============================================================================
_COFFRES_ARMURE = {"classique": 4, "prismatique": 8, "military": 10}

ARMURES = {
    "helmet": dict(
        nom="Casque Système", type="casque", icone=("helmet", "helm"), taille="12MB", couleur=(60, 240, 255), coffres=_COFFRES_ARMURE,
        stat_principale=("reduction_dmgs", 0.03, 0.25),
        substats_possibles=[("auto_regen", 1.0, 5.0), ("auto_aim", 0.50, 1.00)]),
    "chestplate": dict(
        nom="Plastron Pare-Feu", type="torse", icone="chestplate", taille="20MB", couleur=(255, 90, 220), coffres=_COFFRES_ARMURE,
        stat_principale=("augmentation_hp", 10.0, 75.0),
        substats_possibles=[("hit_speed", 0.10, 0.50), ("dash_atq", 1.0, 3.0)]),
    "leggings": dict(
        nom="Jambières Bus Données", type="jambieres", icone="leggins", taille="18MB", couleur=(255, 200, 60), coffres=_COFFRES_ARMURE,
        stat_principale=("reduction_dmgs", 0.05, 0.40),
        substats_possibles=[("mult_damage", 0.10, 0.40), ("zap_chaine", 3.0, 10.0)]),
    "boots": dict(
        nom="Bottes Super-Cadence", type="bottes", icone="boots", taille="10MB", couleur=(120, 255, 140), coffres=_COFFRES_ARMURE,
        stat_principale=("vitesse", 0.10, 0.30),
        substats_possibles=[("all_stats", 5.0, 50.0), ("sprint_mult_dmg", 0.20, 0.60)]),
    "ram_ext": dict(
        nom="Extension RAM", type="ram", icone="ram_ext", taille="5MB", couleur=(190, 120, 255),
        coffres={"classique": 3, "prismatique": 6, "military": 8},
        stat_principale=("poids_max_buff", 0.01, 1.00),
        substats_possibles=[("buff_passif_sac", 0.05, 0.25)]),
}

SLOTS_ARMURE = ("casque", "torse", "jambieres", "bottes", "ram")
