# ui/terminal.py -- terminal du jeu (TAB pour l'ouvrir/compléter).
#   Sortie COLORÉE (équipements à la couleur de leur rareté), colonnes alignées, retour à la ligne automatique,
#   défilement fluide (molette / PageHaut / PageBas), curseur clignotant.
#   Une ligne de log = liste de segments (texte, couleur[, colonne]) ; une colonne = position alignée (en caractères).
import os
import time

import pygame

from data import config, reglages
from data.competences import BRANCHES, COMPETENCES
from data.raretes import RARETES
from data.stats import formater
from engine.textes import police, texte
from ui.panneau_equipement import lignes_stats, NOMS_SLOTS
from world import competences, inventaire

# --- palette -----------------------------------------------------------------
C_TXT, C_DIM, C_LABEL = (205, 205, 220), (120, 120, 145), (150, 150, 175)
C_PROMPT, C_DIR, C_OK, C_ERR = (0, 235, 255), (90, 255, 140), (120, 255, 150), (255, 100, 100)
C_ROSE, C_JAUNE, C_VAL = (255, 70, 170), (255, 225, 90), (245, 245, 255)

COMMANDES = ["cat", "cd", "clear", "equip", "exit", "help", "ls", "reset", "respec", "rm", "set", "stats",
             "ult", "unequip", "up"]
MOLETTE = getattr(pygame, "MOUSEWHEEL", None)


def seg_item(it, avec_uid=None):
    """Segments d'un objet : son nom à la couleur de sa rareté."""
    return (it["nom"], RARETES[it["rarete"]]["couleur"])


class Ligne:
    __slots__ = ("segs", "_wrap")

    def __init__(self, segs):
        self.segs = segs
        self._wrap = {}

    def texte(self):
        return "".join(s[0] for s in self.segs)

    def __contains__(self, mot):               # permet  "abc" in ligne
        return mot in self.texte()


