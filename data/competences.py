# data/competences.py
# ============================================================================
#  ARBRE DE COMPÉTENCES (GDD : 4 branches).  Définitions pures ; les règles sont dans world/competences.py.
#  AJOUTER UNE COMPÉTENCE = une entrée dans COMPETENCES (branche, type, doc, + paramètres) puis, si c'est une
#  nouvelle mécanique, une fonction dans world/competences.py.
#
#    type  : "mineure" | "majeure" | "standard" | "ultime"  -> coût en PC par niveau et niveau max (COUTS)
#    cd    : présent = compétence ACTIVE (recharge en s) ; absent = passive / statistique
#    power_capa : coefficient de puissance de la formule universelle (compétences qui font des dégâts)
#    touche: nom d'action dans data/controles.py (TOUCHES)
# ============================================================================
POINTS = {"depart": 9999, "par_score": 400}      # PC de départ ; +1 PC tous les `par_score` points de score
METRE = 50.0                                    # 1 mètre du GDD = 50 unités du monde (le joueur court à 250 u/s)
BASE_DMG = 8.0                                  # base_dmg : statistique fondamentale d'attaque du personnage
BOSS_FACTOR_STANDARD = 1.0                      # boss_factor d'un ennemi standard (30 + 10 * niveau pour un boss)

# (PC par niveau, niveau maximum)
COUTS = {"mineure": (1, 10), "majeure": (2, 10), "standard": (3, 5), "ultime": (5, 3)}

# spec_weight : poids des points spécialisés ; stat_dmg : la statistique de dégâts de la branche
BRANCHES = {
    "mobilite": dict(nom="Mobilité",     spec_weight=2.5, stat_dmg="mobility_dmg",   couleur=(60, 240, 255)),
    "controle": dict(nom="Contrôle",     spec_weight=1.8, stat_dmg="control_dmg",    couleur=(255, 70, 110)),
    "aoe":      dict(nom="AOE / Portée", spec_weight=2.0, stat_dmg="aoe_dmg",        couleur=(255, 200, 60)),
    "synth":    dict(nom="Synth",        spec_weight=1.5, stat_dmg="corruption_dmg", couleur=(190, 100, 255)),
}

COMPETENCES = {
    # ------------------------------------------------------------------ MOBILITÉ
    "speed_stat": dict(branche="mobilite", type="mineure", nom="Vitesse",
        doc="+5% de vitesse de déplacement par niveau."),
    "mobility_dmg": dict(branche="mobilite", type="mineure", nom="Dégâts de mobilité",
        doc="+1 point de dégâts de mobilité par niveau (x2.5 dans la formule universelle)."),
    "dash": dict(branche="mobilite", type="standard", nom="Dash", cd=4.0, power_capa=120, touche="dash",
        doc="Propulse le joueur et blesse tout sur la trajectoire. L'armure peut donner des niveaux gratuits."),
    "speed_damage": dict(branche="mobilite", type="standard", nom="Vitesse = Dégâts",
        doc="+8% de vitesse par niveau ; +0.5% x niveau de dégâts d'arme par tranche de 10 de vitesse (hors dash)."),
    "suppression_rapide": dict(branche="mobilite", type="ultime", nom="Suppression rapide", cd=50.0, power_capa=600, touche="ultime",
        doc="Téléporte d'ennemi en ennemi (3 + 2 x niv + 2 x niv dash sauts), dégâts à chaque impact. Verrouille le dash."),
    # ------------------------------------------------------------------ CONTRÔLE
    "control_dmg": dict(branche="controle", type="mineure", nom="Dégâts de contrôle",
        doc="+1 point de dégâts de contrôle ; +5% de dégâts subis par niveau sur les cibles contrôlées."),
    "control_power": dict(branche="controle", type="majeure", nom="Puissance de contrôle",
        doc="+1 indice de puissance : durée, rayon, nombre de cibles, chances de réussite."),
    "controle_passif": dict(branche="controle", type="standard", nom="Champ de contrôle",
        doc="Un ennemi dans votre cône de vision est ralenti de 30%. Dégâts +(control_dmg x niv)% mais chaque tir coûte 2 munitions."),
    "stacking": dict(branche="controle", type="standard", nom="Stacking",
        doc="Un tir peut attirer les ennemis proches vers la cible et les étourdir 5 s (recharge interne 3 s)."),
    "controle_total": dict(branche="controle", type="ultime", nom="Contrôle total", cd=60.0, touche="ultime",
        doc="Affiche PV et taux de piratage ; pirate l'ennemi visé : il devient un allié (+50%) jusqu'à sa mort."),
    # ------------------------------------------------------------------ AOE / PORTÉE
    "aoe_dmg": dict(branche="aoe", type="mineure", nom="Dégâts de zone",
        doc="+1 point de dégâts de zone (x2.0) ; +5% de rayon des zones par niveau."),
    "range_pierce": dict(branche="aoe", type="majeure", nom="Portée / Pénétration",
        doc="+15% de portée par niveau ; +1 pénétration tous les 3 niveaux (traverse ennemis et couverts)."),
    "onde_vectorielle": dict(branche="aoe", type="standard", nom="Onde vectorielle", cd=8.0, power_capa=150, touche="onde_vectorielle",
        doc="Impulsion au sol : repousse les ennemis, détruit les projectiles. Rayon 5 m x (1 + 0.05 x aoe_dmg)."),
    "ricochet_laser": dict(branche="aoe", type="standard", nom="Ricochet laser",
        doc="Un tir qui touche a (15 x niv)% de chance de ricocher vers une cible à 10 m (60% des dégâts)."),
    "effondrement_polygonal": dict(branche="aoe", type="ultime", nom="Effondrement polygonal", cd=55.0, touche="ultime",
        doc="Dôme géant 8 s : chaque tir tiré dedans est dupliqué sur tous les ennemis du dôme (40% + 10% x niv)."),
    # ------------------------------------------------------------------ SYNTH
    "corruption_dmg": dict(branche="synth", type="mineure", nom="Dégâts de corruption",
        doc="+1 point de dégâts de corruption par niveau (x1.5)."),
    "corruption_power": dict(branche="synth", type="majeure", nom="Puissance de corruption",
        doc="+5% de progression par tick et +1 m de rayon de contagion par niveau."),
    "corruption_virulente": dict(branche="synth", type="standard", nom="Corruption virulente", cd=10.0, power_capa=25, touche="corruption_virulente",
        doc="Injecte un virus (DoT). À 100% : corrompu à vie (dégâts subis +x%, infligés -x%), contagion alentour."),
    "corruption_accrue": dict(branche="synth", type="standard", nom="Corruption accrue",
        doc="Désactive la contagion ; progression x2, ticks +50% par niveau ; le taux peut monter à 150% (cible unique)."),
    "propagation_letale": dict(branche="synth", type="ultime", nom="Propagation létale", cd=90.0, power_capa=300, touche="ultime",
        doc="12 s : onde qui corrompt tout, sillage toxique, gravité -30%, murs translucides."),
}

for _cid, _c in COMPETENCES.items():
    assert _c["branche"] in BRANCHES and _c["type"] in COUTS, f"data/competences.py -> '{_cid}' : branche/type invalide"
