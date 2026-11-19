# world/inventaire.py
# ============================================================================
#  INVENTAIRE / ÉQUIPEMENT : ÉTAT et RÈGLES (les définitions sont dans data/armes.py, data/armures.py,
#  data/stats.py, data/raretes.py).
#  Chaque exemplaire possédé est une INSTANCE avec un identifiant unique (ex: "helmet_3").
#  Chaque objet a un POIDS en MB ; on ne peut pas porter plus que poids_max() (base + slot RAM).
# ============================================================================
import random
from data import config
from data.armes import ARMES, ARME_DEPART, BORNES_ARMES, STAT_CONFIG_ARME
from data.armures import ARMURES, SLOTS_ARMURE
from data.raretes import RARETES
from data.stats import STATS, STATS_ARMURE

CATALOGUE = {**ARMES, **ARMURES}          # toutes les définitions d'items, par id de base
SLOTS = ("arme",) + SLOTS_ARMURE

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
    """Recalcule TOUT depuis les items équipés et l'écrit dans data/config.py. GÉNÉRIQUE : piloté par data/stats.py."""
    uid = equipees["arme"]
    if uid in possedees:
        for stat, cle in STAT_CONFIG_ARME.items():
            setattr(config, cle, possedees[uid]["stats"].get(stat, 0))

    t = calculer_stats()
    global stats_actives
    stats_actives = t
    a = t["all_stats"]      # "points partout" : ajoutés AVANT les autres bonus
    for nom, d in STATS.items():
        cible = d.get("cible")
        if not cible:
            continue
        v = t.get(nom, 0.0)
        if d.get("all_stats"):
            v += a * getattr(config, d["all_stats"])
        cap = d.get("cap")
        if cap is not None:
            v = min(getattr(config, cap) if isinstance(cap, str) else cap, v)
        setattr(config, cible, int(round(v)) if d.get("entier") else v)
    # hit_speed : +X% de cadence = délai divisé par (1 + X)
    config.CADENCE_TIR = max(0.03, config.CADENCE_TIR / (1.0 + config.BONUS_CADENCE))
    _bump()


def pieces_equipees():
    """[(slot, instance | None)] dans l'ordre d'affichage (pour le HUD / le terminal)."""
    return [(s, possedees.get(equipees[s])) for s in SLOTS]


def definition(instance):
    """Définition (data/) d'une instance : couleur, icône..."""
    return CATALOGUE.get(instance["base_id"], {}) if instance else {}


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
