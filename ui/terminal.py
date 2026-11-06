# ui/terminal.py
import pygame
from data import equipements

class TerminalInventory:
    def __init__(self):
        # Racine à "home" pour naviguer dans inventory, option, sound
        self.current_path = ["home"]
        self.history = []
        self.history_index = 0
        self.input_text = ""
        self.jeu = None          # branché par Jeu : sert à synchroniser l'équipement
        
        # Faux système de fichiers complet
        self.fs = {
            "home": {
                "type": "dir",
                "contents": {
                    "inventory": {"type": "dir", "contents": {}},   # généré depuis data/equipements.py
                    "option": {
                        "type": "dir",
                        "contents": {
                            "fps_max":  {"size": "1MB", "type": "setting", "val": 60},
                            "vsync":    {"size": "1MB", "type": "setting", "val": "OFF"}
                        }
                    },
                    "sound": {
                        "type": "dir",
                        "contents": {
                            "master_vol": {"size": "1MB", "type": "setting", "val": "80%"}
                        }
                    }
                }
            }
        }
        
        self.output_logs = [
            "SYNTH_OS v1.08 - SECURE SHELL [SYSTEM PAUSE]",
            "Commandes: ls, cd, cat, equip, set, reset, clear, exit  (help)"
        ]

    def get_current_dir_obj(self):
        if self.current_path == ["home", "inventory"]:
            # Récupère dynamiquement la liste et la taille depuis possedees
            return {
                item_id: {"type": item_data["type"], "size": item_data["taille"]} 
                for item_id, item_data in equipements.possedees.items()
            }
        curr = self.fs
        for p in self.current_path:
            curr = curr[p]["contents"]
        return curr

    def _sync(self):
        if self.jeu is not None:
            if hasattr(self.jeu, "synchroniser_equipement"):
                self.jeu.synchroniser_equipement()
            elif hasattr(self.jeu, "synchroniser_arme"):
                self.jeu.synchroniser_arme()

    def _cmd_equipement(self, cmd, args):
        L = self.output_logs
        if cmd == "cat":
            if not args or args[0] not in equipements.possedees:
                L.append("cat: usage  cat <item_id>   (ls dans inventory pour la liste)")
                return
            item_id = args[0]
            item = equipements.possedees[item_id]
            
            # Vérification de l'équipement dans l'un des slots
            est_equipe = "EQUIPE" if item_id in equipements.equipees.values() else "range"
            L.append(f"{item['nom']} [{item['type']}] ({item['rarete'].upper()}) - {'[' + est_equipe + ']'}")
            
            for st, v in item["stats"].items():
                L.append(f"   {st:18s} = {v}")

        elif cmd == "equip":
            if args and equipements.equiper(args[0]):
                self._sync()
                slot = equipements.possedees[args[0]]["type"]
                L.append(f"{args[0]} équipée dans le slot [{slot}].")
            else:
                L.append("equip: usage  equip <item_id>   (item possédé)")

        elif cmd == "set":
            if len(args) != 3:
                stats_bornes = ", ".join(equipements.BORNES_ARMES.keys())
                L.append(f"set: usage  set <item_id> <stat> <valeur> (ex stats arme: {stats_bornes})")
                return
            try:
                ok, msg = equipements.modifier(args[0], args[1], float(args[2]))
            except ValueError:
                ok, msg = False, "valeur invalide"
            L.append(msg)
            if ok:
                self._sync()

        elif cmd == "reset":
            if args and equipements.reset_item(args[0]):
                self._sync()
                L.append(f"{args[0]} remis aux stats d'origine.")
            else:
                L.append("reset: usage  reset <item_id>")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                resultat = self.execute_command(self.input_text)
                if self.input_text.strip():
                    self.history.append(self.input_text)
                    self.history_index = len(self.history)
                self.input_text = ""
                return resultat
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_UP:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.input_text = self.history[self.history_index]
            elif event.key == pygame.K_DOWN:
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.input_text = self.history[self.history_index]
            else:
                if event.unicode:
                    self.input_text += event.unicode
        return None

    def execute_command(self, cmd_line):
        cmd_line = cmd_line.strip()
        
        if cmd_line in ["exit", "quit"]:
            return "CLOSE_TERMINAL"
            
        prompt_str = f"@user/{'/'.join(self.current_path)}~bash$> {cmd_line}"
        self.output_logs.append(prompt_str)
        
        parts = cmd_line.split()
        if not parts:
            return None
        
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "ls":
            contents = self.get_current_dir_obj()
            for name, data in contents.items():
                if data["type"] == "dir":
                    self.output_logs.append(f"  [DIR]  {name}/")
                else:
                    self.output_logs.append(f"  [{data['type']:9s}] {name} ---- {data['size']}")
            
            if "inventory" in self.current_path:
                slots_str = ", ".join([f"{slot}:{iid or 'vide'}" for slot, iid in equipements.equipees.items()])
                self.output_logs.append(f"  équipés : {slots_str}")
        
        elif cmd == "cd":
            if not args or args[0] == "~":
                self.current_path = ["home"]
            elif args[0] == "..":
                if len(self.current_path) > 1:
                    self.current_path.pop()
                else:
                    self.output_logs.append("cd: déjà à la racine (home)")
            else:
                target = args[0].rstrip("/")
                contents = self.get_current_dir_obj()
                if target in contents and contents[target]["type"] == "dir":
                    self.current_path.append(target)
                else:
                    self.output_logs.append(f"cd: dossier introuvable : {target}")
        
        elif cmd in ("cat", "equip", "set", "reset"):
            self._cmd_equipement(cmd, args)

        elif cmd == "help" or "-h" in args:
            self.output_logs.append("ls, cd <dir>, cd .., clear, exit")
            self.output_logs.append("Equipements (cd inventory) : cat <item_id>, equip <item_id>,")
            self.output_logs.append("   set <item_id> <stat> <valeur>, reset <item_id>")
        
        elif cmd == "clear":
            self.output_logs.clear()
        
        else:
            self.output_logs.append(f"zsh: commande introuvable : {cmd}")
        
        return None

    def dessiner(self, surface, font):
        largeur_ecran, hauteur_ecran = surface.get_size()
        
        w = largeur_ecran // 2
        h = hauteur_ecran // 2
        
        x = largeur_ecran - w - 20
        y = hauteur_ecran - h - 20

        term_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        term_surf.fill((10, 0, 20, 245))
        
        pygame.draw.rect(term_surf, (0, 255, 255), term_surf.get_rect(), 2)
        pygame.draw.rect(term_surf, (255, 0, 127), (0, 0, w, 24))
        title_font = pygame.font.SysFont(None, 20)
        title_surf = title_font.render("TERMINAL - BASH V1.08 [SYSTEM PAUSE]", True, (255, 255, 255))
        term_surf.blit(title_surf, (10, 4))
        
        y_offset = 30
        max_lines = (h - 60) // 18
        visible_logs = self.output_logs[-max_lines:]
        
        for log in visible_logs:
            if "@user" in log:
                color = (0, 255, 255)
            elif "[DIR]" in log:
                color = (0, 255, 100)
            elif "----" in log:
                color = (255, 220, 0)
            else:
                color = (200, 200, 200)
                
            log_surf = font.render(log, True, color)
            term_surf.blit(log_surf, (10, y_offset))
            y_offset += 18
        
        prompt_str = f"@user/{'/'.join(self.current_path)}~bash$> {self.input_text}_"
        input_surf = font.render(prompt_str, True, (255, 0, 127))
        term_surf.blit(input_surf, (10, h - 25))
        
        surface.blit(term_surf, (x, y))