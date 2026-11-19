# boosts.py
# ============================================================================
#  AJOUTER UN BOOST / ITEM = ajouter UNE entrée dans BOOSTS (plus bas). Rien d'autre.
#
#   nom, rarete   : affichage
#   effet         : "stat" | "vie_max" | "auto_regen" | "munitions" | "soin" | "equipement" (+ item="<id catalogue>")
#                   (nouveau type d'effet = une petite fonction dans EFFETS)
#   valeur        : intensité (+0.15 = +15% pour "stat")
#   stat, cap, label, hud : pour effet "stat" (nom de la stat, plafond, texte, couleur HUD)
#   tables        : {"classique": poids, "prismatique": poids, ...} -> dans quels coffres il tombe
#   pickup        : (optionnel) objet tournant au sol : modele, echelle, couleur, drop (chance
#                   de drop par monstre tué). Sans "pickup" -> pyramide de la couleur de rareté.
#  Lire une stat côté jeu : stats.mult("vitesse") -> 1.0 + bonus cumulé (world/butin.py).
#  Ce fichier ne contient QUE des définitions ; l'application des effets est dans world/butin.py.
# ============================================================================
from enum import Enum
from . import config
from .modeles import MODELE_MUNITIONS, MODELE_SOINS
from .coffres import COFFRES
from .armes import ARMES
from .armures import ARMURES


# =============================================================
#  Raretés
# =============================================================
class Rarete(Enum):
    VERT = 0
    BLEU = 1
    JAUNE = 2
    ROUGE = 3


COULEURS_RARETE = {
    Rarete.VERT:  (80, 255, 120),
    Rarete.BLEU:  (80, 180, 255),
    Rarete.JAUNE: (255, 220, 80),
    Rarete.ROUGE: (255, 70, 100),
}


# =============================================================
#  Registre des boosts
# =============================================================
BOOSTS = {
    "MUNITIONS_V": dict(
        nom=f"Munitions +{config.PACK_MUNITIONS}", rarete=Rarete.VERT, effet="munitions",
        valeur=config.PACK_MUNITIONS, tables={"classique": config.POIDS_CS_MUNITIONS},
        pickup=dict(modele=MODELE_MUNITIONS, echelle=3.0, couleur=(60, 240, 255),
                    drop=config.DROP_MUNITIONS)),
    "SOIN_V": dict(
        nom=f"Soin +{config.PACK_SOIN} PV", rarete=Rarete.VERT, effet="soin",
        valeur=config.PACK_SOIN, tables={"classique": config.POIDS_CS_SOIN},
        pickup=dict(modele=MODELE_SOINS, echelle=3.0, couleur=(120, 255, 150),
                    drop=config.DROP_SOIN)),
    "VIE_V": dict(nom=f"Vie max +{config.FORCE_VIE_V*100:.0f}%", rarete=Rarete.VERT,
                  effet="vie_max", valeur=config.FORCE_VIE_V,
                  tables={"classique": config.POIDS_CS_VIE_V}),
    "VIE_B": dict(nom=f"Vie max +{config.FORCE_VIE_B*100:.0f}%", rarete=Rarete.BLEU,
                  effet="vie_max", valeur=config.FORCE_VIE_B,
                  tables={"classique": config.POIDS_CS_VIE_B}),
    "VIE_J": dict(nom=f"Vie max +{config.FORCE_VIE_J*100:.0f}%", rarete=Rarete.JAUNE,
                  effet="vie_max", valeur=config.FORCE_VIE_J,
                  tables={"prismatique": config.POIDS_PS_VIE_J}),
    "VITESSE_J": dict(nom=f"Vitesse +{config.FORCE_VITESSE_J*100:.0f}%", rarete=Rarete.JAUNE,
                      effet="stat", stat="vitesse", label="VITESSE", hud="CYAN",
                      valeur=config.FORCE_VITESSE_J, cap=config.CAP_VITESSE,
                      tables={"prismatique": config.POIDS_PS_VITESSE_J}),
    "SAUT_J": dict(nom=f"Saut +{config.FORCE_SAUT_J*100:.0f}%", rarete=Rarete.JAUNE,
                   effet="stat", stat="saut", label="SAUT", hud="CYAN",
                   valeur=config.FORCE_SAUT_J, cap=config.CAP_SAUT,
                   tables={"prismatique": config.POIDS_PS_SAUT_J}),
    "DEGATS_J": dict(nom=f"Dégâts +{config.FORCE_DEGATS_J*100:.0f}%", rarete=Rarete.JAUNE,
                     effet="stat", stat="degats", label="DEGATS", hud="ROSE",
                     valeur=config.FORCE_DEGATS_J, cap=config.CAP_DEGATS,
                     tables={"prismatique": config.POIDS_PS_DEGATS_J}),
    "AUTO_REGEN_R": dict(nom="Auto-régénération", rarete=Rarete.ROUGE, effet="auto_regen",
                         valeur=config.AUTOREGEN_PV,
                         tables={"prismatique": config.POIDS_PS_AUTOREGEN_R}),
}

# ---------------------------------------------------------------------------
#  Équipements : générés AUTOMATIQUEMENT depuis le champ "coffres" de data/armes.py et data/armures.py.
#  (définir une arme/armure avec  coffres={"classique": 4, ...}  suffit pour qu'elle tombe des coffres)
#  La rareté (commun...special) est tirée à l'ouverture du coffre, pas ici.
# ---------------------------------------------------------------------------
for _item, _d in {**ARMES, **ARMURES}.items():
    if _d.get("coffres"):
        BOOSTS["EQ_" + _item.upper()] = dict(nom=_d["nom"], rarete=Rarete.JAUNE, effet="equipement",
                                              item=_item, valeur=0, tables=_d["coffres"])

PICKUP_IDS = [k for k, d in BOOSTS.items() if "pickup" in d]   # index = type dans entity.pickups


def table_butin(nom_table):
    """[(id, poids)] de tous les boosts présents dans la table `nom_table`."""
    return [(k, d["tables"][nom_table]) for k, d in BOOSTS.items() if nom_table in d.get("tables", {})]




DELAI_GRACE_BUTIN = 1.5      # s avant qu'un butin lâché puisse être ramassé automatiquement
