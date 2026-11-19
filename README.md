# Project_retro
    little retro project for fun,
    use Config.py to custom the game
    You can add or custom exsistant modele with the 3DWIRE modeler


## Organisation du code

| Dossier | Rôle |
|---|---|
| `main.py` | **Fenêtre + événements uniquement** (touches : `data/controles.py`) |
| `data/` | **Définitions pures** : monstres, biomes, armes, armures, stats, raretés, boss, boosts, décors, coffres, sprites, options. Ne dépend de rien. |
| `world/` | **Règles / état** : `jeu.py` (le jeu), `inventaire.py`, `butin.py`, `entity.py` (IA), `boss.py`, `terrain.py` |
| `engine/` | **Tout ce qui dessine ou calcule l'affichage** : `affichage.py`, `scene.py`, `ciel.py`, `effets.py`, `rendu_monstres.py`, `assets.py`, `qualite.py`... |
| `ui/` | **Interface** : `interface.py`, `hud.py`, `panneau_equipement.py` (droite), `terminal.py` (TAB = complétion) |
| `assets/` | icônes d'équipement 32x32 (`engine/assets.py` les charge) |

## Ajouter du contenu (un seul endroit à chaque fois)

* **Monstre** : un bloc `monstre("cle", ...)` dans `data/monstres.py` — modèle, stats, score **et biomes** (`biomes={"neon_grid": 2}`).
  Défauts par comportement, hauteurs déduites du modèle, erreurs explicites si un champ manque.
  Nouveau *comportement* : `@comportement("nom")` dans `world/entity.py` + ses défauts dans `DEFAUTS_COMPORTEMENT`.
* **Arme / armure** : une entrée dans `data/armes.py` ou `data/armures.py` (`coffres={"classique": 4}` = elle tombe des coffres).
* **Stat d'équipement** : une entrée dans `data/stats.py` (libellé, format, attribut de config visé, plafond) — appliquée automatiquement.
* **Biome** : une entrée dans `data/biomes.py` ; ses monstres viennent des monstres qui le déclarent.
* **Boss** : `BOSS_GEO` + `PALIERS` dans `data/boss.py` ; nouveau pattern : `@pattern("nom")` dans `world/boss.py`.
* **Icône d'objet** : champ `icone="nom"` -> `assets/<rareté>_<nom>.png` (tuple = noms alternatifs) ; sinon une icône vectorielle est dessinée.

## Interface
Panneau permanent à droite : chaque pièce équipée avec son **icône de rareté** (`assets/<rareté>_<objet>.png`, slot vide : `empty_slot.png`), son nom à la couleur de rareté et ses boosts ; puis les boosts ramassés et le poids RAM.
Terminal (TAB pour l'ouvrir) : **TAB complète** commandes, dossiers, items, options, valeurs et stats ; un 2e TAB liste les possibilités.

## Options & performances
Dans le terminal : `cd option`, `ls`, `set <option> <valeur>` (sauvegardé dans `reglages.json`).
`qualite auto` adapte halos / distance / particules aux FPS ; `resolution` (au prochain lancement) est le plus gros levier ;
`F3` affiche les stats (texte seul) ; `F11` plein écran.

## Arbre de compétences (GDD)
4 branches (Mobilité, Contrôle, AOE/Portée, Synth), 20 compétences : `data/competences.py` (définitions) + `world/competences.py` (règles).
Formule universelle : `Total_DMG = ((stat_dmg * spec_weight + base_dmg) * power_capa * 1.1^(lvl-1)) / 100`.

* **Points (PC)** : 3 au départ, +1 tous les 400 points de score (`POINTS` dans `data/competences.py`).
* **Terminal** : `cd skills` puis `ls`, `cat <compétence>`, `up <compétence> [n]`, `ult <ultime>`, `respec` (rembourse tout).
  Niveau 0 = verrouillée ; un seul ultime actif à la fois (le premier acheté est équipé).
* **Touches** (`data/controles.py`) : **A** dash · **E** onde vectorielle · **C** corruption virulente · **V** ultime équipé.
  La barre de recharge s'affiche à gauche, les PC disponibles aussi.
* **Équipement** : la stat `dash_atq` des armures donne des **niveaux de dash gratuits**.
* Choix d'équilibrage non précisés par le GDD : 1 mètre = 50 unités ; `base_dmg` = 8 ; portée du dash = (2 + 0.25 x niv) cellules ;
  corruption : +10% de jauge par tick de base ; cône de contrôle ±25°, 900 unités. Tout est modifiable dans `data/`.

## Terminal
Sortie colorée (objets à la couleur de leur rareté, colonnes alignées), retour à la ligne automatique, défilement fluide
(molette, PageHaut/PageBas), curseur clignotant. **TAB** complète commandes, dossiers, items, options, valeurs, stats et compétences.

## Tests
`python tests/smoke.py` (112 vérifications : comportements, architecture, ajout de contenu, TAB, assets, événements) —
`python tests/bench.py [--real] [--qualite bas|moyen|haut]` (benchmark).
Sans pygame installé, un faux pygame est utilisé ; avec `--real`, le vrai coût de dessin est mesuré (SDL dummy).
