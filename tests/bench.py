"""Benchmark headless : python tests/bench.py [--real] [--frames N]
  - sans --real : faux pygame (compte les appels de dessin, mesure le cout CPU LOGIQUE du moteur)
  - avec --real : vrai pygame (SDL_VIDEODRIVER=dummy) -> mesure aussi le cout reel du dessin logiciel."""
import os, sys, time, math, statistics, argparse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--real", action="store_true"); ap.add_argument("--frames", type=int, default=600); ap.add_argument("--qualite", default="haut"); ap.add_argument("--distance", type=int, default=0)
args = ap.parse_args()
if args.real:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy"); import pygame; fp = None
else:
    import tests.fake_pygame as fp; fp.installer(); import pygame
import random
random.seed(1)
from world.jeu import Jeu
from engine.affichage import Affichage
from data import config
pygame.init()
surf = pygame.display.set_mode((config.LARGEUR, config.HAUTEUR))
try:
    from data import reglages
    reglages._valeurs["qualite"] = args.qualite
    if args.distance: reglages._valeurs["distance"] = args.distance
    from engine import qualite as _q
    config.appliquer_distance(_q.distance_effective())
except ImportError:
    pass            # code d'origine : pas de reglages
jeu = Jeu()
aff = Affichage(surf, jeu)
jeu.joueur.pv = 10**9
dt = 1 / 60
tms, hitch = [], []
if fp: fp.reset_stats()
t_all = time.perf_counter()
for f in range(args.frames):
    t = f * dt
    config.yaw += 0.8 * math.sin(f * 0.02) + 0.35          # le joueur tourne en avancant -> traverse des chunks
    config.pitch = 4 * math.sin(f * 0.013)
    if f % 9 == 0: jeu.tirer()
    if f % 240 == 100 and hasattr(jeu, "dash"): jeu.dash()
    t0 = time.perf_counter()
    jeu.mettre_a_jour(dt, t, 1, 0.0, 0, False)
    aff.dessiner(t)
    tms.append((time.perf_counter() - t0) * 1000)
tot = time.perf_counter() - t_all
spikes = sorted(range(len(tms)), key=lambda i: -tms[i])[:5]
print('pires frames:', [(i, round(tms[i],1)) for i in spikes])
print(f"frames={args.frames}  moyenne={statistics.mean(tms):.2f} ms  mediane={statistics.median(tms):.2f} ms  "
      f"p99={sorted(tms)[int(len(tms)*.99)]:.2f} ms  pire={max(tms):.1f} ms")
if fp:
    S = fp.STATS; n = args.frames
    print(f"appels dessin/frame={S['calls']/n:.0f}  (polygones {S['poly']/n:.0f}, lignes {S['line']/n:.0f}, rect {S['rect']/n:.0f}, blit {S['blit']/n:.0f})"
          f"  surfaces creees/frame={S['surf_new']/n:.1f}  polices creees/frame={S['font_new']/n:.2f}")
