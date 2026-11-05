# 🕹️ Document de Game Design : FPS Wireframe Synthwave (Pygame)

Ce document récapitule l'ensemble des concepts, mécaniques, identités visuelles et choix techniques pour le développement de ton FPS en Python avec Pygame.

---

## 1. Identité Technique & Direction Artistique

* **Moteur Graphique :** Vraie 3D polygonal en fil de fer (*wireframe*) avec projection en perspective ($X, Y, Z$).
* **Direction Artistique :** Esthétique **Synthwave / Cyberpunk 80s** (lignes néons sur fond noir, grille de sol perspective, couleurs saturées).
* **Concept d'Immersion (Lore) :**
  * Le joueur n'est pas dans un monde réel, mais piégé **dans une matrice / un système informatique**.
  * **Le Joueur :** Un programme pirate / un exécutable (`.exe`).
  * **Les Ennemis :** Des virus, malwares, et subroutines de sécurité.
  * **Les Coffres / Bonus :** Des "Caches Mémoires" ou "Archives de Données".
  * **Le Score :** Le volume de données extraites (Mo / Go).

---

## 2. Palette de Couleurs Néons

* **Cyan Fluo :** `(0, 255, 255)` — Zone stable, éléments neutres.
* **Magenta / Rose :** `(255, 0, 127)` — Zone corrompue, tirs, boss.
* **Orange / Jaune Solaire :** `(255, 140, 0)` / `(255, 220, 0)` — Mode Overclock, bonus rares.
* **Vert Matrix / Néon :** `(0, 255, 100)` — Données, santé, boucliers.

---

## 3. Système de Biomes & Chunks

La carte est générée par **chunks** virtuels. Chaque biome modifie la couleur des arêtes et applique une **règle physique unique** :

| Biome | Visuel / Couleur | Règle de Gameplay Spéciale |
| :--- | :--- | :--- |
| **01. Le Noyau (Grid Zone)** | Cyan / Bleu | Zone d'origine. Physique neutre, bonne visibilité, coffres standards. |
| **02. Secteur Endommagé (Glitch Zone)** | Magenta / Violet | Arêtes du maillage qui clignotent/se déforment. Tirs légèrement déviés et monstres qui se régénèrent. |
| **03. Mémoire Cache (Overclock Zone)** | Orange / Jaune | Vitesse générale boostée (1.5x). Surchauffe continue du joueur qui perd de la vie s'il ne détruit pas d'ennemis. |
| **04. Le Vide (Silent Void)** | Vert Mat / Sombre | Les murs wireframe sont invisibles sauf s'ils sont éclairés par un tir ou une onde sonar. |

---

## 4. Bestiaire & Boss

### Ennemis Réguliers
1. **Le Striker (Ligne Électrique) :**
   * *Comportement :* N'a pas de volume 3D complexe, se déplace hyper vite en ligne droite vers le joueur sous forme de rayon d'énergie.
2. **Le Polygone Shield (Bouclier Vectoriel) :**
   * *Comportement :* Ennemi composé de plusieurs faces fil de fer. Chaque tir détruit une face. Il faut tourner autour de lui pour toucher son cœur vulnérable.
3. **Le Phasme (Traqueur de Grille) :**
   * *Comportement :* Se déplace sous forme de distorsion directe dans la grille du sol et surgit au dernier moment.

### Boss & Paliers
* Spawns automatiques à des paliers de score précis.
* **Pattern :** Structures géométriques géantes (ex: Icosaèdre / Cube rotatif) qui projettent des vagues d'ondes néons ou déploient des tourelles satellites autour d'elles.

---

## 5. Effets Visuels & "Game Juice" (Implémentation Pygame)

1. **Effet Halo Lumineux (*Glow*) :**
   * Tracer la ligne une première fois avec une épaisseur plus grande et une couleur sombre/transparente.
   * Retracer la même ligne plus fine par-dessus avec la couleur néon vive.
2. **Explosion de Sommets (*Vertex Shatter*) :**
   * À la mort d'un ennemi, décomposer sa structure $X, Y, Z$ en une nuée de particules vectorielles projetées dans l'espace 3D avec gravité.
3. **Ondulation de Grille (*Grid Wave*) :**
   * Lors des impacts de tirs ou des explosions, appliquer un décalage sinusoïdal sur les sommets adjacents du maillage du sol.
4. **Effet de Vitesse (FOV Dynamic) :**
   * Augmenter légèrement la distance focale de projection lors des dashs pour étirer la perspective.

---

## 6. Prochaines Étapes de Développement

- [ ] Structurer le générateur de terrain par chunks avec l'attribution des biomes.
- [ ] Implémenter le dictionnaire de couleurs/règles par biome.
- [ ] Ajouter l'effet de particule 3D à la destruction des entités.
- [ ] Programmer le premier type de boss à palier de score.