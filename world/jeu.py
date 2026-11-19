# world/jeu.py -- LE JEU : état + règles (déplacement, tir, dash, interactions, progression).
#   Aucun affichage ici : le rendu est dans engine/, l'interface dans ui/, les événements dans main.py.
import math
from data import config, boosts, controles
from data.boosts import BOOSTS, PICKUP_IDS
from engine import effets                      # le jeu DÉCLENCHE des effets visuels (dash, tirs) mais ne dessine rien
from world import entity, inventaire, butin, terrain, coffre, competences
from data.competences import COMPETENCES
from world import boss as boss_module
from world.butin import StatsBoostes
from world.entity import Joueur
from world.terrain import get_hauteur_sol, get_zone, reinitialiser_monde


class Jeu:
    def __init__(self):
        self.joueur = Joueur()
        self.stats = StatsBoostes()
        self.zone = None
        self.pause = False               # True : terminal ouvert (le jeu est figé)
        self.popup_text, self.popup_timer, self.popup_color = "", 0.0, (255, 255, 255)
        self.tir_t = 0.0                 # durée restante de l'éclair de tir (pour l'affichage)
        self.tir_fin = None              # point d'impact écran du dernier tir
        self.sprint = False
        self.vitesse_reelle = 0.0        # vitesse de déplacement réelle (hors dash) : speed_damage
        self._equip_version = -1
        self._arme_affichee = None
        self._boss_annonce = None
        self.reinitialiser()

    @property
    def dash_cd(self):
        return competences.cd.get("dash", 0.0)

    def annoncer(self, texte, couleur=(255, 255, 255), duree=2.0):
        """Message au centre bas de l'écran (affiché par ui/interface.py)."""
        self.popup_text, self.popup_color, self.popup_timer = texte, couleur, duree

    def reinitialiser(self):
        inventaire.reinitialiser()
        reinitialiser_monde()
        entity.reinitialiser_entites()
        butin.vider_butins()
        boss_module.reinitialiser_boss()
        competences.reinitialiser()
        self.stats = StatsBoostes()
        self.temps_run = 0.0
        self.couche_max = 0          # couche la plus profonde atteinte (progression / boss)
        config.cam_x, config.cam_z = config.DEPART_X, config.DEPART_Z
        config.cam_y = get_hauteur_sol(config.cam_x, config.cam_z) - 30
        config.yaw = config.pitch = config.vitesse_y = 0.0
        config.mettre_a_jour_rayons()
        self.joueur.reinitialiser()
        self.sprint = False
        self.vitesse_reelle = 0.0
        self._arme_affichee = inventaire.equipees["arme"]
        self.synchroniser_equipement(annonce=False)
        self.tir_t = 0.0
        self.tir_fin = None
        self.popup_text, self.popup_timer = "", 0.0
        self._boss_annonce = None
        self._maj_zone()

    def _maj_zone(self):
        t = config.TAILLE_CHUNKS * config.ECHELLE_GRILLE
        cx, cz = int(math.floor(config.cam_x / t)), int(math.floor(config.cam_z / t))
        self.zone = get_zone(cx, cz, config.PORTEE_CHUNKS)
        terrain.prechauffer(cx, cz, config.PORTEE_CHUNKS)    # 1 chunk voisin préparé par frame (pas de saccade)

    def regarder(self, rel_x, rel_y):
        if self.joueur.mort:
            return
        config.yaw += rel_x * controles.SENSIBILITE_SOURIS
        config.pitch = max(-85, min(85, config.pitch + rel_y * controles.SENSIBILITE_SOURIS))

    def tirer(self):
        j = self.joueur
        if boss_module.run_gagnee:
            return
        if not j.tenter_tir():
            return
        self.tir_t = 0.10
        competences.preparer_tir()                                     # portée / pénétration (range_pierce)
        mult = (self.stats.degats_mult * inventaire.multiplicateur_degats(self.sprint)
                * (1.0 + competences.bonus_arme(self.vitesse_reelle)))   # speed_damage : vitesse -> dégâts
        base_degats = config.DEGATS_TIR
        degats = config.DEGATS_TIR = base_degats * mult
        try:
            self.tir_fin, _, _ = entity.tirer_laser(self.zone["cles"], j)
        finally:
            config.DEGATS_TIR = base_degats
        competences.apres_tir(self, degats)                            # ricochet, stacking, dôme, munition en plus

    def competence(self, action):
        """Touche de compétence (onde, virus, ultime) -> world/competences.py."""
        competences.declencher_touche(self, action)

    def synchroniser_equipement(self, annonce=True):
        """Appelé dès que l'équipement change (terminal, ramassage, reset) : PV max, chargeur, annonce d'arme."""
        j = self.joueur
        self.stats.recalculer_pv_max(j)
        if j.chargeur > config.CHARGEUR_TAILLE:          # arme au chargeur plus petit : le surplus retourne en réserve
            surplus = j.chargeur - config.CHARGEUR_TAILLE
            j.chargeur = config.CHARGEUR_TAILLE
            j.reserve = min(config.MUNITIONS_RESERVE_MAX, j.reserve + surplus)
        self._equip_version = inventaire.version
        arme_id = inventaire.equipees["arme"]
        if annonce and arme_id != self._arme_affichee and arme_id in inventaire.possedees:
            it = inventaire.possedees[arme_id]
            self.annoncer(f"ARME : {it['nom']} [{it['rarete'].upper()}]", inventaire.RARETES[it["rarete"]]["couleur"], 2.0)
        self._arme_affichee = arme_id

    def cible_interaction(self):
        """Ce que la touche F ferait ici : le plus proche parmi coffre fermé / butin / pickup.
        -> (genre, objet, libellé, couleur) ou None."""
        x, z, r = config.cam_x, config.cam_z, config.RAYON_INTERACTION
        meilleur, d_min = None, r
        chest, d = coffre.coffre_proche(self.zone, x, z, r)
        if chest is not None:
            meilleur, d_min = ("coffre", chest, "Ouvrir le coffre", (255, 255, 255)), d
        for b in butin.butins_au_sol:
            d = math.hypot(b.x - x, b.z - z)
            if d < d_min:
                meilleur, d_min = ("butin", b, f"Ramasser {b.nom}", b.couleur), d
        for p in entity.pickups:
            d = math.hypot(p[0] - x, p[1] - z)
            if d < d_min:
                d_def = BOOSTS[PICKUP_IDS[int(p[2])]]
                meilleur, d_min = ("pickup", p, f"Ramasser {d_def['nom']}", d_def["pickup"]["couleur"]), d
        return meilleur

    def interagir(self):
        """Touche F : ouvre le coffre / ramasse l'objet le plus proche. Plus d'aimant ni de ramassage forcé."""
        if self.joueur.mort or boss_module.run_gagnee:
            return
        cible = self.cible_interaction()
        if cible is None:
            return
        genre, obj, _, _ = cible
        if genre == "coffre":
            self.interagir_coffre()
            return
        self.stats.messages_ramassage.clear()
        if genre == "butin":
            obj.notifie = False                       # on veut le message "trop lourd" à chaque essai
            if butin.appliquer(obj.def_id, self.stats, self.joueur, obj):
                butin.butins_au_sol[:] = [b for b in butin.butins_au_sol if b is not obj]
        else:
            if butin.appliquer(PICKUP_IDS[int(obj[2])], self.stats, self.joueur):
                entity.pickups[:] = [p for p in entity.pickups if p is not obj]
        if not self.stats.messages_ramassage:             # refus sans message (munitions / PV déjà pleins...)
            self.stats.messages_ramassage.append(("DEJA AU MAXIMUM", (255, 120, 120)))

    def interagir_coffre(self):
        butins = coffre.ouvrir_coffre_proche(self.zone, config.cam_x, config.cam_z)
        if butins:
            self.annoncer("COFFRE : " + " + ".join(b.nom for b in butins), butins[0].couleur, 2.5)
        return butins

    def dash(self):
        """Compétence DASH (touche A) : bond en avant qui blesse tout sur le trajet. Niveau 0 = verrouillé."""
        j = self.joueur
        if j.mort or boss_module.run_gagnee or competences.dash_verrouille():
            return
        lvl = competences.niveau("dash")
        if lvl <= 0:
            self.annoncer("DASH verrouillé : investis des PC (terminal : cd skills ; up dash)", (255, 120, 120), 2.0)
            return
        if not competences.pret("dash"):
            self.annoncer(f"DASH : {self.dash_cd:.0f}s", (255, 120, 120), 1.0)
            return
        dist = (2.0 + 0.25 * lvl) * config.DASH_UNITES_PAR_CELLULE      # portée du dash : +0.25 cellule par niveau
        rad = math.radians(config.yaw)
        dx, dz = math.sin(rad), math.cos(rad)
        x0, z0 = config.cam_x, config.cam_z
        etapes = max(1, int(dist // 25))
        x, z = x0, z0
        for _ in range(etapes):                           # par petits pas : les décors solides bloquent le dash
            x, z = terrain.repousser(x + dx * dist / etapes, z + dz * dist / etapes, config.cam_y + 30)
        config.cam_x, config.cam_z = x, z
        effets.fov.declencher_dash()                                  # FOV dynamique : la perspective s'étire
        for f in (0.2, 0.4, 0.6, 0.8):                                # traînée d'étincelles le long du dash
            effets.etincelles((x0 + (x - x0) * f, config.cam_y + 10, z0 + (z - z0) * f), (0, 255, 255), n=5,
                              vitesse=120.0, taille=14.0)
        effets.onde(x, z, amp=config.ONDE_DASH_AMP, vitesse=520.0, longueur=340.0)
        nb = entity.degats_zone_segment(self.zone["cles"], x0, z0, x, z, config.DASH_RAYON * competences.rayon_aoe(),
                                        competences.degats("dash"), j)       # formule universelle (branche Mobilité)
        competences.cd["dash"] = COMPETENCES["dash"]["cd"]
        self.annoncer(f"DASH ! {nb} cible(s)" if nb else "DASH !", (0, 255, 255), 1.2)

    def recommencer_si_fini(self):
        """Entrée : relance la partie après game over / victoire."""
        if self.joueur.mort or boss_module.run_gagnee:
            self.reinitialiser()

    def recharger(self):
        if self.joueur.mort or boss_module.run_gagnee:
            self.reinitialiser()
        else:
            self.joueur.lancer_recharge()

    def mettre_a_jour(self, dt, temps, avant, cote, saut, sprint=False):
        """avant/cote : -1, 0 ou 1 (touches) ; saut/sprint : booléens."""
        config.mettre_a_jour_rayons()
        j = self.joueur
        if inventaire.version != self._equip_version:       # équipement modifié depuis la dernière frame
            self.synchroniser_equipement()
        j.mettre_a_jour(dt)
        effets.maj(dt, temps, self.sprint)
        competences.mettre_a_jour(self, dt)                 # recharges, effets, ultimes (avant l'IA des monstres)
        entity.mettre_a_jour_zaps(dt)
        self.stats.update(dt, j)
        self.tir_t = max(0.0, self.tir_t - dt)
        self.popup_timer = max(0.0, self.popup_timer - dt)
        if j.mort or boss_module.run_gagnee:
            return
        self.temps_run += dt

        self.sprint = bool(sprint) and (avant != 0 or cote != 0)
        vitesse = 250 * self.stats.vitesse_mult * (1.0 + config.BONUS_VITESSE) * competences.mult_vitesse() * dt
        x_av, z_av = config.cam_x, config.cam_z
        if self.sprint:
            vitesse *= config.SPRINT_MULT
        rad = math.radians(config.yaw)
        config.cam_x += (avant * math.sin(rad) + cote * math.cos(rad)) * vitesse
        config.cam_z += (avant * math.cos(rad) - cote * math.sin(rad)) * vitesse

        config.cam_x, config.cam_z = terrain.repousser(config.cam_x, config.cam_z, config.cam_y + 30)
        self.vitesse_reelle = math.hypot(config.cam_x - x_av, config.cam_z - z_av) / dt if dt > 0 else 0.0

        sol = get_hauteur_sol(config.cam_x, config.cam_z) - 30

        if saut and abs(config.cam_y - sol) < 2:
            config.vitesse_y = -300 * self.stats.saut_mult
        config.vitesse_y += config.gravite * config.GRAVITE_MULT * dt
        config.cam_y += config.vitesse_y * dt
        if config.cam_y > sol:
            config.cam_y = sol
            config.vitesse_y = 0

        self._maj_zone()

        # Progression : nouvelle couche atteinte -> annonce
        couche = terrain.get_couche_monde(config.cam_x, config.cam_z)
        if couche > self.couche_max:
            self.couche_max = couche
            biome = terrain.BIOMES[terrain.COUCHES[couche]]
            self.annoncer(f"COUCHE {couche + 1}/{terrain.NB_COUCHES} - {biome['nom']}", biome["couleur_grille"], 3.5)

        # Dernière couche atteinte -> boss final (fin de run quand il tombe)
        if couche >= terrain.NB_COUCHES - 1 and boss_module.lancer_boss_final(config.cam_x, config.cam_z):
            self.annoncer("!!! BOSS FINAL !!!", (255, 40, 40), 4.0)
        butin.ramasser_butins(j, self.stats, config.cam_x, config.cam_z, dt)

        entity.mettre_a_jour_monstres(dt, self.zone["cles"], j, temps)
        entity.mettre_a_jour_projectiles(dt, j)
        entity.mettre_a_jour_pickups(j, dt, self.stats)
        boss_module.mettre_a_jour_boss(dt, j, temps)
        boss_module.mettre_a_jour_projectiles_boss(dt, j)
        b = boss_module.boss
        if b is not None and b is not self._boss_annonce and not b.final:       # annonce d'un nouveau boss
            self._boss_annonce = b
            self.annoncer(f"!!! {b.nom} !!!", (255, 60, 160), 3.0)
