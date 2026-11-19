# data/reglages.py
# ============================================================================
#  OPTIONS JOUEUR (performances / affichage) -- persistées dans reglages.json
#  AJOUTER UNE OPTION = ajouter UNE entrée dans REGLAGES (+ un écouteur si elle doit agir en direct).
#  Utilisées par : data/config.py (résolution, distance), main.py (fps, vsync, plein écran),
#  engine/qualite.py, engine/effets.py, et le terminal (cd option ; ls ; set <nom> <valeur>).
#  Ce module ne dépend d'AUCUN autre module du jeu (il est importé par config.py).
# ============================================================================
import json
import os

_FICHIER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reglages.json")

REGLAGES = {
    "fps_max":     dict(defaut=60, choix=[0, 30, 60, 90, 120, 144, 240],
                        doc="FPS maximum (0 = illimité)"),
    "vsync":       dict(defaut=False, doc="synchronisation verticale (on/off)"),
    "plein_ecran": dict(defaut=False, doc="plein écran (on/off, touche F11)"),
    "distance":    dict(defaut=1800, min=800, max=3000,
                        doc="distance d'affichage du monde (unités). Moins = plus de FPS"),
    "qualite":     dict(defaut="auto", choix=["auto", "bas", "moyen", "haut"],
                        doc="qualité visuelle ; auto = s'adapte aux FPS en direct"),
    "particules":  dict(defaut=500, min=0, max=1500, doc="nombre max de particules simultanées"),
    "resolution":  dict(defaut="1920x1080", choix=["1920x1080", "1600x900", "1280x720", "960x540"],
                        doc="résolution INTERNE du rendu (appliquée au prochain lancement)"),
    "fx_grille":   dict(defaut=True, doc="ondulation de la grille (on/off)"),
    "fx_fov":      dict(defaut=True, doc="FOV dynamique sur dash / sprint (on/off)"),
}

_valeurs = {k: v["defaut"] for k, v in REGLAGES.items()}
_ecouteurs = {}          # nom -> [fonctions(valeur)]


def _charger():
    try:
        with open(_FICHIER, "r", encoding="utf-8") as f:
            brut = json.load(f)
    except (OSError, ValueError):
        return
    for nom, val in brut.items():
        if nom in REGLAGES:
            ok, v = _convertir(nom, val)
            if ok:
                _valeurs[nom] = v


def _convertir(nom, val):
    """-> (ok, valeur_typée). Accepte aussi des chaînes (saisie terminal)."""
    spec = REGLAGES[nom]
    defaut = spec["defaut"]
    try:
        if isinstance(defaut, bool):
            if isinstance(val, str):
                s = val.strip().lower()
                if s in ("on", "true", "1", "oui", "yes"):
                    return True, True
                if s in ("off", "false", "0", "non", "no"):
                    return True, False
                return False, None
            return True, bool(val)
        if isinstance(defaut, int):
            v = int(float(val))
            if "choix" in spec and v not in spec["choix"]:
                return False, None
            if "min" in spec:
                v = max(spec["min"], min(spec["max"], v))
            return True, v
        v = str(val).strip().lower() if nom != "resolution" else str(val).strip().lower()
        if "choix" in spec and v not in spec["choix"]:
            return False, None
        return True, v
    except (TypeError, ValueError):
        return False, None


def get(nom):
    return _valeurs[nom]


def definir(nom, valeur, sauver_fichier=True):
    """-> (ok, message). Applique la valeur et prévient les écouteurs."""
    if nom not in REGLAGES:
        return False, f"option inconnue : {nom}  (cd option ; ls)"
    ok, v = _convertir(nom, valeur)
    if not ok:
        return False, f"valeur invalide pour {nom} : {valeur}   ({description_valeurs(nom)})"
    _valeurs[nom] = v
    for fn in _ecouteurs.get(nom, ()):
        fn(v)
    if sauver_fichier:
        sauver()
    note = "  (au prochain lancement)" if nom == "resolution" else ""
    return True, f"{nom} = {texte(nom)}{note}"


def sur_changement(nom, fonction):
    _ecouteurs.setdefault(nom, []).append(fonction)


def sauver():
    try:
        with open(_FICHIER, "w", encoding="utf-8") as f:
            json.dump(_valeurs, f, indent=2)
    except OSError:
        pass


def texte(nom):
    v = _valeurs[nom]
    if isinstance(v, bool):
        return "ON" if v else "OFF"
    if nom == "fps_max" and v == 0:
        return "illimité"
    return str(v)


def description_valeurs(nom):
    s = REGLAGES[nom]
    if isinstance(s["defaut"], bool):
        return "on / off"
    if "choix" in s:
        return "valeurs : " + ", ".join(str(c) for c in s["choix"])
    return f"entier {s['min']} à {s['max']}"


_charger()
