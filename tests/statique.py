"""Contrôle statique : noms non définis + attributs de modules du projet inexistants.
   python tests/statique.py   -> détecte les erreurs du type  `ouvrir_coffre.coffre_proche` (NameError) après un déplacement de code."""
import ast, builtins, glob, importlib, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
try:
    import pygame  # noqa
except ImportError:
    import tests.fake_pygame as fp; fp.installer()
PROJET = {"data", "world", "engine", "ui"}
fichiers = [f for f in sorted(glob.glob("**/*.py", recursive=True)) if not f.startswith("tests") and not f.endswith("__init__.py")]
mauvais = 0
for f in fichiers:
    arbre = ast.parse(open(f, encoding="utf-8").read())
    definis = set(dir(builtins)) | {"__file__"}
    alias = {}
    for n in ast.walk(arbre):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            definis.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            definis.add(n.id)
        elif isinstance(n, ast.arg):
            definis.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            definis.add(n.name)
        elif isinstance(n, ast.ImportFrom):
            # imports relatifs (from . import x) : le paquet est le dossier du fichier
            paquet = os.path.dirname(f).replace(os.sep, ".")
            module = n.module if n.level == 0 else (paquet + ("." + n.module if n.module else ""))
            for a in n.names:
                definis.add(a.asname or a.name)
                if module and module.split(".")[0] in PROJET:
                    try:
                        alias[a.asname or a.name] = importlib.import_module(f"{module}.{a.name}")
                    except ImportError:
                        pass
        elif isinstance(n, ast.Import):
            for a in n.names:
                definis.add((a.asname or a.name).split(".")[0])
    for n in ast.walk(arbre):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in definis:
            print(f"{f}:{n.lineno}  nom non défini : {n.id}"); mauvais += 1
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias \
                and not hasattr(alias[n.value.id], n.attr):
            print(f"{f}:{n.lineno}  module sans attribut : {n.value.id}.{n.attr}"); mauvais += 1
print("OK : aucun nom / attribut manquant" if not mauvais else f"{mauvais} problème(s)")
sys.exit(1 if mauvais else 0)
