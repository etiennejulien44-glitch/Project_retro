# world/competences.py -- ARBRE DE COMPÉTENCES : état (niveaux, PC, ultime équipé, recharges) et mécaniques.
#   Définitions et valeurs : data/competences.py.   Formule universelle (GDD) :
#       Total_DMG = ((stat_dmg * spec_weight + base_dmg) * power_capa * 1.1^(lvl-1)) / 100
#   Appelé par world/jeu.py : mettre_a_jour() chaque frame, declencher_touche() sur une touche de compétence,
#   preparer_tir() / apres_tir() autour de chaque tir.
import math
import random

from data import config
from data.competences import (BASE_DMG, BOSS_FACTOR_STANDARD, BRANCHES, COMPETENCES, COUTS, METRE, POINTS)
from data.controles import TOUCHES
from engine import effets
from world import boss as boss_module
from world import entity
from world.terrain import get_hauteur_sol, monstres_caches

niveaux = {}            # niveaux INVESTIS : {id: niveau}
points = 0              # PC disponibles
ultime = None           # id de l'ultime équipé (un seul à la fois)
cd = {}                 # recharges restantes (s)
t = 0.0                 # horloge des effets (ne tourne pas en pause)
_pc_gagnes = 0
suppression = None      # état de Suppression rapide en cours
dome = None             # Effondrement polygonal : {"x","z","r","fin"}
propagation = None      # Propagation létale : {"fin"}
sillages = []           # traînées toxiques [x, z, expire]
_t_sillage = _t_contagion = _t_stacking = 0.0


def reinitialiser():
    global points, ultime, t, _pc_gagnes, suppression, dome, propagation, _t_sillage, _t_contagion, _t_stacking
    niveaux.clear(); cd.clear(); sillages.clear()
    points, ultime, t, _pc_gagnes = POINTS["depart"], None, 0.0, 0
    suppression = dome = propagation = None
    _t_sillage = _t_contagion = _t_stacking = 0.0
    config.GRAVITE_MULT = 1.0
    effets.glitch_moteur = False
    entity.tir_mod["portee"], entity.tir_mod["penetration"] = 1.0, 0


# ===========================================================================
#  Niveaux, coûts, formule
# ===========================================================================
def niveau(cid):
    """Niveau EFFECTIF (investi + niveaux gratuits de l'équipement : le dash reçoit dash_atq)."""
    n = niveaux.get(cid, 0)
    return n + int(config.DASH_CELLULES) if cid == "dash" else n


def cout(cid):
    return COUTS[COMPETENCES[cid]["type"]][0]


def maximum(cid):
    return COUTS[COMPETENCES[cid]["type"]][1]


def est_ultime(cid):
    return COMPETENCES[cid]["type"] == "ultime"


def est_active(cid):
    return "cd" in COMPETENCES[cid]


def actif(cid):
    """Utilisable : niveau > 0 (sinon verrouillée) et, pour un ultime, c'est celui qui est équipé."""
    return niveau(cid) > 0 and (not est_ultime(cid) or ultime == cid)


def acheter(cid, n=1):
    """-> (ok, message). Dépense des PC pour monter `cid` de n niveaux."""
    global points, ultime
    if cid not in COMPETENCES:
        return False, f"compétence inconnue : {cid}"
    acquis = 0
    for _ in range(max(1, n)):
        if niveaux.get(cid, 0) >= maximum(cid):
            return acquis > 0, f"{cid} : niveau maximum ({maximum(cid)})" if not acquis else f"{cid} -> niveau {niveaux[cid]} (max)"
        if points < cout(cid):
            return acquis > 0, f"PC insuffisants : {cout(cid)} requis, {points} disponibles"
        points -= cout(cid)
        niveaux[cid] = niveaux.get(cid, 0) + 1
        acquis += 1
    if est_ultime(cid) and ultime is None:
        ultime = cid
    return True, f"{COMPETENCES[cid]['nom']} -> niveau {niveaux[cid]}   ({points} PC restants)"


def equiper_ultime(cid):
    global ultime
    if cid not in COMPETENCES or not est_ultime(cid):
        return False, "ce n'est pas un ultime"
    if niveaux.get(cid, 0) <= 0:
        return False, f"{cid} est verrouillé (niveau 0)"
    ultime = cid
    return True, f"Ultime équipé : {COMPETENCES[cid]['nom']}  (un seul ultime actif à la fois)"


