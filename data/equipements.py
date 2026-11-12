# data/equipements.py
# ============================================================================
# GESTION UNIFIÉE DES ARMES ET ARMURES  (remplace l'ancien data/armes.py)
#
#   Slots : 1 'arme' + 5 armures ('casque', 'torse', 'jambieres', 'bottes', 'ram')
#
#   AJOUTER UN ITEM = ajouter UNE entrée dans CATALOGUE, puis (pour qu'il tombe dans
#   les coffres) UNE entrée dans BOOSTS (data/boosts.py) avec effet="equipement".
#
#   Chaque exemplaire possédé est une INSTANCE avec un identifiant unique
#   (ex: "helmet_3") : on peut donc avoir plusieurs casques de raretés différentes.
#   Chaque objet a un POIDS en MB ; le joueur ne peut pas porter plus que poids_max()
#   (base + bonus du slot RAM). Tout ce qui est dans l'inventaire compte, équipé ou non.
# ============================================================================
import random
from data import config

# ---------------------------------------------------------------------------
# 1. RARETÉS (New_Todoo_liste.txt)
# ---------------------------------------------------------------------------
RARETES = {
    "commun":   {"taux": 0.45, "mult": 0.75, "couleur": (190, 190, 205)},
    "rare":     {"taux": 0.35, "mult": 0.85, "couleur": (80, 180, 255)},
    "leg":      {"taux": 0.10, "mult": 1.00, "couleur": (255, 220, 80)},
    "mythique": {"taux": 0.07, "mult": 1.50, "couleur": (255, 70, 100)},
    "special":  {"taux": 0.03, "mult": 1.25, "couleur": (200, 90, 255), "tout_substats": True},
}

