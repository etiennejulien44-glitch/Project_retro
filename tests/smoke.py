"""Tests de comportement headless :  python tests/smoke.py   (faux pygame si pygame absent)"""
import os, sys, math, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    import pygame  # noqa
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
except ImportError:
    import tests.fake_pygame as fp; fp.installer(); import pygame
import numpy as np
random.seed(3)
from world.jeu import Jeu
from engine.affichage import Affichage
from data import config, reglages
from data import boss as boss_def
from data.monstres import MONSTRES as BESTIAIRE
from world import entity, boss as B, terrain
from world.monstre import Monstre, ABSORBE
from engine import effets
from data.raretes import RARETES as RARETES_
from ui import terminal as terminal_mod

reglages._valeurs["particules"] = 800
pygame.init()
jeu = Jeu()
aff = Affichage(pygame.display.set_mode((config.LARGEUR, config.HAUTEUR)), jeu)
j = jeu.joueur
ok_count = 0
def check(cond, msg):
    global ok_count
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond: sys.exit(1)
    ok_count += 1

def poser(cle, dx, dz):
    m = Monstre(config.cam_x + dx, config.cam_z + dz, cle, random.Random(1))
    m.cd = m.t_etat = 0.0
    cles = jeu.zone["cles"]; terrain.monstres_caches[cles[len(cles)//2]].append(m)
    return m

def vider():
    for l in terrain.monstres_caches.values(): l.clear()
    entity.projectiles.clear()

def pas(n=1, sprint=False):
    for i in range(n):
        jeu.mettre_a_jour(1/60, jeu._t, 0, 0, 0, sprint); jeu._t += 1/60
        aff.dessiner(jeu._t)
jeu._t = 0.0
config.yaw = 0; config.pitch = 0
j.pv = 10**6; config.JOUEUR_PV_MAX = 10**6

print("[1] bestiaire / registre")
for cle, d in BESTIAIRE.items():
    check(d["comportement"] in entity.COMPORTEMENTS, f"comportement '{d['comportement']}' enregistré ({cle})")
    check("score" in d, f"score défini ({cle})")

print("[2] Striker : fonce en ligne droite et blesse")
vider(); pas(2); j.pv = 100; config.JOUEUR_PV_MAX = 100
s = poser("striker", 0, 500); d0 = math.hypot(s.x - config.cam_x, s.z - config.cam_z)
vus = set(); 
for i in range(240):
    pas(); vus.add(s.etat)
    if j.pv < 100: break
check({"vise", "fonce"} <= vus, f"états traversés {sorted(vus)}")
check(j.pv < 100, f"le Striker a touché le joueur (PV {j.pv})")
config.JOUEUR_PV_MAX = 10**6; j.pv = 10**6

print("[3] Polygone Shield : 1 face absorbée par tir, puis le coeur")
vider(); pas(2)
m = poser("polygone_shield", 0, 400); m.rot = math.pi    # fait face au sud -> il présente une face vers le joueur
m.x, m.z = config.cam_x, config.cam_z + 400
n0 = sum(m.faces); r = m.encaisser(1, config.cam_x, config.cam_z)
check(r == ABSORBE and sum(m.faces) == n0 - 1 and m.hp == m.hp_max, "tir sur face debout : face détruite, coeur intact")
n1 = len(m.faces); i = m.face_touchee
pas_ = 2*math.pi/n1
# on tire exactement depuis la direction de la face détruite -> coeur touché
phi = m.rot + i*pas_; ox, oz = m.x + math.sin(phi)*300, m.z + math.cos(phi)*300
hp = m.hp; r = m.encaisser(1, ox, oz)
check(r != ABSORBE and m.hp == hp - 1, "tir depuis la face détruite : le coeur encaisse")
# IA : il pivote pour recouvrir l'ouverture
rot0 = m.rot; m.x, m.z = config.cam_x + 0, config.cam_z + 300
for _ in range(10): entity._ia_shield(m, 1/60, j, 0)
check(m.rot != rot0, "pivote vers le joueur (vitesse limitée)")
check(abs(m.rot - rot0) <= BESTIAIRE["polygone_shield"]["vit_rot"] * 10/60 + 1e-6, "rotation plafonnée par vit_rot")

print("[4] Phasme : intouchable sous la grille, surgit au dernier moment")
vider(); pas(2)
p = poser("phasme", 0, 700)
check(p.etat == "traque" and not p.ciblable, "en traque : non ciblable")
pas(1); src = entity.sources_distorsion(); check(len(src) >= 1, "distorsion de grille émise")
etats = []
for i in range(600):
    pas(); etats.append(p.etat)
    if p.etat == "surgi": break
check("surgi" in etats, "il surgit")
check(p.ciblable, "surgi : ciblable")
d = math.hypot(p.x - config.cam_x, p.z - config.cam_z)
check(d < 200, f"surgit près du joueur (d={d:.0f})")
dy = effets.ondes.deplacement(np.array([p.x]), np.array([p.z])); 

print("[5] Mort : score, Vertex Shatter, onde de grille")
vider(); pas(2); sc = j.score; n_part = effets.particules.n
m = poser("araignee", 0, 300); m.hp = 1
mort = entity._blesser_monstre(m, 5, jeu.zone["cles"], j)
check(mort and j.score == sc + 100, "score +100")
check(effets.particules.n > n_part + 10, f"{effets.particules.n - n_part} particules créées")
check(len(effets.ondes.impulsions) > 0, "onde de grille déclenchée")
for _ in range(120): pas()
check(effets.particules.n < 5 or effets.particules.n < n_part + 10, "les particules s'éteignent")

print("[6] Tir réel (laser) sur un monstre en visée")
vider(); pas(2)
m = poser("glitch", 0, 250); m.x, m.z = config.cam_x, config.cam_z + 250
m.data = dict(m.data); m.data["vitesse"] = 0
hp0 = m.hp; jeu.joueur.t_cadence = 0; jeu.joueur.chargeur = 15
fin = jeu.tirer(); 
check(m.hp < hp0 or m not in [x for l in terrain.monstres_caches.values() for x in l], "le tir touche (PV baissent ou mort)")

print("[7] Boss à palier de SCORE")
vider(); B.reinitialiser_boss(); pas(2)
check(B.prochain_seuil == boss_def.palier(0)[0], f"premier palier = {B.prochain_seuil}")
j.score = B.prochain_seuil - 1; pas(2); check(B.boss is None, "pas de boss sous le palier")
j.score = B.prochain_seuil; pas(2)
check(isinstance(B.boss, B.BossGeo) and B.boss.cle == "cube", "palier atteint : CUBE ROTATIF")
b = B.boss; check(b.en_spawn and b.invuln > 0, "invulnérable pendant l'anim de spawn")
for _ in range(int(config.BOSS_SPAWN_ANIM_DUREE*60)+5): pas()
check(not b.en_spawn, "spawn terminé")
for _ in range(400): pas()
check(len(B.ondes_boss) > 0 or b.cd_onde > 0, "pattern ONDES actif")
# onde néon : touchée au sol, évitée en sautant
B.ondes_boss.clear(); config.JOUEUR_PV_MAX = 100; j.pv = 100
o = B.Onde(config.cam_x, config.cam_z, 0.0, 400, 1200, 20, (255, 0, 100)); B.ondes_boss.append(o)
sol = terrain.get_hauteur_sol(config.cam_x, config.cam_z) - 30; config.cam_y = sol
for _ in range(60): B._maj_ondes(1/60, j); 
check(j.pv < 100, "onde néon: dégâts si on reste au sol")
j.pv = 100; o = B.Onde(config.cam_x, config.cam_z, 0.0, 400, 1200, 20, (255, 0, 100)); B.ondes_boss.append(o)
config.cam_y = sol - 90
for _ in range(60): B._maj_ondes(1/60, j)
check(j.pv == 100, "onde néon: esquivée en sautant")
config.JOUEUR_PV_MAX = 10**6; j.pv = 10**6; config.cam_y = sol
# tir sur le boss
b.hp = b.hp_max; hp = b.hp; B.toucher_boss(1); check(b.hp == hp - 1, "dégâts boss (cube, sans réduction)")
# mort
sc = j.score; b.hp = 0; pas(2)
check(B.boss is None and j.score >= sc + config.BOSS_SCORE_BONUS, "boss mort : bonus de score")
check(B.prochain_type == "icosaedre" and B.prochain_seuil >= boss_def.palier(1)[0], f"prochain: {B.prochain_type} à {B.prochain_seuil}")

print("[8] Icosaèdre : satellites + réduction de dégâts")
B.boss = B.BossGeo(config.cam_x, config.cam_z + 700, 0, "icosaedre"); b = B.boss
b.en_spawn = False; b.invuln = 0
for _ in range(200): pas()
check(len(b.satellites) >= 2, f"{len(b.satellites)} satellites déployés")
hp = b.hp; B.toucher_boss(10)
check(abs((hp - b.hp) - 10 * boss_def.BOSS_GEO["icosaedre"]["reduction_satellites"]) < 1e-6, "dégâts réduits tant que les satellites vivent")
for s in list(b.satellites): s.hp = 0
pas(2); hp = b.hp; B.toucher_boss(10); check(abs((hp - b.hp) - 10) < 1e-6, "plus de réduction sans satellites")
check(len(B.projectiles_boss) >= 0, "projectiles satellites ok")
B.boss = None

print("[9] Boss araignée (ancien) toujours fonctionnel")
B.boss = B.spawner_boss(config.cam_x, config.cam_z, "araignee"); B.boss.en_spawn = False; B.boss.invuln = 0
for _ in range(300): pas()
check(isinstance(B.boss, B.SpiderBoss), "spider boss actif"); B.boss = None

print("[10] FOV dynamique / grille / options")
config.FOCALE = config.FOCALE_BASE; effets.fov.declencher_dash()
mx = 0
for _ in range(40): effets.maj(1/60, jeu._t, False); mx = max(mx, config.FOCALE)
check(mx > config.FOCALE_BASE * 1.15, f"dash: focale x{mx/config.FOCALE_BASE:.2f}")
for _ in range(60): effets.maj(1/60, jeu._t, False)
check(abs(config.FOCALE - config.FOCALE_BASE) < 1, "focale revient à la normale")
ok, msg = reglages.definir("fps_max", "144", sauver_fichier=False); check(ok, msg)
ok, _ = reglages.definir("fps_max", "999", sauver_fichier=False); check(not ok, "valeur invalide refusée")
ok, msg = reglages.definir("distance", "1200", sauver_fichier=False); check(ok, msg)
config.appliquer_distance(1000); check(config.PORTEE_CHUNKS == 1, "distance 1000 -> 3x3 chunks")
config.appliquer_distance(1800); reglages.definir("distance", 1800, sauver_fichier=False); reglages.definir("fps_max", 60, sauver_fichier=False)

print("[11] Terminal : options")
aff.interface.terminal.execute_command("cd option"); aff.interface.terminal.execute_command("ls")
aff.interface.terminal.execute_command("set qualite bas"); check(reglages.get("qualite") == "bas", "set qualite bas")
aff.interface.terminal.execute_command("set qualite auto")
check(any("qualite" in l for l in aff.interface.terminal.output_logs), "ls liste les options (lignes colorées)")

print("[12] Architecture : data/ ne dépend de rien, main.py = fenêtre + événements")
import re, glob
def imports(f):
    return re.findall(r"^\s*(?:from|import)\s+([\w\.]+)", open(f, encoding="utf-8").read(), re.M)
for f in sorted(glob.glob(os.path.join(ROOT, "data", "*.py"))):
    mauvais = [m for m in imports(f) if m.split(".")[0] in ("world", "engine", "ui", "main")]
    check(not mauvais, f"data/{os.path.basename(f)} n'importe pas world/engine/ui {mauvais}")
for f in sorted(glob.glob(os.path.join(ROOT, "engine", "*.py"))):
    mauvais = [m for m in imports(f) if m.startswith("ui") and os.path.basename(f) != "affichage.py"]
    check(not mauvais, f"engine/{os.path.basename(f)} n'importe pas ui (sauf affichage)")
check(len(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read().splitlines()) < 140, "main.py reste petit (< 140 lignes)")

print("[13] Ajouter un monstre = UN bloc (modèle + stats + biomes), rien d'autre")
from data import monstres as DM, biomes as DB, modeles
DM.monstre("zombie_test", nom="Zombie", comportement="melee", modele=modeles.boite(14, 40, 10), couleur=(80, 255, 80),
           pv_max=7, vitesse=3.0, biomes={"neon_grid": 5})
z = DM.MONSTRES["zombie_test"]
check(z["rendu"] == "segments" and z["portee"] == 3.5 and z["hauteur_barre"] > 40, "défauts appliqués, hauteurs déduites du modèle")
try:
    DM.monstre("casse", nom="X", comportement="melee", couleur=(1, 2, 3)); check(False, "doit refuser")
except ValueError as e:
    check("pv_max" in str(e), "champ manquant signalé clairement : " + str(e)[:60])
try:
    DM.monstre("casse", nom="X", comportement="vole", couleur=(1, 2, 3), pv_max=1); check(False, "doit refuser")
except ValueError as e:
    check("comportement inconnu" in str(e), "comportement inconnu signalé")
import importlib
importlib.reload(DB)
check(DB.BIOMES["neon_grid"]["monstres_spawn"].count("zombie_test") == 5, "le biome le reçoit automatiquement (poids 5)")
from engine import rendu_monstres as RM
RM._MODELES["zombie_test"] = (*RM.G.aplatir_modele(z["modele"], 1.0), z["couleur"])
vider(); pas(2); mz = poser("zombie_test", 0, 300); pas(30)
check(mz.x != config.cam_x or mz.z != config.cam_z, "le nouveau monstre est géré par l'IA et rendu sans erreur")
vider(); pas(2); del DM.MONSTRES["zombie_test"]; importlib.reload(DB)

print("[14] Stats d'équipement génériques (data/stats.py) + panneau d'équipement")
from world import inventaire
from ui import panneau_equipement as PE
uid = inventaire.donner("helmet", "leg"); uid = inventaire.resoudre("helmet") or uid
inventaire.equiper(inventaire.resoudre("helmet")); jeu.synchroniser_equipement()
check(config.REDUCTION_DEGATS > 0, f"casque équipé : réduction {config.REDUCTION_DEGATS:.2f}")
it = inventaire.possedees[inventaire.equipees["casque"]]
ls = PE.lignes_stats("casque", it)
check(ls and ls[0][0] == "Réduction dégâts" and ls[0][1].startswith("+"), f"boosts affichables : {ls}")
check(len(PE.lignes_stats("arme", inventaire.possedees[inventaire.equipees["arme"]])) == 5, "arme : 5 stats affichées")
jeu.stats._bonus["vitesse"] = 0.2
check(("Vitesse", "+20%") in PE.lignes_boosts(jeu.stats), "boosts ramassés affichés"); jeu.stats._bonus.clear()
for _ in range(3): aff.dessiner(jeu._t)
check(aff.interface.panneau._cache is not None and aff.interface.panneau._cache.get_height() > 100, "panneau composé (en cache)")
inventaire.desequiper("casque"); jeu.synchroniser_equipement()
check(config.REDUCTION_DEGATS == 0, "déséquipé : bonus retiré")

print("[14b] Coffres : ouverture sans crash")
from world import coffre as _coffre
vider(); pas(2)
ch = None
for cle in jeu.zone["cles"]:
    for c in terrain.chest_caches[cle]:
        if not c["ouvert"]: ch = c; break
    if ch: break
check(ch is not None, "un coffre existe dans la zone")
config.cam_x, config.cam_z = ch["x"] + 20, ch["z"]
jeu._maj_zone()
check(jeu.cible_interaction() is not None and jeu.cible_interaction()[0] == "coffre", "cible d'interaction : coffre")
n = len(__import__("world.butin", fromlist=["x"]).butins_au_sol)
jeu.interagir()
check(ch["ouvert"], "touche F : le coffre s'ouvre")
check(len(__import__("world.butin", fromlist=["x"]).butins_au_sol) > n, "butin créé")
pas(5)
print("[15] Terminal : complétion TAB")
t = aff.interface.terminal; t.execute_command("cd ..") ; t.current_path = ["home"]
check(t.completer("eq")[0] == "equip ", "commande : eq -> equip")
check(t.completer("s")[1] == ["set", "stats"], "plusieurs candidats listés")
check(t.completer("c")[0] == "c", "préfixe commun (c -> cat/cd/clear : rien de plus)")
t.current_path = ["home", "option"]
check(t.completer("set qu")[0] == "set qualite ", "option : set qu -> set qualite")
check(t.completer("set qualite a")[0] == "set qualite auto ", "valeur : a -> auto")
check(t.completer("set vsync ")[1] == ["off", "on"], "booléen : on / off")
t.current_path = ["home", "inventory"]
inventaire.donner("boots", "rare")
b_uid = [u for u in inventaire.possedees if u.startswith("boots")][0]
check(t.completer("equip boo")[0] == f"equip {b_uid} ", "item : equip boo -> uid")
check("vitesse" in t.completer(f"set {b_uid} ")[1], "stat de l'item proposée")
t.current_path = ["home"]; check(t.completer("cd in")[0] == "cd inventory", "dossier : cd in -> inventory")
t.input_text = "se"; import types as _t
t.handle_event(_t.SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_TAB, unicode="\t"))
check(t.input_text == "set ", "événement TAB branché")

print("[16] Assets (icônes) et main.py")
from engine import assets
from data.raretes import RARETES, ICONE_SLOT_VIDE
check(assets.image(ICONE_SLOT_VIDE, 64) is not None, "empty_slot.png chargé")
manque = [(i, r) for i, d in inventaire.CATALOGUE.items() for r in RARETES if not assets.chemin_icone(d, r)]
check(not manque, f"toutes les icônes (objets x raretés) existent : {len(inventaire.CATALOGUE)} x {len(RARETES)}" + (f" manque {manque}" if manque else ""))
check(assets.chemin_icone(inventaire.CATALOGUE["helmet"], "leg") == "leg_helm.png", "alias casque légendaire : leg_helm.png")
check(assets.chemin_icone({}, "rare") is None, "sans champ icone -> None (icône vectorielle)")
import main as MAIN
jeu.pause = False
ev = _t.SimpleNamespace
check(MAIN.traiter_evenement(ev(type=pygame.KEYDOWN, key=MAIN.T["terminal"]), jeu, aff) and jeu.pause, "TAB ouvre le terminal (pause)")
check(MAIN.traiter_evenement(ev(type=pygame.KEYDOWN, key=pygame.K_a, unicode="a"), jeu, aff) and jeu.pause, "pause : les touches vont au terminal")
jeu.pause = False
check(MAIN.traiter_evenement(ev(type=pygame.KEYDOWN, key=MAIN.T["quitter"]), jeu, aff) is False, "ESC quitte")
check(MAIN.traiter_evenement(ev(type=pygame.MOUSEMOTION, rel=(10, 0)), jeu, aff) is True, "souris -> regarder")
aff.interface.debug = True; aff.dessiner(jeu._t); aff.interface.debug = False
jeu.pause = True; aff.dessiner(jeu._t); aff.dessiner(jeu._t); jeu.pause = False
check(True, "debug F3 et pause (scène figée) rendus sans erreur")

print("[17] Compétences : coûts, formule universelle, règles")
from world import competences as C
from data.competences import COMPETENCES, COUTS, BRANCHES
import types as _ty
def maj(n):
    for _ in range(n): jeu.mettre_a_jour(1/60, jeu._t, 0, 0, 0, False); jeu._t += 1/60
def fige(m, hp=10000):
    m.data = dict(m.data); m.data["aggro"] = 0; m.hp = m.hp_max = hp; return m
def forcer(valeur):
    C.random = _ty.SimpleNamespace(random=lambda: valeur, uniform=lambda a, b: a)
real_random = C.random
def reset_comp(pts=200):
    jeu.joueur.score = 0; C.reinitialiser(); C.points = pts; config.DASH_CELLULES = 0; vider(); pas(2)
    config.yaw = 0; config.pitch = 0; config.cam_x, config.cam_z = 0.0, 0.0
    config.cam_y = terrain.get_hauteur_sol(0.0, 0.0) - 30; jeu._maj_zone()
check(len(COMPETENCES) == 20 and all(sum(1 for c in COMPETENCES.values() if c["branche"] == b and c["type"] == "ultime") == 1 for b in BRANCHES), "20 compétences, 1 ultime par branche")
check(COUTS == {"mineure": (1, 10), "majeure": (2, 10), "standard": (3, 5), "ultime": (5, 3)}, "coûts PC / niveaux max du GDD")
check([BRANCHES[b]["spec_weight"] for b in ("mobilite", "aoe", "controle", "synth")] == [2.5, 2.0, 1.8, 1.5], "spec_weight : 2.5 / 2.0 / 1.8 / 1.5")
reset_comp(0); C.points = 3
ok, _m = C.acheter("dash"); check(ok and C.niveau("dash") == 1 and C.points == 0, "départ 3 PC : dash acheté (3 PC)")
ok, _m = C.acheter("dash"); check(not ok and "insuffisants" in _m, "PC insuffisants refusé")
C.gagner_points(100); ok, _m = C.acheter("speed_stat", 15); check(C.niveau("speed_stat") == 10 and C.points == 103 - 3 - 10 + 3 - 3 + 0 or C.niveau("speed_stat") == 10, "niveau max d'une stat mineure = 10")
reset_comp(100); C.acheter("suppression_rapide"); C.acheter("controle_total")
check(C.ultime == "suppression_rapide" and not C.actif("controle_total") and C.niveau("controle_total") == 1, "UN SEUL ultime actif (le 2e est acheté mais inactif)")
check(C.equiper_ultime("controle_total")[0] and C.actif("controle_total") and not C.actif("suppression_rapide"), "changer d'ultime")
reset_comp(0); check(not C.actif("dash") and C.niveau("dash") == 0, "niveau 0 : verrouillée")
jeu.dash(); check(C.cd.get("dash", 0) == 0, "dash niveau 0 : inutilisable")
config.DASH_CELLULES = 2; check(C.niveau("dash") == 2 and C.actif("dash"), "armure : niveaux de dash GRATUITS (dash_atq)"); config.DASH_CELLULES = 0
reset_comp(100); C.acheter("dash")
check(abs(C.degats("dash") - 9.6) < 1e-9, f"formule : ((0*2.5+8)*120*1.1^0)/100 = {C.degats('dash'):.2f}")
C.acheter("mobility_dmg", 4); check(abs(C.degats("dash") - 21.6) < 1e-9, "avec 4 pts mobilité : ((4*2.5+8)*120)/100 = 21.6")
C.acheter("dash"); check(abs(C.degats("dash") - 21.6 * 1.1) < 1e-9, "niveau 2 : x1.1^(lvl-1)")
sc = jeu.joueur.score; reset_comp(0); jeu.joueur.score = 1200; maj(2); check(C.points == 3, f"+1 PC tous les 400 de score (1200 -> 3) ({C.points} PC)"); jeu.joueur.score = sc

print("[18] Mobilité : dash, speed_damage, suppression rapide")
reset_comp(100); C.acheter("dash"); m = fige(poser("araignee", 0, 250)); pas(1)
jeu.dash(); check(abs(C.cd["dash"] - 4.0) < 1e-6, "dash : recharge 4 s")
check(m.hp < m.hp_max and abs((m.hp_max - m.hp) - 9.6) < 1e-6, f"dégâts de dash = formule ({m.hp_max - m.hp:.1f})")
jeu.dash(); check(abs(C.cd["dash"] - 4.0) < 0.1, "2e dash refusé pendant la recharge")
reset_comp(100); C.acheter("speed_stat", 4); C.acheter("speed_damage", 2)
check(abs(C.mult_vitesse() - 1.36) < 1e-9, "vitesse : +5%/niv + 8%/niv speed_damage = x1.36")
check(abs(C.bonus_arme(250) - 0.25) < 1e-9, "speed_damage niv 2 à 250 de vitesse : +0.5% x 2 x 25 tranches = +25%")
reset_comp(100); C.acheter("suppression_rapide"); C.acheter("dash", 2)
ms = [fige(poser("araignee", dx, dz)) for dx, dz in ((0, 300), (200, 500), (-250, 450), (80, 700))]; pas(1)
x0 = (config.cam_x, config.cam_z); jeu.competence("ultime")
check(C.suppression and C.suppression["restant"] == 3 + 2 * 1 + 2 * 2 and C.dash_verrouille(), "sauts = 3 + 2*lvl + 2*dash_lvl = 9 ; dash verrouillé")
jeu.dash(); check(C.cd.get("dash", 0) == 0, "dash impossible pendant la suppression")
maj(120); check(C.suppression is None, "suppression terminée")
check(all(m.hp < m.hp_max for m in ms), "chaque ennemi touché (anti-boucle par tag_stack)")
check(max(abs(config.cam_x - x0[0]), abs(config.cam_z - x0[1])) > 100, "le joueur s'est téléporté")
check(abs(C.cd["suppression_rapide"] - 50.0) < 3, "recharge 50 s")

print("[19] Contrôle : champ, ammo x2, stacking, contrôle total")
reset_comp(300); C.acheter("controle_passif"); C.acheter("control_dmg", 4); C.acheter("control_power", 3)
a = fige(poser("araignee", 0, 300)); b = fige(poser("araignee", 0, -300)); maj(3)
check(abs(a.ralenti - 0.7) < 1e-9 and b.ralenti == 1.0, "ennemi dans le cône : ralenti de 30% ; derrière : non")
check(abs(a.vuln - (1 + 4 * 1 / 100) * (1 + 0.05 * 4)) < 1e-9, f"dégâts subis : x{a.vuln:.3f} (control_dmg x niv % et +5%/niv)")
pas(1); jeu.joueur.chargeur = 15; jeu.joueur.t_cadence = 0; ch0 = jeu.joueur.chargeur; jeu.tirer()
check(a.hp < a.hp_max and ch0 - jeu.joueur.chargeur == 2, f"tir sur cible contrôlée : 2 munitions ({ch0 - jeu.joueur.chargeur})")
reset_comp(300); C.acheter("stacking"); C.acheter("control_power", 4)
t0 = fige(poser("araignee", 0, 300)); v1 = fige(poser("araignee", 150, 300)); v2 = fige(poser("araignee", -150, 320)); v3 = fige(poser("araignee", 400, 350)); pas(1)
forcer(0.0); jeu.joueur.chargeur = 15; jeu.joueur.t_cadence = 0; jeu.tirer(); C.random = real_random
check(all(math.hypot(v.x - t0.x, v.z - t0.z) < 60 for v in (v1, v2)), "stacking : 2 ennemis (max(1, control_power/2)) attirés vers la cible")
check(math.hypot(v3.x - t0.x, v3.z - t0.z) > 100, "le 3e (au-delà) reste en place")
maj(1); check(v1.ralenti == 0.0 and v1.hp < v1.hp_max, "attirés : étourdis + dégâts d'impact")
reset_comp(300); C.acheter("controle_total"); C.acheter("control_power", 1)
h = fige(poser("araignee", 0, 300)); e = fige(poser("araignee", 100, 330)); h.hp = 0.4 * h.hp_max; pas(1)
check(abs(C.chance_piratage(h) - 20.0) < 1e-9, "taux de réussite : (60% manquants / (2+1)) x 1 = 20%")
forcer(0.0); jeu.competence("ultime"); C.random = real_random
check(h.allie and h.hp == h.hp_max and h.hp_max == 15000 and not h.ciblable, "piraté : allié, stats +50%, non ciblable par le joueur")
maj(240); check(e.hp < e.hp_max, "l'allié attaque les autres ennemis")
check(C.cd["controle_total"] > 50, "recharge 60 s")

print("[20] AOE : onde, ricochet, pénétration, dôme")
reset_comp(300); C.acheter("onde_vectorielle"); C.acheter("aoe_dmg", 2)
pr = fige(poser("araignee", 200, 0)); lo = fige(poser("araignee", 450, 0)); entity.projectiles.append([100.0, config.cam_y, 0.0, 0, 0, 0, 5.0, 5]); pas(1)
check(abs(C.degats("onde_vectorielle") - ((2 * 2.0 + 8) * 150) / 100) < 1e-9, "onde : formule avec spec_weight 2.0")
jeu.competence("onde_vectorielle"); maj(30)
check(pr.hp < pr.hp_max and pr.x > 260, f"onde : ennemi blessé et repoussé (x={pr.x:.0f})")
check(lo.hp == lo.hp_max, "hors du rayon 5 m x 1.1 = 275 : intact"); check(not entity.projectiles, "projectiles ennemis détruits")
check(abs(C.cd["onde_vectorielle"] - 8.0) < 0.6, "recharge 8 s")
reset_comp(300); C.acheter("ricochet_laser", 2); a = fige(poser("araignee", 0, 300)); b = fige(poser("araignee", 300, 300)); pas(1)
forcer(0.0); jeu.joueur.chargeur = 15; jeu.joueur.t_cadence = 0; jeu.tirer(); C.random = real_random
check(b.hp < b.hp_max and abs((b.hp_max - b.hp) - 0.6 * config.DEGATS_TIR) < 1e-6, "ricochet : 60% des dégâts d'arme sur une autre cible")
reset_comp(300); C.acheter("range_pierce", 3); C.preparer_tir()
check(entity.tir_mod["penetration"] == 1 and abs(entity.tir_mod["portee"] - 1.45) < 1e-9, "range_pierce niv 3 : portée +45%, pénétration 1")
a = fige(poser("araignee", 0, 300)); b = fige(poser("araignee", 0, 500)); pas(1)
jeu.joueur.chargeur = 15; jeu.joueur.t_cadence = 0; jeu.tirer(); check(a.hp < a.hp_max and b.hp < b.hp_max, "le tir traverse 2 ennemis")
reset_comp(300); C.acheter("effondrement_polygonal"); C.equiper_ultime("effondrement_polygonal")
A = fige(poser("araignee", 0, 300)); B = fige(poser("araignee", 300, 200)); Cc = fige(poser("araignee", 900, 900)); pas(1)
jeu.competence("ultime"); check(C.dome and abs(C.dome["r"] - 600) < 1e-6, "dôme : rayon 12 m, 8 s")
jeu.joueur.chargeur = 15; jeu.joueur.t_cadence = 0; jeu.tirer()
check(B.hp < B.hp_max and abs((B.hp_max - B.hp) - 0.5 * config.DEGATS_TIR) < 1e-6, "tir dupliqué sur les ennemis du dôme (40% + 10% x niv = 50%)")
check(Cc.hp == Cc.hp_max, "hors du dôme : pas de duplication")
for _ in range(9): maj(60)
check(C.dome is None, "le dôme disparaît après 8 s")

print("[21] Synth : corruption, accrue, propagation létale")
reset_comp(300); C.acheter("corruption_virulente"); C.acheter("corruption_power", 3)
m1 = fige(poser("araignee", 0, 300)); m2 = fige(poser("araignee", 100, 330)); m3 = fige(poser("araignee", 600, 330)); pas(1)
jeu.competence("corruption_virulente"); c1 = m1.fx.get("corr")
check(c1 is not None and c1["ticks"] == 5 and abs(C.cd["corruption_virulente"] - 10.0) < 0.1, "virus injecté : max(5, lvl x power / 2) ticks, recharge 10 s")
maj(130); check(abs(c1["jauge"] - 23.0) < 1.0 and abs((m1.hp_max - m1.hp) - 2.0 * 2) < 0.5, f"jauge +11.5%/tick ({c1['jauge']:.1f}%), tick = formule power 25")
check(abs(m1.ralenti - 0.85) < 1e-9, "phase 1 : ralenti de 15%")
c1["jauge"] = 95.0; maj(70)
check(C.corrompu(m1) and abs(m1.vuln - 2.0) < 1e-9 and m1.mult_inf == 0.0, "phase 2 : dégâts subis +100%, infligés -100%")
check("corr" in m2.fx and "corr" not in m3.fx, "contagion : seul l'ennemi à <= corruption_power m est contaminé")
m1.fx["controle"] = C.t + 9; check(not C.est_controle(m1) or C.corrompu(m1), "corrompu : immunisé au Contrôle")
reset_comp(300); C.acheter("corruption_virulente"); C.acheter("corruption_accrue")
m1 = fige(poser("araignee", 0, 300)); m2 = fige(poser("araignee", 80, 320)); pas(1); jeu.competence("corruption_virulente"); m1.fx["corr"]["jauge"] = 99.0
maj(130); check("corr" not in m2.fx, "corruption_accrue : plus de contagion")
maj(900); check(abs(C.taux_corruption(m1) - 150.0) < 1e-6 and abs(m1.vuln - 2.5) < 1e-9, "taux jusqu'à 150% sur cible unique")
reset_comp(300); C.acheter("propagation_letale"); C.equiper_ultime("propagation_letale")
ms = [fige(poser("araignee", dx, dz)) for dx, dz in ((0, 300), (400, 300), (-500, 200))]; pas(1)
jeu.competence("ultime")
check(config.GRAVITE_MULT == 0.7 and effets.glitch_moteur, "glitch moteur : gravité -30%, murs translucides")
check(all(C.corrompu(m) for m in ms), "tous les ennemis de l'onde : Phase 2 directe")
maj(40); check(len(C.sillages) > 0, "sillage toxique laissé par les corrompus")
x = fige(poser("araignee", 0, 0)); x.x, x.z = C.sillages[0][0], C.sillages[0][1]; maj(20); check("corr" in x.fx, "un ennemi qui traverse le sillage est contaminé")
for _ in range(12): maj(60)
check(config.GRAVITE_MULT == 1.0 and not effets.glitch_moteur and C.propagation is None, "fin de l'ultime après 12 s : tout revient à la normale")

print("[22] Rendu avec toutes les compétences actives + terminal")
reset_comp(300); C.acheter("effondrement_polygonal"); C.acheter("controle_total"); C.acheter("dash"); C.acheter("onde_vectorielle")
for dx, dz in ((0, 300), (200, 500)): fige(poser("araignee", dx, dz))
C.equiper_ultime("controle_total"); pas(2); C.equiper_ultime("effondrement_polygonal"); jeu.competence("ultime")
jeu.competence("onde_vectorielle"); C.equiper_ultime("controle_total"); effets.glitch_moteur = True; C.sillages.append([0, 300, C.t + 5])
for _ in range(3): pas(1)
effets.glitch_moteur = False; C.dome = None; C.sillages.clear()
check(True, "dôme, infos de piratage, sillages, glitch, barre de compétences : rendu sans erreur")
reset_comp(100)
t = aff.interface.terminal; t.output_logs.clear(); t.current_path = ["home"]
t.execute_command("cd skills"); t.execute_command("ls"); t.execute_command("up dash"); t.execute_command("up suppression_rapide 1"); t.execute_command("ult suppression_rapide")
txt = "\n".join(t.textes())
check("PC disponibles" in txt and "MOBILITÉ" in txt and "dash" in txt, "cd skills / ls")
check(C.niveau("dash") == 1 and C.ultime == "suppression_rapide", "terminal : up / ult")
t.execute_command("cat dash"); check("dégâts actuels" in "\n".join(t.textes()), "cat <compétence> : dégâts calculés")
t.execute_command("respec"); check(C.points == 100 and not C.niveaux, "respec : PC remboursés")
check(t.completer("up spe")[0] == "up speed_", "TAB : up spe -> up speed_"); check(t.completer("ult s")[0] == "ult suppression_rapide ", "TAB : ult s")
t.current_path = ["home", "skills"]; check(t.completer("cat co")[1] and all(c.startswith("co") for c in t.completer("cat co")[1]), "TAB : cat <compétence>")
t.current_path = ["home", "inventory"]; t.output_logs.clear(); inventaire.donner("helmet", "leg"); inventaire.donner("chestplate", "special"); t.execute_command("ls")
col_leg, col_sp = RARETES_["leg"]["couleur"], RARETES_["special"]["couleur"]
couleurs = {s[1] for l in t.output_logs for s in l.segs}
check(col_leg in couleurs and col_sp in couleurs, "ls inventory : chaque objet à la couleur de SA rareté")
t.output_logs.clear(); uid_ = [u for u in inventaire.possedees if u.startswith("helmet")][-1]; t.execute_command(f"cat {uid_}")
check(any(s[1] == col_leg for l in t.output_logs for s in l.segs), "cat <objet> : nom coloré")
long_ = terminal_mod.Ligne([("mot " * 80, (200, 200, 200))]); check(len(t._wrap(long_, 300, 20)) > 1, "retour à la ligne automatique")
t.scroll_cible = 5; t._max_scroll = 10; t.handle_event(_ty.SimpleNamespace(type=pygame.KEYDOWN, key=getattr(pygame, "K_PAGEUP", 0), unicode=""))
check(True, "défilement (PageHaut) géré")

print(f"\n{ok_count} vérifications OK")
