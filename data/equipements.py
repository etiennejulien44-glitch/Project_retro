# data/equipements.py (remplace ou étend data/armes.py)
# ============================================================================
# GESTION UNIFIÉE DES ARMES ET ARMURES
# Slots d'équipement : 
#   - 1 slot 'arme'
#   - 5 slots d'armure : 'casque', 'torse', 'jambieres', 'bottes', 'ram'
# ============================================================================
import random
from data import config

# ---------------------------------------------------------------------------
# 1. RARETÉS ET TAUM D'OBTENTION (issu de New_Todoo_liste.txt)
# ---------------------------------------------------------------------------
RARETES = {
    "commun":   {"taux": 0.45, "mult": 0.75},
    "rare":     {"taux": 0.35, "mult": 0.85},
    "leg":      {"taux": 0.10, "mult": 1.00},
    "mythique": {"taux": 0.07, "mult": 1.50},
    "special":  {"taux": 0.03, "mult": 1.25, "tout_substats": True},
}

# ---------------------------------------------------------------------------
# 2. CATALOGUE DE BASE (ARMES & ARMURES)
# ---------------------------------------------------------------------------
CATALOGUE = {
    # --- ARMES ---
    "laser_v1": {
        "nom": "Laser Blaster v1", "type": "arme", "taille": "12MB",
        "stats": {"degats": 200.0, "cadence": 0.18, "chargeur": 15, "recharge": 1.4, "portee": 1800}
    },
    "plasma": {
        "nom": "Plasma Rifle", "type": "arme", "taille": "15MB",
        "stats": {"degats": 4.0, "cadence": 0.55, "chargeur": 6, "recharge": 2.2, "portee": 1800}
    },
    "pulse_smg": {
        "nom": "Pulse SMG", "type": "arme", "taille": "9MB",
        "stats": {"degats": 0.5, "cadence": 0.07, "chargeur": 40, "recharge": 1.8, "portee": 1200}
    },

    # --- ARMURES ---
    "Helmet": {
        "nom": "Casque Système", "type": "casque", "taille": "12MB",
        "stat_principale": ("reduction_dmgs", 0.03, 0.25),
        "substats_possibles": [
            ("auto_regen", 1.0, 5.0),      # +1 à +5 HP/s
            ("auto_aim", 0.50, 1.00)       # 50% à 100% auto aim
        ]
    },
    "chestplate": {
        "nom": "Plastron Pare-Feu", "type": "torse", "taille": "20MB",
        "stat_principale": ("augmentation_hp", 10.0, 75.0),
        "substats_possibles": [
            ("hit_speed", 0.10, 0.50),     # +10% à +50% hit speed
            ("dash_atq", 1.0, 3.0)         # Dash 1 à 3 cellules
        ]
    },
    "leggins": {
        "nom": "Jambières Bus Données", "type": "jambieres", "taille": "18MB",
        "stat_principale": ("reduction_dmgs", 0.05, 0.40),
        "substats_possibles": [
            ("mult_damage", 0.10, 0.40),   # x1.10 à x1.40 dégâts
            ("zap_chaine", 3.0, 10.0)      # 3 à 10 rebonds
        ]
    },
    "boots": {
        "nom": "Bottes Super-Cadence", "type": "bottes", "taille": "10MB",
        "stat_principale": ("vitesse", 0.10, 0.30),
        "substats_possibles": [
            ("all_stats", 5.0, 50.0),      # +5 à +50 partout
            ("sprint_mult_dmg", 0.20, 0.60)# +20% à +60% dmg au sprint
        ]
    },
    "RAM_extensions": {
        "nom": "Extension RAM", "type": "ram", "taille": "5MB",
        "stat_principale": ("sac_taille_buff", 0.01, 1.00), # +1% à +100% sac
        "substats_possibles": [
            ("buff_passif_sac", 0.05, 0.25)
        ]
    }
}

# Configuration des bornes armes pour modification terminal
BORNES_ARMES = {
    "degats": (0.1, 50.0), "cadence": (0.03, 2.0), "chargeur": (1, 200),
    "recharge": (0.2, 6.0), "portee": (300, 1800)
}
STAT_CONFIG_ARME = {
    "degats": "DEGATS_TIR", "cadence": "CADENCE_TIR", "chargeur": "CHARGEUR_TAILLE",
    "recharge": "RECHARGE_DUREE", "portee": "PORTEE_TIR"
}

ARME_DEPART = "laser_v1"

# ---------------------------------------------------------------------------
# 3. ÉTAT DU JEU
# ---------------------------------------------------------------------------
possedees = {}  # item_id -> dict de données de l'item instancié

# Slots uniques : 1 arme + 5 pièces d'armure
equipees = {
    "arme": None,
    "casque": None,
    "torse": None,
    "jambieres": None,
    "bottes": None,
    "ram": None
}

# ---------------------------------------------------------------------------
# 4. FONCTIONS PRINCIPALES UNIFIÉES
# ---------------------------------------------------------------------------

def tirer_rarete():
    """Tire une rareté aléatoire selon les taux définis."""
    r = random.random()
    cumul = 0.0
    for nom_rar, data in RARETES.items():
        cumul += data["taux"]
        if r <= cumul:
            return nom_rar
    return "commun"


