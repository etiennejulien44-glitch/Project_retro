# data/stats.py
# ============================================================================
#  CATALOGUE DES STATS D'ÉQUIPEMENT.  AJOUTER UNE STAT = UNE entrée ici, puis l'utiliser dans une armure.
#    label     : nom affiché (HUD, terminal)
#    fmt       : "pct" (+12%) | "plus" (+12) | "mult" (x1.12) | "int" (7) | "par_s" (+2.0/s) | "cellules" (2.0 cellules)
#    cible     : attribut de data/config.py qui reçoit le TOTAL des pièces équipées (None = stat purement passive)
#    cap       : plafond (nombre, ou nom d'un attribut de config)       entier : arrondi à l'entier
#    all_stats : nom de l'attribut de config donnant ce que vaut 1 point de la stat "all_stats" pour celle-ci
#  La logique est dans world/inventaire.py (appliquer_config) : rien à y modifier pour une stat standard.
# ============================================================================
STATS = {
    "reduction_dmgs":  dict(label="Réduction dégâts", fmt="pct",  cible="REDUCTION_DEGATS", cap="REDUCTION_MAX", all_stats="ALL_STATS_REDUCTION"),
    "augmentation_hp": dict(label="PV max",           fmt="plus", cible="BONUS_HP",         all_stats="ALL_STATS_HP"),
    "vitesse":         dict(label="Vitesse",          fmt="pct",  cible="BONUS_VITESSE",    all_stats="ALL_STATS_VITESSE"),
    "poids_max_buff":  dict(label="Poids max",        fmt="pct",  cible="BUFF_POIDS_MAX"),
    "auto_regen":      dict(label="Régénération",     fmt="par_s", cible="REGEN_EQUIP"),
    "auto_aim":        dict(label="Aide à la visée",  fmt="pct",  cible="AUTO_AIM", cap=1.0),
    "hit_speed":       dict(label="Cadence de tir",   fmt="pct",  cible="BONUS_CADENCE"),
    "dash_atq":        dict(label="Niveaux de Dash",  fmt="plus", cible="DASH_CELLULES", entier=True),   # niveaux GRATUITS de la compétence dash
    "mult_damage":     dict(label="Dégâts",           fmt="pct",  cible="MULT_DEGATS_EQUIP"),
    "zap_chaine":      dict(label="Éclairs en chaîne", fmt="int", cible="ZAP_NB", entier=True),
    "all_stats":       dict(label="Toutes les stats", fmt="plus", cible=None),
    "sprint_mult_dmg": dict(label="Dégâts en sprint", fmt="pct",  cible="BONUS_DEGATS_SPRINT"),
    "buff_passif_sac": dict(label="Passif du sac",    fmt="pct",  cible=None),
    # stat VIRTUELLE (jamais portée par un objet) : ce que "all_stats" apporte aux dégâts de base
    "_degats_base":    dict(label="Dégâts de base",   fmt="pct",  cible="BONUS_DEGATS_BASE", all_stats="ALL_STATS_DEGATS", virtuel=True),
}

STATS_ARMURE = tuple(k for k, d in STATS.items() if not d.get("virtuel"))


def formater(stat, valeur):
    """('Réduction dégâts', '+12%') prêt à afficher."""
    d = STATS.get(stat, {"label": stat, "fmt": "plus"})
    f = d["fmt"]
    if f == "pct":
        txt = f"+{valeur * 100:.0f}%"
    elif f == "mult":
        txt = f"x{1 + valeur:.2f}"
    elif f == "int":
        txt = f"{valeur:.0f}"
    elif f == "par_s":
        txt = f"+{valeur:.1f}/s"
    elif f == "cellules":
        txt = f"{valeur:.1f} cell."
    else:
        txt = f"+{valeur:.0f}" if abs(valeur) >= 10 else f"+{valeur:.1f}"
    return d["label"], txt