class TerminalInventory:
    def __init__(self):
        self._surf = None
        self._tab_ligne = None
        self.current_path = ["home"]
        self.history, self.history_index, self.input_text = [], 0, ""
        self.jeu = None                        # branché par ui/interface.py : synchronise l'équipement
        self.scroll = self.scroll_cible = 0.0  # en lignes visuelles depuis le bas (0 = bas)
        self._max_scroll, self._nb_lignes, self._dernier_t = 0.0, 0, time.perf_counter()
        self.fs = {"home": {"type": "dir", "contents": {
            "inventory": {"type": "dir", "contents": {}},     # généré depuis world/inventaire.py
            "skills": {"type": "dir", "contents": {}},        # généré depuis data/competences.py
            "option": {"type": "dir", "contents": {}},        # généré depuis data/reglages.py
            "sound": {"type": "dir", "contents": {"master_vol": {"size": "1MB", "type": "setting", "val": "80%"}}},
        }}}
        self.output_logs = []
        self.log(("SYNTH_OS v1.09 - SECURE SHELL [SYSTEM PAUSE]", C_ROSE))
        self.log(("help", C_PROMPT), (" : commandes   -   ", C_DIM), ("TAB", C_JAUNE), (" : complétion   -   ", C_DIM),
                 ("molette", C_JAUNE), (" : défilement", C_DIM))
        self.log(("cd inventory", C_PROMPT), (" équipements   ", C_DIM), ("cd skills", C_PROMPT),
                 (" compétences   ", C_DIM), ("cd option", C_PROMPT), (" réglages", C_DIM))

    # ------------------------------------------------------------------ journal
    def log(self, *segs):
        """log(("texte", couleur), ("autre", couleur, colonne), ...) ou log("simple texte")."""
        if len(segs) == 1 and isinstance(segs[0], str):
            segs = ((segs[0], C_TXT),)
        self.output_logs.append(Ligne(list(segs)))

    def ok(self, msg):
        self.log((msg, C_OK))

    def err(self, msg):
        self.log((msg, C_ERR))

    def textes(self):
        return [l.texte() for l in self.output_logs]

    # ------------------------------------------------------------------ "système de fichiers"
    def get_current_dir_obj(self):
        if self.current_path == ["home", "option"]:
            return {nom: {"type": "setting", "size": reglages.texte(nom), "doc": spec["doc"]}
                    for nom, spec in reglages.REGLAGES.items()}
        if self.current_path == ["home", "inventory"]:
            return {uid: {"type": it["type"], "size": it["taille"], "rarete": it["rarete"]}
                    for uid, it in inventaire.possedees.items()}
        if self.current_path == ["home", "skills"]:
            return {cid: {"type": "skill"} for cid in COMPETENCES}
        curr = self.fs
        for p in self.current_path:
            curr = curr[p]["contents"]
        return curr

    def _sync(self):
        if self.jeu is not None and hasattr(self.jeu, "synchroniser_equipement"):
            self.jeu.synchroniser_equipement()

    @property
    def dans(self):
        return self.current_path[-1]

    # ------------------------------------------------------------------ COMMANDES
    def cmd_ls(self, args):
        if self.dans == "inventory":
            return self._ls_inventaire()
        if self.dans == "skills":
            return self._ls_skills()
        for name, d in self.get_current_dir_obj().items():
            if d["type"] == "dir":
                self.log(("  ", C_TXT), (f"{name}/", C_DIR))
            elif "doc" in d:
                self.log(("  ", C_TXT), (name, C_PROMPT, 2), ("=", C_DIM, 16), (str(d["size"]), C_VAL, 18),
                         (d["doc"], C_DIM, 30))
            else:
                self.log(("  ", C_TXT), (name, C_PROMPT, 2), (str(d.get("size", d.get("val", ""))), C_DIM, 16))

    def _ls_inventaire(self):
        equipes = set(inventaire.equipees.values())
        if not inventaire.possedees:
            self.log(("  (inventaire vide)", C_DIM))
        else:
            self.log(("  SLOT", C_DIM, 4), ("OBJET", C_DIM, 16), ("RARETÉ", C_DIM, 40), ("POIDS", C_DIM, 52), ("ID", C_DIM, 60))
        for uid, it in inventaire.possedees.items():
            col = RARETES[it["rarete"]]["couleur"]
            eq = uid in equipes
            self.log(("●" if eq else " ", C_OK, 1), (it["type"], col, 4), (it["nom"], col, 16),
                     (it["rarete"], col, 40), (it["taille"], C_LABEL, 52), (uid, C_VAL if eq else C_DIM, 60))
        self.log(("  ● équipé", C_OK), (f"     poids {inventaire.poids_porte()}/{inventaire.poids_max()} MB", C_LABEL))

    def _ls_skills(self):
        self.log(("  PC disponibles : ", C_LABEL), (str(competences.points), C_JAUNE),
                 ("      ultime équipé : ", C_LABEL), (competences.ultime or "aucun", C_JAUNE))
        for bid, b in BRANCHES.items():
            self.log((f"  {b['nom'].upper()}  (spec x{b['spec_weight']})", b["couleur"]))
            for cid, c in COMPETENCES.items():
                if c["branche"] != bid:
                    continue
                niv, mx = competences.niveaux.get(cid, 0), competences.maximum(cid)
                if c["type"] == "ultime":
                    genre = "ultime" + (" ★" if competences.ultime == cid else "")
                elif "cd" in c:
                    genre = "actif"
                else:
                    genre = "passif" if c["type"] == "standard" else "stat"
                self.log((cid, b["couleur"] if niv else C_DIM, 4), (f"{niv}/{mx}", C_OK if niv else C_DIM, 28),
                         (f"{competences.cout(cid)} PC", C_LABEL, 36), (genre, C_LABEL, 44))

    def cmd_cd(self, args):
        if not args or args[0] == "~":
            self.current_path = ["home"]
        elif args[0] == "..":
            if len(self.current_path) > 1:
                self.current_path.pop()
            else:
                self.err("cd: déjà à la racine (home)")
        else:
            cible = args[0].rstrip("/")
            contenu = self.get_current_dir_obj()
            if cible in contenu and contenu[cible]["type"] == "dir":
                self.current_path.append(cible)
            else:
                self.err(f"cd: dossier introuvable : {cible}")

    def cmd_cat(self, args):
        if self.dans == "option":
            nom = args[0] if args else ""
            if nom not in reglages.REGLAGES:
                return self.err("cat: usage  cat <option>")
            self.log((nom, C_PROMPT), (" = ", C_DIM), (reglages.texte(nom), C_VAL), ("   " + reglages.REGLAGES[nom]["doc"], C_DIM))
            return self.log(("   " + reglages.description_valeurs(nom), C_LABEL))
        if self.dans == "skills":
            return self._cat_skill(args[0] if args else "")
        uid = inventaire.resoudre(args[0]) if args else None
        if uid is None:
            return self.err("cat: usage  cat <item_id>   (ls dans inventory pour la liste)")
        it = inventaire.possedees[uid]
        col = RARETES[it["rarete"]]["couleur"]
        eq = uid in inventaire.equipees.values()
        self.log((it["nom"], col), (f"   [{it['rarete'].upper()}]", col), ("   ÉQUIPÉ" if eq else "   rangé", C_OK if eq else C_DIM))
        self.log((f"   {uid}  -  slot {it['type']}  -  {it['taille']}", C_DIM))
        for lib, val in lignes_stats(it["type"], it):
            self.log(("     " + lib, C_LABEL), (val, C_VAL, 26))

    def _cat_skill(self, cid):
        if cid not in COMPETENCES:
            return self.err("cat: usage  cat <compétence>   (ls pour la liste)")
        c, b = COMPETENCES[cid], BRANCHES[COMPETENCES[cid]["branche"]]
        niv, eff = competences.niveaux.get(cid, 0), competences.niveau(cid)
        self.log((c["nom"], b["couleur"]), (f"   [{b['nom']} - {c['type']}]", C_DIM))
        self.log(("   niveau ", C_LABEL), (f"{niv}/{competences.maximum(cid)}", C_OK if niv else C_ERR),
                 (f"  (effectif {eff})" if eff != niv else "", C_JAUNE), (f"     coût {competences.cout(cid)} PC/niveau", C_LABEL))
        if "cd" in c:
            self.log(("   recharge ", C_LABEL), (f"{c['cd']:.0f}s", C_VAL), ("   touche ", C_LABEL), (c.get("touche", "-"), C_VAL))
        if "power_capa" in c and eff > 0:
            self.log(("   dégâts actuels ", C_LABEL), (f"{competences.degats(cid):.1f}", C_JAUNE),
                     (f"   (power {c['power_capa']}, base {competences.base_dmg():.0f})", C_DIM))
        self.log(("   " + c["doc"], C_TXT))
        if eff == 0:
            self.log(("   VERROUILLÉ : niveau 0 = inutilisable (up " + cid + ")", C_ERR))

    def cmd_equip(self, args):
        uid = inventaire.resoudre(args[0]) if args else None
        inventaire.derniere_erreur = ""
        if uid and inventaire.equiper(uid):
            self._sync()
            it = inventaire.possedees[uid]
            self.log(("  équipé : ", C_OK), seg_item(it), (f"   → slot {it['type']}", C_DIM))
        else:
            self.err("equip: " + (inventaire.derniere_erreur or "usage  equip <item_id>   (item possédé)"))

    def cmd_unequip(self, args):
        inventaire.derniere_erreur = ""
        if args and inventaire.desequiper(args[0]):
            self._sync()
            self.ok(f"  {args[0]} déséquipé (reste dans l'inventaire).")
        else:
            self.err("unequip: " + (inventaire.derniere_erreur or "usage  unequip <slot|item_id>"))

    def cmd_rm(self, args):
        if not args:
            return self.err("rm: usage  rm <item_id>   (jette l'objet et libère du poids)")
        ok, msg = inventaire.jeter(args[0])
        (self.ok if ok else self.err)(msg)
        if ok:
            self._sync()

    def cmd_reset(self, args):
        if args and inventaire.reset_item(args[0]):
            self._sync()
            self.ok(f"  {args[0]} : stats re-générées.")
        else:
            self.err("reset: usage  reset <item_id>")

    def cmd_set(self, args):
        if self.dans == "option":
            if len(args) != 2:
                return self.err("set: usage  set <option> <valeur>   (ls pour la liste)")
            ok, msg = reglages.definir(args[0], args[1])
            return (self.ok if ok else self.err)(msg)
        if len(args) != 3:
            return self.err(f"set: usage  set <item_id> <stat> <valeur>  (stats arme : {', '.join(inventaire.BORNES_ARMES)})")
        try:
            ok, msg = inventaire.modifier(args[0], args[1], float(args[2]))
        except ValueError:
            ok, msg = False, "valeur invalide"
        (self.ok if ok else self.err)(msg)
        if ok:
            self._sync()

    def cmd_stats(self, args):
        t = inventaire.stats_actives or inventaire.calculer_stats()
        self.log(("  Poids  ", C_LABEL), (f"{inventaire.poids_porte()}/{inventaire.poids_max()} MB", C_VAL))
        self.log(("  Réduction dégâts ", C_LABEL), (f"-{config.REDUCTION_DEGATS * 100:.0f}%", C_VAL),
                 ("   PV bonus ", C_LABEL), (f"+{config.BONUS_HP:.0f}", C_VAL))
        self.log(("  Vitesse ", C_LABEL), (f"+{config.BONUS_VITESSE * 100:.0f}%", C_VAL),
                 ("   Dégâts ", C_LABEL), (f"x{inventaire.multiplicateur_degats():.2f}", C_VAL))
        for k, v in t.items():
            if v and k not in ("reduction_dmgs", "augmentation_hp", "vitesse", "poids_max_buff"):
                lib, val = formater(k, v)
                self.log(("  " + lib, C_LABEL), (val, C_JAUNE, 22))

    def cmd_up(self, args):
        if not args:
            return self.err("up: usage  up <compétence> [niveaux]   (cd skills ; ls)")
        try:
            n = int(args[1]) if len(args) > 1 else 1
        except ValueError:
            return self.err("up: nombre de niveaux invalide")
        ok, msg = competences.acheter(args[0], n)
        (self.ok if ok else self.err)("  " + msg)

    def cmd_ult(self, args):
        if not args:
            return self.err("ult: usage  ult <ultime>   (un seul ultime actif : suppression_rapide, controle_total, ...)")
        ok, msg = competences.equiper_ultime(args[0])
        (self.ok if ok else self.err)("  " + msg)

    def cmd_respec(self, args):
        self.ok("  " + competences.respec())

    def cmd_clear(self, args):
        self.output_logs.clear()

    def cmd_help(self, args):
        for cmd, desc in (("ls / cd <dir> / cd ..", "naviguer (inventory, skills, option)"),
                          ("cat <id>", "détails d'un objet / d'une option / d'une compétence"),
                          ("equip <id> / unequip <slot|id>", "équiper / retirer"), ("rm <id>", "jeter un objet"),
                          ("stats", "bonus cumulés de l'équipement"), ("set <id> <stat> <val>", "modifier un objet (inventory)"),
                          ("set <option> <valeur>", "régler une option (option)"), ("reset <id>", "re-tirer les stats"),
                          ("up <compétence> [n]", "dépenser des PC (cd skills)"), ("ult <ultime>", "équiper l'ultime"),
                          ("respec", "rembourser tous les PC"), ("clear / exit", "vider / fermer")):
            self.log(("  " + cmd, C_PROMPT, 2), (desc, C_DIM, 34))

    # ------------------------------------------------------------------ AUTO-COMPLÉTION (TAB)
    def _candidats(self, cmd, idx, deja):
        """Valeurs possibles pour l'argument n°idx de `cmd` (selon le dossier courant)."""
        if cmd == "cd":
            return [n for n, d in self.get_current_dir_obj().items() if d["type"] == "dir"] + [".."] if idx == 0 else []
        if cmd == "up":
            return list(COMPETENCES) if idx == 0 else []
        if cmd == "ult":
            return [c for c, d in COMPETENCES.items() if d["type"] == "ultime"] if idx == 0 else []
        if self.dans == "skills":
            return list(COMPETENCES) if cmd == "cat" and idx == 0 else []
        if self.dans == "option":
            if cmd in ("cat", "set") and idx == 0:
                return list(reglages.REGLAGES)
            if cmd == "set" and idx == 1 and deja and deja[0] in reglages.REGLAGES:
                spec = reglages.REGLAGES[deja[0]]
                return ["on", "off"] if isinstance(spec["defaut"], bool) else [str(c) for c in spec.get("choix", [])]
            return []
        equipes = set(inventaire.equipees.values())
        if cmd in ("cat", "rm", "reset") and idx == 0:
            return list(inventaire.possedees)
        if cmd == "equip" and idx == 0:
            return [u for u in inventaire.possedees if u not in equipes]
        if cmd == "unequip" and idx == 0:
            return list(inventaire.SLOTS) + [u for u in inventaire.possedees if u in equipes]
        if cmd == "set":
            if idx == 0:
                return list(inventaire.possedees)
            if idx == 1 and deja and deja[0] in inventaire.possedees:
                return list(inventaire.possedees[deja[0]]["stats"])
        return []

    def completer(self, ligne):
        """-> (nouvelle_ligne, [candidats]).  Un seul candidat : complété.  Plusieurs : préfixe commun."""
        mots = ligne.split(" ")
        prefixe = mots[-1]
        cands = COMMANDES if len(mots) == 1 else self._candidats(mots[0], len(mots) - 2, mots[1:-1])
        cands = sorted(c for c in cands if c.lower().startswith(prefixe.lower()))
        if not cands:
            return ligne, []
        base = " ".join(mots[:-1] + [""]) if len(mots) > 1 else ""
        if len(cands) == 1:
            return base + cands[0] + ("" if (mots[0] == "cd" and len(mots) > 1) else " "), cands
        return base + os.path.commonprefix(cands), cands

    def _tab(self):
        nouvelle, cands = self.completer(self.input_text)
        if len(cands) > 1 and nouvelle == self.input_text:           # aucun progrès : on liste les possibilités
            self.log(("  " + "   ".join(cands), C_JAUNE))
        return nouvelle

    # ------------------------------------------------------------------ événements
    def handle_event(self, event):
        if MOLETTE is not None and event.type == MOLETTE:
            self.scroll_cible = max(0.0, min(self._max_scroll, self.scroll_cible + event.y * 3))
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                resultat = self.execute_command(self.input_text)
                if self.input_text.strip():
                    self.history.append(self.input_text)
                    self.history_index = len(self.history)
                self.input_text = ""
                self.scroll_cible = 0.0
                return resultat
            elif event.key == pygame.K_TAB:
                self.input_text = self._tab()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == getattr(pygame, "K_PAGEUP", -1):
                self.scroll_cible = min(self._max_scroll, self.scroll_cible + 8)
            elif event.key == getattr(pygame, "K_PAGEDOWN", -1):
                self.scroll_cible = max(0.0, self.scroll_cible - 8)
            elif event.key == pygame.K_UP:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.input_text = self.history[self.history_index]
            elif event.key == pygame.K_DOWN:
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.input_text = self.history[self.history_index]
            elif event.unicode and event.unicode.isprintable():
                self.input_text += event.unicode
        return None

    def execute_command(self, cmd_line):
        cmd_line = cmd_line.strip()
        if cmd_line in ("exit", "quit"):
            return "CLOSE_TERMINAL"
        self.log(("@user/" + "/".join(self.current_path), C_PROMPT), ("~bash$> ", C_ROSE), (cmd_line, C_VAL))
        parts = cmd_line.split()
        if not parts:
            return None
        cmd, args = parts[0], parts[1:]
        if cmd == "help" or "-h" in args:
            self.cmd_help(args)
        elif cmd in COMMANDES and hasattr(self, "cmd_" + cmd):
            getattr(self, "cmd_" + cmd)(args)
        else:
            self.err(f"zsh: commande introuvable : {cmd}   (help)")
        return None

    # ------------------------------------------------------------------ affichage
    def _wrap(self, ligne, largeur_px, taille):
        """Découpe une ligne en lignes visuelles (listes de segments (txt, couleur, x_px|None)). Mise en cache."""
        cle = (largeur_px, taille)
        if cle in ligne._wrap:
            return ligne._wrap[cle]
        font = police(taille)
        cw = font.size("0")[0]
        if any(len(s) > 2 for s in ligne.segs):                      # ligne à colonnes : alignement, pas de césure
            out = [[(s[0], s[1], s[2] * cw if len(s) > 2 else None) for s in ligne.segs]]
        else:
            out, cur, x = [], [], 0
            for txt, col in ((s[0], s[1]) for s in ligne.segs):
                for mot in txt.replace("\t", "  ").split(" "):
                    w = font.size(mot + " ")[0]
                    if x + w > largeur_px and cur:
                        out.append(cur)
                        cur, x = [], 0
                        mot = mot if mot else ""
                    cur.append((mot + " ", col, None))
                    x += w
            out.append(cur)
        ligne._wrap[cle] = out
        return out

    def dessiner(self, surface, font=None):
        W, H = surface.get_size()
        k = H / 1080.0
        taille, pas = max(16, int(24 * k)), max(20, int(28 * k))
        w, h = int(W * 0.50), int(H * 0.58)
        x, y = 20, H - h - 20
        if self._surf is None or self._surf.get_size() != (w, h):
            self._surf = pygame.Surface((w, h), pygame.SRCALPHA)
        s = self._surf
        s.fill((8, 4, 22, 222))
        pygame.draw.rect(s, (0, 235, 255), s.get_rect(), 2)
        pygame.draw.rect(s, C_ROSE, (0, 0, w, 28))
        s.blit(texte("TERMINAL  -  BASH V1.09   [PAUSE]", 20, (255, 255, 255)), (10, 6))

        # lignes visuelles (avec retour à la ligne), les plus récentes en bas
        zone_h = h - 28 - pas - 16
        visibles = zone_h // pas
        lignes = []
        for l in self.output_logs[-300:]:
            lignes.extend(self._wrap(l, w - 24, taille))
        n = len(lignes)
        self._max_scroll = max(0.0, n - visibles)
        now = time.perf_counter()
        dt, self._dernier_t = min(0.1, now - self._dernier_t), now
        if n > self._nb_lignes and self.scroll_cible < 0.5:          # nouvelles lignes : elles « glissent » vers le haut
            self.scroll += (n - self._nb_lignes)
        self._nb_lignes = n
        self.scroll_cible = min(self.scroll_cible, self._max_scroll)
        self.scroll += (self.scroll_cible - self.scroll) * min(1.0, 14.0 * dt)       # défilement amorti
        if abs(self.scroll - self.scroll_cible) < 0.01:
            self.scroll = self.scroll_cible

        base = int(self.scroll)                                       # lignes entières décalées + fraction en pixels
        frac = int((self.scroll - base) * pas)
        s.set_clip((4, 30, w - 8, zone_h))
        fin = n - base
        debut = max(0, fin - visibles - 2)
        cw = police(taille).size("0")[0]
        for i in range(debut, fin):
            yy = 30 + zone_h - (fin - i) * pas + frac + 2
            xx = 12
            for txt, col, xpx in lignes[i]:
                img = texte(txt, taille, col)
                if xpx is not None:
                    xx = 12 + xpx
                s.blit(img, (xx, yy))
                xx += img.get_width()
        s.set_clip(None)
        if self._max_scroll > 0:                                       # curseur de défilement
            haut = max(18, int(zone_h * visibles / max(1, n)))
            pos = int((zone_h - haut) * (1.0 - self.scroll / self._max_scroll))
            pygame.draw.rect(s, (70, 70, 110), (w - 6, 30 + pos, 3, haut))
            if self.scroll_cible > 0.5:
                s.blit(texte("▼ PageBas / molette", 18, C_DIM), (w - 170, h - pas - 18))

        # ligne de saisie
        yi = h - pas - 6
        pygame.draw.line(s, (60, 60, 100), (8, yi - 4), (w - 8, yi - 4), 1)
        chemin = "@user/" + "/".join(self.current_path)
        a = texte(chemin, taille, C_PROMPT)
        s.blit(a, (12, yi))
        b = texte("~bash$> ", taille, C_ROSE)
        s.blit(b, (12 + a.get_width(), yi))
        cx = 12 + a.get_width() + b.get_width()
        if self.input_text:
            t = texte(self.input_text, taille, C_VAL)
            s.blit(t, (cx, yi))
            cx += t.get_width()
        if int(now * 2) % 2 == 0:                                      # curseur clignotant
            pygame.draw.rect(s, C_VAL, (cx + 1, yi + 2, max(8, cw // 2), taille - 4))
        surface.blit(s, (x, y))