# ---------------------------------------------------------------------------
# 2. CATALOGUE
# ---------------------------------------------------------------------------
CATALOGUE = {
    # --- ARMES (la rareté multiplie "degats") ---
    "laser_v1": {
        "nom": "Laser Blaster v1", "type": "arme", "taille": "12MB",
        "stats": {"degats": 1.0, "cadence": 0.18, "chargeur": 15, "recharge": 1.4, "portee": 1800}
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
    "helmet": {
        "nom": "Casque Système", "type": "casque", "taille": "12MB",
        "stat_principale": ("reduction_dmgs", 0.03, 0.25),
        "substats_possibles": [
            ("auto_regen", 1.0, 5.0),      # +1 à +5 PV/s
            ("auto_aim", 0.50, 1.00),      # 50% à 100% d'aide à la visée
        ],
    },
    "chestplate": {
        "nom": "Plastron Pare-Feu", "type": "torse", "taille": "20MB",
        "stat_principale": ("augmentation_hp", 10.0, 75.0),
        "substats_possibles": [
            ("hit_speed", 0.10, 0.50),     # +10% à +50% de cadence de tir
            ("dash_atq", 1.0, 3.0),        # dash de 1 à 3 cellules (touche A)
        ],
    },
    "leggings": {
        "nom": "Jambières Bus Données", "type": "jambieres", "taille": "18MB",
        "stat_principale": ("reduction_dmgs", 0.05, 0.40),
        "substats_possibles": [
            ("mult_damage", 0.10, 0.40),   # x1.10 à x1.40 dégâts
            ("zap_chaine", 3.0, 10.0),     # 3 à 10 éclairs sur les ennemis proches
        ],
    },
    "boots": {
        "nom": "Bottes Super-Cadence", "type": "bottes", "taille": "10MB",
        "stat_principale": ("vitesse", 0.10, 0.30),
        "substats_possibles": [
            ("all_stats", 5.0, 50.0),          # +5 à +50 "points" partout
            ("sprint_mult_dmg", 0.20, 0.60),   # +20% à +60% dégâts en sprint
        ],
    },
    "ram_ext": {
        "nom": "Extension RAM", "type": "ram", "taille": "5MB",
        "stat_principale": ("poids_max_buff", 0.01, 1.00),   # +1% à +100% de poids max transportable
        "substats_possibles": [
            ("buff_passif_sac", 0.05, 0.25),   # les armures rangées dans le sac donnent 5-25% de leur stat
        ],
    },
}

SLOTS = ("arme", "casque", "torse", "jambieres", "bottes", "ram")
SLOTS_ARMURE = SLOTS[1:]

# Toutes les stats d'armure qu'on additionne (pour modifier() et le total)
STATS_ARMURE = (
    "reduction_dmgs", "augmentation_hp", "vitesse", "poids_max_buff",
    "auto_regen", "auto_aim", "hit_speed", "dash_atq", "mult_damage",
    "zap_chaine", "all_stats", "sprint_mult_dmg", "buff_passif_sac",
)

# Bornes (console du terminal) pour les armes
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
possedees = {}                           # uid -> instance
equipees = {s: None for s in SLOTS}      # slot -> uid (ou None)
version = 0                              # +1 à chaque changement : le jeu se resynchronise
stats_actives = {}                       # dernier résultat de calculer_stats()
_compteur = 0


def _bump():
    global version
    version += 1


# ---------------------------------------------------------------------------
# 4. TIRAGE / CRÉATION
# ---------------------------------------------------------------------------
def tirer_rarete(biais=None):
    """Tire une rareté selon les taux. `biais` = {rarete: multiplicateur} (coffres militaires...)."""
    poids = {n: d["taux"] * (biais or {}).get(n, 1.0) for n, d in RARETES.items()}
    r = random.random() * sum(poids.values())
    cumul = 0.0
    for nom, p in poids.items():
        cumul += p
        if r <= cumul:
            return nom
    return "commun"


def taille_mb(item):
    """'12MB' -> 12"""
    try:
        return int(str(item["taille"]).upper().replace("MB", "").strip())
    except (KeyError, ValueError):
        return 0


def generer_instance_item(base_id, rarete=None, biais=None):
    """Crée une instance (non possédée) : stats principales x rareté + substats aléatoires."""
    if base_id not in CATALOGUE:
        return None
    t = CATALOGUE[base_id]
    rarete = rarete or tirer_rarete(biais)
    mult_rar = RARETES[rarete]["mult"]
    inst = {"base_id": base_id, "nom": t["nom"], "type": t["type"],
            "taille": t["taille"], "rarete": rarete, "stats": {}}

    if t["type"] == "arme":
        inst["stats"] = dict(t["stats"])
        inst["stats"]["degats"] = round(inst["stats"]["degats"] * mult_rar, 3)
        return inst

    nom_stat, v_min, v_max = t["stat_principale"]
    inst["stats"][nom_stat] = round(random.uniform(v_min, v_max) * mult_rar, 3)
    subs = t.get("substats_possibles", [])
    if RARETES[rarete].get("tout_substats"):
        for n, lo, hi in subs:
            inst["stats"][n] = round(random.uniform(lo, hi), 3)
    elif subs:
        n, lo, hi = random.choice(subs)
        inst["stats"][n] = round(random.uniform(lo, hi), 3)
    return inst


def stat_principale(item):
    """(nom, valeur) de la stat principale d'une armure, None pour une arme."""
    t = CATALOGUE.get(item["base_id"])
    if not t or "stat_principale" not in t:
        return None
    n = t["stat_principale"][0]
    return n, item["stats"].get(n, 0.0)


# ---------------------------------------------------------------------------
# 5. POIDS TRANSPORTÉ (MB)
# ---------------------------------------------------------------------------
def poids_porte():
    return sum(taille_mb(i) for i in possedees.values())


def poids_max():
    return int(config.POIDS_MAX_BASE_MB * (1.0 + getattr(config, "BUFF_POIDS_MAX", 0.0)))


def place_libre(taille):
    return poids_porte() + taille <= poids_max()


def resoudre(ref):
    """Retrouve un uid depuis ce que tape le joueur : uid exact, sinon id de base (insensible à la casse)."""
    if not ref:
        return None
    r = ref.lower()
    if r in possedees:
        return r
    for uid, it in possedees.items():
        if it["base_id"].lower() == r:
            return uid
    return None


def ajouter(instance):
    """Range une instance dans le sac. -> (True, uid) ou (False, raison)."""
    global _compteur
    if instance is None:
        return False, "item inconnu"
    if not place_libre(taille_mb(instance)):
        return False, "trop lourd"
    _compteur += 1
    uid = f"{instance['base_id'].lower()}_{_compteur}"
    possedees[uid] = instance
    _bump()
    return True, uid


def donner(base_id, rarete=None):
    """Raccourci console / debug : crée et range un item. -> uid ou None."""
    ok, res = ajouter(generer_instance_item(base_id, rarete))
    return res if ok else None


derniere_erreur = ""     # raison du dernier refus (affichée par le terminal)


def surcharge():
    """True si le joueur porte plus que son poids max (ex: RAM retirée)."""
    return poids_porte() > poids_max()


def _refuser(msg):
    global derniere_erreur
    derniere_erreur = msg
    return False


def jeter(ref):
    """Jette un item (le déséquipe d'abord). -> (ok, message)"""
    uid = resoudre(ref)
    if uid is None:
        return False, f"item inconnu : {ref}"
    if possedees[uid]["type"] == "arme" and equipees["arme"] == uid:
        return False, "impossible de jeter l'arme équipée"
    avant_equipees = dict(equipees)
    item = possedees.pop(uid)
    for s, u in equipees.items():
        if u == uid:
            equipees[s] = None
    appliquer_config()
    if surcharge():                       # ex: jeter la RAM alors qu'on porte trop pour s'en passer
        possedees[uid] = item
        equipees.update(avant_equipees)
        appliquer_config()
        return False, f"impossible : tu serais en surcharge ({poids_porte()}/{poids_max()} MB sans cet objet)"
    return True, f"{uid} ({item['nom']}) jeté."


# ---------------------------------------------------------------------------
# 6. ÉQUIPER
# ---------------------------------------------------------------------------
def _changer_slot(slot, nouvel_uid):
    ancien = equipees[slot]
    equipees[slot] = nouvel_uid
    appliquer_config()
    if surcharge():                       # la RAM précédente donnait plus de poids max
        equipees[slot] = ancien
        appliquer_config()
        return _refuser(f"surcharge : {poids_porte()}/{poids_max()} MB avec ce changement")
    return True


def equiper(ref):
    uid = resoudre(ref)
    if uid is None:
        return False
    slot = possedees[uid]["type"]
    if slot not in equipees:
        return False
    return _changer_slot(slot, uid)


def desequiper(cible):
    """`cible` = nom de slot ('casque'...) ou uid. L'arme ne se déséquipe pas (on en change)."""
    slot = cible if cible in equipees else None
    if slot is None:
        uid = resoudre(cible)
        slot = next((s for s, u in equipees.items() if u == uid), None) if uid else None
    if slot is None or equipees[slot] is None:
        return False
    if slot == "arme":
        return _refuser("l'arme ne se déséquipe pas : equip une autre arme")
    return _changer_slot(slot, None)


def reinitialiser():
    """Nouvelle partie : inventaire vide, arme de départ équipée."""
    global _compteur
    for s in equipees:
        equipees[s] = None
    possedees.clear()
    _compteur = 0
    uid = donner(ARME_DEPART, rarete="leg")
    equiper(uid)


# ---------------------------------------------------------------------------
# 7. CALCUL DES STATS
# ---------------------------------------------------------------------------
def calculer_stats():
    """Cumule les stats des pièces équipées + le passif de la RAM sur l'inventaire. -> dict {stat: total}."""
    tot = {s: 0.0 for s in STATS_ARMURE}

    for slot in SLOTS_ARMURE:
        uid = equipees[slot]
        if uid in possedees:
            for st, v in possedees[uid]["stats"].items():
                if st in tot:
                    tot[st] += v

    # RAM : les armures rangées (non équipées) donnent une fraction de leur stat principale
    passif = tot["buff_passif_sac"]
    if passif > 0:
        equipes = set(equipees.values())
        for uid, it in possedees.items():
            if uid in equipes or it["type"] in ("arme", "ram"):
                continue
            sp = stat_principale(it)
            if sp and sp[0] in tot:
                tot[sp[0]] += sp[1] * passif
    return tot


def appliquer_config():
    """Recalcule TOUT depuis les items équipés et l'écrit dans data/config.py."""
    # --- Arme ---
    uid = equipees["arme"]
    if uid in possedees:
        for stat, cle in STAT_CONFIG_ARME.items():
            setattr(config, cle, possedees[uid]["stats"].get(stat, 0))

    t = calculer_stats()
    global stats_actives
    stats_actives = t
    a = t["all_stats"]      # "points partout" : ajoutés AVANT les autres bonus

    config.REDUCTION_DEGATS = min(config.REDUCTION_MAX, t["reduction_dmgs"] + a * config.ALL_STATS_REDUCTION)
    config.BONUS_HP = t["augmentation_hp"] + a * config.ALL_STATS_HP
    config.BONUS_VITESSE = t["vitesse"] + a * config.ALL_STATS_VITESSE
    config.BONUS_DEGATS_BASE = a * config.ALL_STATS_DEGATS
    config.BUFF_POIDS_MAX = t["poids_max_buff"]
    config.REGEN_EQUIP = t["auto_regen"]
    config.AUTO_AIM = min(1.0, t["auto_aim"])
    config.MULT_DEGATS_EQUIP = t["mult_damage"]
    config.BONUS_DEGATS_SPRINT = t["sprint_mult_dmg"]
    config.ZAP_NB = int(round(t["zap_chaine"]))
    config.DASH_CELLULES = t["dash_atq"]
    # hit_speed : +X% de cadence = délai divisé par (1 + X)
    config.CADENCE_TIR = max(0.03, config.CADENCE_TIR / (1.0 + t["hit_speed"]))
    _bump()


def multiplicateur_degats(sprint=False):
    """Multiplicateur de dégâts apporté par l'équipement (à appliquer sur config.DEGATS_TIR)."""
    m = (1.0 + config.BONUS_DEGATS_BASE) * (1.0 + config.MULT_DEGATS_EQUIP)
    if sprint:
        m *= 1.0 + config.BONUS_DEGATS_SPRINT
    return m


# ---------------------------------------------------------------------------
# 8. CONSOLE (terminal) : modifier / reset
# ---------------------------------------------------------------------------
def modifier(ref, stat, valeur):
    uid = resoudre(ref)
    if uid is None:
        return False, f"item inconnu : {ref}"
    item = possedees[uid]

    if item["type"] == "arme":
        if stat not in BORNES_ARMES:
            return False, f"stat inconnue ({', '.join(BORNES_ARMES)})"
        lo, hi = BORNES_ARMES[stat]
        if not lo <= valeur <= hi:
            return False, f"{stat} doit être entre {lo} et {hi}"
        item["stats"][stat] = int(valeur) if stat in ("chargeur", "portee") else float(valeur)
    else:
        if stat not in STATS_ARMURE:
            return False, f"stat inconnue ({', '.join(STATS_ARMURE)})"
        item["stats"][stat] = float(valeur)

    if uid in equipees.values():
        appliquer_config()
    return True, f"{uid}.{stat} = {item['stats'][stat]}"


def reset_item(ref):
    """Annule les modifs console : re-génère les stats de l'item (même base, même rareté)."""
    uid = resoudre(ref)
    if uid is None:
        return False
    it = possedees[uid]
    possedees[uid] = generer_instance_item(it["base_id"], it["rarete"])
    if uid in equipees.values():
        appliquer_config()
    return True
