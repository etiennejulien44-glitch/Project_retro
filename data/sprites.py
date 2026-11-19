# data/sprites.py -- sprites/animations disponibles dans assets/ (chargés par engine/assets.py)
#   Animation 8 directions "PixelOver" : un PNG + un JSON par direction : <dossier>/<fichier avec {d}>.png/.json
#   AJOUTER UN SPRITE = une entrée ici ; ajouter une IMAGE SIMPLE = juste la déposer dans assets/ (assets.image("x.png")).
SPRITES = {
    "businessman": dict(
        anims={"marche": ("Walk", "Businessman_Walk_dir{d}"),
               "course": ("Running", "Businessman_Running_dir{d}")},
        directions=8,
        face=4,               # numéro de direction qui regarde le joueur (portrait de l'interface)
    ),
}
IMAGES = {"arbre": "tree.png"}
AVATAR = "businessman"