def generer_instance_item(base_id, rarete=None):
    """Génère un item avec ses stats calculées et ses substats rdm."""
    if base_id not in CATALOGUE:
        return None

    template = CATALOGUE[base_id]
    item_type = template["type"]
    rarete = rarete or tirer_rarete()
    mult_rar = RARETES[rarete]["mult"]
    est_special = RARETES[rarete].get("tout_substats", False)

    instance = {
        "base_id": base_id,
        "nom": template["nom"],
        "type": item_type,
        "taille": template["taille"],
        "rarete": rarete,
        "stats": {}
    }

    if item_type == "arme":
        # Arme : copie des stats de base
        instance["stats"] = dict(template["stats"])
    else:
        # Armure : Stat principale pondérée par la rareté
        stat_name, v_min, v_max = template["stat_principale"]
        val_base = round(random.uniform(v_min, v_max) * mult_rar, 3)
        instance["stats"][stat_name] = val_base
        
        # Substats / Effets
        substats_possibles = template.get("substats_possibles", [])
        if est_special:
            # Reçoit TOUS les substats
            for sub_name, s_min, s_max in substats_possibles:
                instance["stats"][sub_name] = round(random.uniform(s_min, s_max), 3)
        elif substats_possibles:
            # Reçoit 1 substat aléatoire
            sub_name, s_min, s_max = random.choice(substats_possibles)
            instance["stats"][sub_name] = round(random.uniform(s_min, s_max), 3)

    return instance


def donner(item_id, rarete=None):
    """Ajoute l'item à l'inventaire. Retourne True si succès."""
    if item_id in possedees:
        return False
    
    instance = generer_instance_item(item_id, rarete)
    if not instance:
        return False

    possedees[item_id] = instance
    return True


def equiper(item_id):
    """Équipe l'item dans son slot dédié (arme, casque, torse, etc.)."""
    if item_id not in possedees:
        return False

    item = possedees[item_id]
    slot = item["type"]

    if slot in equipees:
        equipees[slot] = item_id
        appliquer_config()
        return True
    return False


def desequiper(slot):
    """Déséquipe l'item du slot spécifié."""
    if slot in equipees and equipees[slot] is not None:
        equipees[slot] = None
        appliquer_config()
        return True
    return False


def reinitialiser():
    """Réinitialise l'inventaire et les équipements."""
    for s in equipees:
        equipees[s] = None
    possedees.clear()
    donner(ARME_DEPART, rarete="leg")
    equiper(ARME_DEPART)


def appliquer_config():
    """Recalcule et applique toutes les stats des items équipés sur le module config."""
    # 1. Stats d'arme
    arme_id = equipees["arme"]
    if arme_id and arme_id in possedees:
        for stat, cle_cfg in STAT_CONFIG_ARME.items():
            setattr(config, cle_cfg, possedees[arme_id]["stats"].get(stat, 0))

    # 2. Accumulation des stats d'armures
    armure_stats_totales = {
        "reduction_dmgs": 0.0,
        "augmentation_hp": 0.0,
        "vitesse": 0.0,
        "sac_taille_buff": 0.0,
        "auto_regen": 0.0,
        "auto_aim": 0.0,
        "hit_speed": 0.0,
        "dash_atq": 0.0,
        "mult_damage": 0.0,
        "zap_chaine": 0.0,
        "all_stats": 0.0,
        "sprint_mult_dmg": 0.0,
        "buff_passif_sac": 0.0
    }

    slots_armure = ["casque", "torse", "jambieres", "bottes", "ram"]
    for slot in slots_armure:
        item_id = equipees[slot]
        if item_id and item_id in possedees:
            for stat, val in possedees[item_id]["stats"].items():
                if stat in armure_stats_totales:
                    armure_stats_totales[stat] += val

    # Application globale dans config
    config.REDUCTION_DEGATS = armure_stats_totales["reduction_dmgs"]
    config.BONUS_HP = armure_stats_totales["augmentation_hp"]
    config.BONUS_VITESSE = armure_stats_totales["vitesse"]
    config.BUFF_TAILLE_SAC = armure_stats_totales["sac_taille_buff"]
    config.STATS_ARMURE_ACTIVE = armure_stats_totales


def modifier(item_id, stat, valeur):
    """Permet de modifier une stat d'arme ou d'armure en jeu via la console."""
    if item_id not in possedees:
        return False, f"item inconnu : {item_id}"

    item = possedees[item_id]

    if item["type"] == "arme":
        if stat not in BORNES_ARMES:
            return False, f"stat inconnue ({', '.join(BORNES_ARMES)})"
        lo, hi = BORNES_ARMES[stat]
        if not lo <= valeur <= hi:
            return False, f"{stat} doit être entre {lo} et {hi}"
        item["stats"][stat] = int(valeur) if stat in ("chargeur", "portee") else float(valeur)
    else:
        # Armure : modification directe de la stat
        item["stats"][stat] = float(valeur)

    # Réapplication si l'item est actuellement équipé
    if item_id in equipees.values():
        appliquer_config()

    return True, f"{item_id}.{stat} = {item['stats'][stat]}"


def reset_item(item_id):
    """Réinitialise les stats d'un item selon sa définition du catalogue."""
    if item_id not in possedees:
        return False
    rarete_actuelle = possedees[item_id].get("rarete", "commun")
    possedees[item_id] = generer_instance_item(possedees[item_id]["base_id"], rarete_actuelle)
    
    if item_id in equipees.values():
        appliquer_config()
    return True