def respec():
    """Rembourse tous les PC investis."""
    global points, ultime
    points += sum(cout(c) * n for c, n in niveaux.items())
    niveaux.clear()
    ultime = None
    cd.clear()
    return f"Compétences réinitialisées : {points} PC disponibles"


def stat(branche):
    """Points investis dans la statistique de dégâts de la branche."""
    return niveau(BRANCHES[branche]["stat_dmg"])


def base_dmg():
    return BASE_DMG * (1.0 + config.BONUS_DEGATS_BASE)


def formule(branche, lvl, power, stat_pts=None):
    s = stat(branche) if stat_pts is None else stat_pts
    return ((s * BRANCHES[branche]["spec_weight"] + base_dmg()) * power * 1.1 ** (max(1, lvl) - 1)) / 100.0


def degats(cid, power=None):
    c = COMPETENCES[cid]
    return formule(c["branche"], niveau(cid), c["power_capa"] if power is None else power)


def gagner_points(n):
    global points
    points += n


# ===========================================================================
#  Modificateurs permanents (lus par world/jeu.py)
# ===========================================================================
def mult_vitesse():
    return 1.0 + 0.05 * niveau("speed_stat") + 0.08 * niveau("speed_damage")


def bonus_arme(vitesse):
    """speed_damage : +0.5% x niveau par tranche de 10 de vitesse de déplacement (hors dash)."""
    return 0.005 * niveau("speed_damage") * int(vitesse // 10)


def rayon_aoe():
    return 1.0 + 0.05 * niveau("aoe_dmg")


def preparer_tir():
    entity.tir_mod["portee"] = 1.0 + 0.15 * niveau("range_pierce")
    entity.tir_mod["penetration"] = niveau("range_pierce") // 3


# ===========================================================================
#  Recharges / déclenchement
# ===========================================================================
def pret(cid):
    return actif(cid) and cd.get(cid, 0.0) <= 0.0


def dash_verrouille():
    return suppression is not None


def _monstres(cles):
    return [m for cle in cles for m in monstres_caches[cle]]


def declencher_touche(jeu, action):
    """action = nom de data/controles.TOUCHES ('onde_vectorielle', 'corruption_virulente', 'ultime')."""
    cid = ultime if action == "ultime" else next((c for c, d in COMPETENCES.items() if d.get("touche") == action), None)
    if cid is None:
        jeu.annoncer("Aucun ultime équipé  (terminal : cd skills ; up <ultime>)", (255, 120, 120), 1.5)
        return False
    if jeu.joueur.mort or boss_module.run_gagnee:
        return False
    if niveau(cid) <= 0:
        jeu.annoncer(f"{COMPETENCES[cid]['nom']} : verrouillé (niveau 0)", (255, 120, 120), 1.5)
        return False
    if cd.get(cid, 0.0) > 0:
        jeu.annoncer(f"{COMPETENCES[cid]['nom']} : {cd[cid]:.0f}s", (255, 120, 120), 1.0)
        return False
    ok = _LANCEURS[cid](jeu)
    if ok:
        cd[cid] = COMPETENCES[cid]["cd"]
    return ok


# ===========================================================================
#  AOE : onde vectorielle
# ===========================================================================
def _onde(jeu):
    r = 5.0 * METRE * rayon_aoe()
    x0, z0, cles, dmg = config.cam_x, config.cam_z, jeu.zone["cles"], degats("onde_vectorielle")
    n = 0
    for m in _monstres(cles):
        d = math.hypot(m.x - x0, m.z - z0)
        if d < r and m.ciblable:
            ux, uz = ((m.x - x0) / d, (m.z - z0) / d) if d > 1e-6 else (0.0, 1.0)
            m.fx["repousse"] = (ux * 900.0, uz * 900.0, t + 0.35)             # repoussé violemment
            entity._blesser_monstre(m, dmg, cles, jeu.joueur, x0, z0)
            n += 1
    entity.projectiles[:] = [p for p in entity.projectiles if math.hypot(p[0] - x0, p[2] - z0) > r]
    boss_module.projectiles_boss[:] = [p for p in boss_module.projectiles_boss if math.hypot(p[0] - x0, p[2] - z0) > r]
    effets.onde(x0, z0, amp=34.0, vitesse=r / 0.5, longueur=300.0, duree=0.9)
    effets.etincelles((x0, config.cam_y + 30, z0), (255, 200, 60), n=18, vitesse=400.0, taille=12.0)
    jeu.annoncer(f"ONDE VECTORIELLE ! {n} cible(s)", (255, 200, 60), 1.2)
    return True


# ===========================================================================
#  SYNTH : corruption
# ===========================================================================
def injecter(m):
    """Injecte le virus (corruption_virulente) : DoT, ralentissement, jauge 0 -> 100%."""
    if m.allie:
        return
    n = max(5, int(niveau("corruption_virulente") * niveau("corruption_power") / 2))
    c = m.fx.get("corr")
    if c is None:
        m.fx["corr"] = {"jauge": 0.0, "ticks": n, "acc": 0.0, "etat": 1}
    elif c["etat"] == 1:
        c["ticks"] = max(c["ticks"], n)


def corrompu(m):
    c = m.fx.get("corr")
    return c is not None and c["etat"] == 2


def taux_corruption(m):
    c = m.fx.get("corr")
    if c is None or c["etat"] != 2:
        return 0.0
    return min(150.0 if niveau("corruption_accrue") > 0 else 100.0, c["jauge"])


def _virulente(jeu):
    m = entity.cible_visee(jeu.zone["cles"])
    if m is None:
        jeu.annoncer("Aucune cible dans le viseur", (255, 120, 120), 1.0)
        return False
    injecter(m)
    effets.etincelles((m.x, get_hauteur_sol(m.x, m.z) - 20, m.z), (190, 100, 255), n=12)
    jeu.annoncer("CORRUPTION INJECTÉE", (190, 100, 255), 1.2)
    return True


def _tick_corruption(m, jeu):
    """Un tick (1/s) de corruption sur le monstre m."""
    c = m.fx["corr"]
    accrue = niveau("corruption_accrue")
    cp = niveau("corruption_power")
    prog = 10.0 * (1.0 + 0.05 * cp) * (2.0 if accrue else 1.0)
    cap = 150.0 if accrue else 100.0
    if c["etat"] == 1 or accrue:                                   # DoT (se poursuit sur cible unique avec 'accrue')
        dmg = degats("corruption_virulente") * (1.0 + 0.5 * accrue)
        if entity._blesser_monstre(m, dmg, jeu.zone["cles"], jeu.joueur, config.cam_x, config.cam_z):
            return
        c["jauge"] = min(cap, c["jauge"] + prog)
        if c["etat"] == 1:
            c["ticks"] -= 1
    if c["etat"] == 1 and c["jauge"] >= 100.0:                     # PHASE 2 : corrompu pour toujours
        c["etat"] = 2
        m.fx.pop("controle", None)
        m.fx.pop("etourdi", None)
        effets.etincelles((m.x, get_hauteur_sol(m.x, m.z) - 25, m.z), (190, 100, 255), n=14)
    elif c["etat"] == 1 and c["ticks"] <= 0:
        del m.fx["corr"]
        return
    if c["etat"] == 2 and accrue == 0:                             # contagion à corruption_power mètres
        r = max(1, cp) * METRE
        for autre in _monstres(jeu.zone["cles"]):
            if autre is not m and not corrompu(autre) and math.hypot(autre.x - m.x, autre.z - m.z) <= r:
                injecter(autre)


# ===========================================================================
#  CONTRÔLE
# ===========================================================================
def est_controle(m):
    return m.fx.get("controle", 0.0) > t


def _champ_controle(mons):
    """controle_passif : tout ennemi dans le cône de vision est ralenti, pendant 5 + niv x control_power s."""
    lvl = niveau("controle_passif")
    if lvl <= 0:
        return
    rad = math.radians(config.yaw)
    fx_, fz_ = math.sin(rad), math.cos(rad)
    duree = 5.0 + lvl * niveau("control_power")
    for m in mons:
        dx, dz = m.x - config.cam_x, m.z - config.cam_z
        d = math.hypot(dx, dz)
        if 1e-6 < d < 900.0 and (dx * fx_ + dz * fz_) / d > 0.9 and not corrompu(m):      # cône ~ ±25°
            m.fx["controle"] = t + duree
            if random.random() < 0.08:
                effets.etincelles((m.x, get_hauteur_sol(m.x, m.z) - 25, m.z), (255, 60, 200), n=2,
                                  vitesse=90.0, taille=10.0)


def _stacking(jeu, cible):
    """Proc : attire les ennemis proches vers la cible touchée et les étourdit 5 s."""
    global _t_stacking
    lvl = niveau("stacking")
    cp = niveau("control_power")
    if lvl <= 0 or cible is None or _t_stacking > 0 or random.random() * 100 >= lvl * 2 + cp:
        return
    _t_stacking = 3.0
    cles = jeu.zone["cles"]
    autres = sorted((m for m in _monstres(cles) if m is not cible and m.ciblable and not corrompu(m)),
                    key=lambda m: math.hypot(m.x - cible.x, m.z - cible.z))[:max(1, cp // 2)]
    dmg = formule("controle", lvl, 50 + lvl * 10)
    for k, m in enumerate(autres):
        a = 2 * math.pi * k / max(1, len(autres))
        m.x, m.z = cible.x + math.cos(a) * 45, cible.z + math.sin(a) * 45         # attirés magnétiquement
        m.fx["etourdi"] = t + 5.0
        entity._blesser_monstre(m, dmg, cles, jeu.joueur, cible.x, cible.z)
        effets.etincelles((m.x, get_hauteur_sol(m.x, m.z) - 25, m.z), (255, 70, 110), n=6)
    if autres:
        effets.onde(cible.x, cible.z, amp=14.0)


def chance_piratage(m):
    """Contrôle total : (PV manquants% / (2 + boss_factor)) x (1 + 0.15 x (lvl - 1))."""
    manquants = 100.0 * (1.0 - m.hp / m.hp_max)
    return min(100.0, manquants / (2.0 + BOSS_FACTOR_STANDARD) * (1.0 + 0.15 * (niveau("controle_total") - 1)))


def allies():
    return [m for cle in monstres_caches for m in monstres_caches[cle] if m.allie]


def _piratage(jeu):
    m = entity.cible_visee(jeu.zone["cles"])
    if m is None:
        jeu.annoncer("Aucune cible dans le viseur", (255, 120, 120), 1.0)
        return False
    limite = max(1, niveau("control_power"))
    if len(allies()) >= limite:
        jeu.annoncer(f"Limite d'alliés atteinte ({limite})", (255, 120, 120), 1.5)
        return False
    ch = chance_piratage(m)
    if random.random() * 100 < ch:
        m.allie = True
        m.fx.clear()
        m.hp_max = int(m.hp_max * 1.5)                            # stats +50%
        m.hp = m.hp_max
        effets.etincelles((m.x, get_hauteur_sol(m.x, m.z) - 25, m.z), (60, 240, 255), n=16)
        effets.onde(m.x, m.z, amp=18.0)
        jeu.annoncer(f"PIRATAGE RÉUSSI ({ch:.0f}%) : {m.data['nom']} est votre allié", (60, 240, 255), 2.5)
    else:
        jeu.annoncer(f"Piratage échoué ({ch:.0f}%)", (255, 120, 120), 1.5)
    return True


# ===========================================================================
#  MOBILITÉ : suppression rapide
# ===========================================================================
def _lancer_suppression(jeu):
    global suppression
    sauts = 3 + 2 * niveau("suppression_rapide") + 2 * niveau("dash")
    suppression = {"restant": sauts, "t": 0.0}
    for m in _monstres(jeu.zone["cles"]):
        m.tag = 0
    jeu.annoncer(f"SUPPRESSION RAPIDE : {sauts} sauts", (60, 240, 255), 1.5)
    return True


def _maj_suppression(dt, jeu):
    global suppression
    s = suppression
    if s is None:
        return
    s["t"] += dt
    pas = 0.18 / (1.0 + 0.15 * niveau("speed_damage"))             # speed_damage : vitesse théorique +15% par niveau
    if s["t"] < pas:
        return
    s["t"] = 0.0
    cles = jeu.zone["cles"]
    mons = [m for m in _monstres(cles) if m.ciblable and m.hp > 0]
    for m in mons:                                                  # chaque téléportation : tous les marqueurs perdent 1
        m.tag = max(0, m.tag - 1)
    candidats = [m for m in mons if m.tag == 0 and math.hypot(m.x - config.cam_x, m.z - config.cam_z) < 1500.0]
    if not candidats or s["restant"] <= 0:
        suppression = None
        for m in mons:
            m.tag = 0
        return
    cible = min(candidats, key=lambda m: math.hypot(m.x - config.cam_x, m.z - config.cam_z))
    cible.tag = 3                                                   # anti-boucle (tag_stack)
    dx, dz = cible.x - config.cam_x, cible.z - config.cam_z
    d = math.hypot(dx, dz) or 1.0
    config.cam_x, config.cam_z = cible.x - dx / d * 70.0, cible.z - dz / d * 70.0
    config.cam_y = get_hauteur_sol(config.cam_x, config.cam_z) - 30
    config.vitesse_y = 0.0
    config.yaw = math.degrees(math.atan2(dx, dz))
    dmg = degats("suppression_rapide") * (1.0 + 0.15 * niveau("speed_damage"))
    effets.fov.declencher_dash()
    effets.etincelles((cible.x, get_hauteur_sol(cible.x, cible.z) - 25, cible.z), (60, 240, 255), n=14)
    effets.onde(cible.x, cible.z, amp=16.0)
    entity._blesser_monstre(cible, dmg, cles, jeu.joueur, config.cam_x, config.cam_z)
    s["restant"] -= 1
    if s["restant"] <= 0:
        suppression = None


# ===========================================================================
#  AOE : effondrement polygonal  /  SYNTH : propagation létale
# ===========================================================================
def _lancer_dome(jeu):
    global dome
    dome = {"x": config.cam_x, "z": config.cam_z, "r": 12.0 * METRE * rayon_aoe(), "fin": t + 8.0}
    effets.onde(dome["x"], dome["z"], amp=30.0, vitesse=dome["r"] / 0.6, longueur=360.0, duree=1.0)
    jeu.annoncer("EFFONDREMENT POLYGONAL : 8 s", (255, 200, 60), 2.0)
    return True


def dans_dome(x, z):
    return dome is not None and math.hypot(x - dome["x"], z - dome["z"]) < dome["r"]


def _lancer_propagation(jeu):
    global propagation
    propagation = {"fin": t + 12.0}
    config.GRAVITE_MULT = 0.7                                       # gravité -30%
    effets.glitch_moteur = True                                     # murs translucides, décor corrompu
    cles, dmg = jeu.zone["cles"], degats("propagation_letale")
    x0, z0, n = config.cam_x, config.cam_z, 0
    for m in _monstres(cles):
        if math.hypot(m.x - x0, m.z - z0) < 24.0 * METRE and m.ciblable:
            if not entity._blesser_monstre(m, dmg, cles, jeu.joueur, x0, z0):
                m.fx["corr"] = {"jauge": 100.0, "ticks": 0, "acc": 0.0, "etat": 2}   # Phase 2 directe
            n += 1
    effets.onde(x0, z0, amp=40.0, vitesse=900.0, longueur=420.0, duree=1.6)
    jeu.annoncer(f"PROPAGATION LÉTALE ! {n} corrompu(s)", (190, 100, 255), 2.5)
    return True


_LANCEURS = {"onde_vectorielle": _onde, "corruption_virulente": _virulente, "suppression_rapide": _lancer_suppression,
             "controle_total": _piratage, "effondrement_polygonal": _lancer_dome, "propagation_letale": _lancer_propagation}


# ===========================================================================
#  Autour de chaque tir
# ===========================================================================
def apres_tir(jeu, degats_arme):
    """Ricochet, stacking, dôme : lus dans entity.dernier_tir (cible touchée ou point d'impact)."""
    cible, pos = entity.dernier_tir["cible"], entity.dernier_tir["pos"]
    cles = jeu.zone["cles"]
    if cible is not None and est_controle(cible) and niveau("controle_passif") > 0:
        jeu.joueur.chargeur = max(0, jeu.joueur.chargeur - 1)       # contrepartie : 2 munitions par tir
    # --- ricochet laser : mur ou ennemi, 60% des dégâts vers une cible proche
    lvl = niveau("ricochet_laser")
    if lvl > 0 and pos is not None and random.random() * 100 < 15 * lvl:
        r = 10.0 * METRE * rayon_aoe()
        cands = [m for m in _monstres(cles) if m is not cible and m.ciblable and m.hp > 0
                 and math.hypot(m.x - pos[0], m.z - pos[2]) < r]
        if cands:
            m = min(cands, key=lambda m: math.hypot(m.x - pos[0], m.z - pos[2]))
            y = get_hauteur_sol(m.x, m.z) + m.data.get("hauteur_centre", -20)
            entity.zaps.append([pos[0], pos[1], pos[2], m.x, y, m.z, 0.25])
            entity._blesser_monstre(m, 0.6 * degats_arme, cles, jeu.joueur, pos[0], pos[2])
    # --- stacking
    _stacking(jeu, cible)
    # --- effondrement : le tir se duplique sur chaque ennemi du dôme
    if dome is not None and dans_dome(config.cam_x, config.cam_z):
        frac = 0.4 + 0.1 * niveau("effondrement_polygonal")
        for m in _monstres(cles):
            if m is not cible and m.ciblable and m.hp > 0 and dans_dome(m.x, m.z):
                y = get_hauteur_sol(m.x, m.z) + m.data.get("hauteur_centre", -20)
                entity.zaps.append([config.cam_x, config.cam_y + 10, config.cam_z, m.x, y, m.z, 0.15])
                entity._blesser_monstre(m, frac * degats_arme, cles, jeu.joueur)


# ===========================================================================
#  Mise à jour de chaque frame
# ===========================================================================
def mettre_a_jour(jeu, dt):
    global t, dome, propagation, _pc_gagnes, _t_sillage, _t_contagion, _t_stacking
    t += dt
    for k in list(cd):
        cd[k] = max(0.0, cd[k] - dt)
    _t_stacking = max(0.0, _t_stacking - dt)

    gagnes = jeu.joueur.score // POINTS["par_score"]                  # +1 PC tous les `par_score` points
    if gagnes > _pc_gagnes:
        gagner_points(gagnes - _pc_gagnes)
        jeu.annoncer(f"+{gagnes - _pc_gagnes} PC de compétence  (terminal : cd skills)", (255, 230, 90), 2.5)
        _pc_gagnes = gagnes

    mons = _monstres(jeu.zone["cles"])
    _champ_controle(mons)
    for m in mons:
        if m.hp <= 0 or m.allie:
            continue
        c = m.fx.get("corr")
        if c is not None:
            c["acc"] += dt
            while c["acc"] >= 1.0 and m.fx.get("corr") is c:
                c["acc"] -= 1.0
                _tick_corruption(m, jeu)
            if m.hp <= 0:
                continue
        rep = m.fx.get("repousse")
        if rep is not None:
            if t < rep[2]:
                m.x += rep[0] * dt
                m.z += rep[1] * dt
            else:
                del m.fx["repousse"]
        # --- facteurs de cette frame
        ralenti, vuln, inf = 1.0, 1.0, 1.0
        if m.fx.get("etourdi", 0.0) > t:
            ralenti = 0.0
        else:
            if est_controle(m):
                ralenti *= 0.7
                cd_ = niveau("control_dmg")
                vuln *= (1.0 + cd_ * niveau("controle_passif") / 100.0) * (1.0 + 0.05 * cd_)
            if c is not None:
                if c["etat"] == 1:
                    ralenti *= 0.85
                else:
                    rate = taux_corruption(m)
                    vuln *= 1.0 + rate / 100.0
                    inf = max(0.0, 1.0 - rate / 100.0)
        m.ralenti, m.vuln, m.mult_inf = ralenti, vuln, inf

    _maj_suppression(dt, jeu)

    if dome is not None and t >= dome["fin"]:
        dome = None
    if propagation is not None:
        _maj_propagation(mons, dt)
        if t >= propagation["fin"]:
            propagation = None
            config.GRAVITE_MULT = 1.0
            effets.glitch_moteur = False
    sillages[:] = [s for s in sillages if s[2] > t]
    preparer_tir()


def _maj_propagation(mons, dt):
    """Sillage toxique : les corrompus laissent une traînée (5 s) qui contamine les ennemis qui la traversent."""
    global _t_sillage, _t_contagion
    _t_sillage -= dt
    if _t_sillage <= 0:
        _t_sillage = 0.25
        for m in mons:
            if corrompu(m) and len(sillages) < 160:
                sillages.append([m.x, m.z, t + 5.0])
    _t_contagion -= dt
    if _t_contagion <= 0 and sillages:
        _t_contagion = 0.2
        for m in mons:
            if m.hp > 0 and not m.allie and not corrompu(m) and "corr" not in m.fx:
                for sx, sz, _ in sillages:
                    if abs(m.x - sx) < 45 and abs(m.z - sz) < 45:
                        injecter(m)
                        break
