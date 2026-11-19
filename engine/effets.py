# engine/effets.py -- "game juice" : particules vectorielles, ondulation de grille, FOV dynamique
#
#  API simple (modules-singletons, utilisables de partout : entity, boss, monstres...) :
#     effets.eclater(P1, P2, couleur, sol_y)      -> Vertex Shatter : chaque segment devient un débris 3D (gravité)
#     effets.etincelles(pos, couleur, n)          -> gerbe d'étincelles (impact, dash...)
#     effets.onde(x, z, amp)                      -> Grid Wave : onde sinusoïdale dans la grille du sol
#     effets.fov.declencher_dash()                -> FOV dynamique
#  Le jeu appelle effets.maj(dt, temps, sprint) 1 fois par frame et lit effets.particules / effets.ondes au rendu.
import math
import numpy as np
from data import config, reglages
from engine.renderer import projeter_3d_masse
from engine.qualite import profil

temps = 0.0                      # horloge des effets (mise à jour par maj())
glitch_moteur = False            # Propagation létale : murs translucides + décor corrompu (lu par engine/scene.py)
_rng = np.random.default_rng(12345)


# =============================================================
#  PARTICULES VECTORIELLES (structure-of-arrays : tout est numpy, zéro objet Python par particule)
# =============================================================
class Particules:
    def __init__(self, capacite=1500):
        self.cap = capacite
        self.n = 0
        self.c = np.zeros((capacite, 3), np.float32)       # centre
        self.h = np.zeros((capacite, 3), np.float32)       # demi-vecteur du segment
        self.v = np.zeros((capacite, 3), np.float32)       # vitesse
        self.col = np.zeros((capacite, 3), np.float32)
        self.vie = np.zeros(capacite, np.float32)
        self.vie0 = np.ones(capacite, np.float32)
        self.sol = np.zeros(capacite, np.float32)          # hauteur du sol au point d'émission (rebond)
        self.spin = np.zeros(capacite, np.float32)
        self._tab = (self.c, self.h, self.v, self.col, self.vie, self.vie0, self.sol, self.spin)

    def limite(self):
        return min(self.cap, int(reglages.get("particules") * profil().particules_ratio))

    def vider(self):
        self.n = 0

    def emettre(self, c, h, v, col, vie, sol, spin):
        k = len(c)
        libre = self.limite() - self.n
        if k == 0 or libre <= 0:
            return
        if k > libre:                                       # trop de débris : on garde un échantillon
            idx = _rng.choice(k, libre, replace=False)
            c, h, v, vie, spin = c[idx], h[idx], v[idx], vie[idx], spin[idx]
            k = libre
        s = slice(self.n, self.n + k)
        self.c[s], self.h[s], self.v[s] = c, h, v
        self.col[s] = col
        self.vie[s] = vie
        self.vie0[s] = vie
        self.sol[s] = sol
        self.spin[s] = spin
        self.n += k

    def maj(self, dt):
        n = self.n
        if not n:
            return
        c, h, v = self.c[:n], self.h[:n], self.v[:n]
        v[:, 1] += config.GRAVITE_PARTICULES * dt
        c += v * dt
        sol = self.sol[:n]
        bas = c[:, 1] > sol
        if bas.any():                                       # rebond amorti sur le sol
            c[bas, 1] = sol[bas]
            v[bas, 1] *= -0.30
            v[bas, 0] *= 0.6
            v[bas, 2] *= 0.6
            self.spin[:n][bas] *= 0.5
        a = self.spin[:n] * dt
        cs, sn = np.cos(a), np.sin(a)
        hx = h[:, 0] * cs + h[:, 2] * sn
        hz = -h[:, 0] * sn + h[:, 2] * cs
        h[:, 0], h[:, 2] = hx, hz
        self.vie[:n] -= dt
        vivants = self.vie[:n] > 0
        if not vivants.all():                               # compactage
            k = int(vivants.sum())
            for arr in self._tab:
                arr[:k] = arr[:n][vivants]
            self.n = k

    def segments_ecran(self):
        """-> (profondeur, [((x1,y1),(x2,y2),couleur), ...]) ou None. UNE projection numpy pour toutes."""
        n = self.n
        if not n:
            return None
        c, h = self.c[:n], self.h[:n]
        ex, ey, rz, v = projeter_3d_masse(np.concatenate((c - h, c + h)))
        ok = v[:n] & v[n:]
        idx = np.nonzero(ok)[0]
        if not len(idx):
            return None
        f = np.clip(self.vie[:n] / self.vie0[:n], 0.0, 1.0)
        cols = (self.col[:n] * (0.25 + 0.75 * f)[:, None])[idx].astype(np.int32).tolist()
        ax, ay = ex[:n][idx].tolist(), ey[:n][idx].tolist()
        bx, by = ex[n:][idx].tolist(), ey[n:][idx].tolist()
        segs = [((ax[i], ay[i]), (bx[i], by[i]), (cols[i][0], cols[i][1], cols[i][2])) for i in range(len(idx))]
        return float(rz[:n][idx].min()), segs


particules = Particules()


def eclater(P1, P2, couleur, sol_y, force=1.0, morceaux=1):
    """VERTEX SHATTER : chaque segment (P1[i] -> P2[i], coordonnées MONDE) devient un débris vectoriel
    projeté vers l'extérieur du modèle, avec gravité et rebond sur le sol."""
    p1 = np.asarray(P1, np.float32).reshape(-1, 3)
    p2 = np.asarray(P2, np.float32).reshape(-1, 3)
    if len(p1) == 0:
        return
    if morceaux > 1:                                        # on casse chaque arête en plusieurs morceaux
        t = np.linspace(0.0, 1.0, morceaux + 1, dtype=np.float32)
        a = p1[:, None, :] + (p2 - p1)[:, None, :] * t[None, :-1, None]
        b = p1[:, None, :] + (p2 - p1)[:, None, :] * t[None, 1:, None]
        p1, p2 = a.reshape(-1, 3), b.reshape(-1, 3)
    centres = (p1 + p2) * 0.5
    demi = (p2 - p1) * 0.5
    k = len(centres)
    dirs = centres - centres.mean(axis=0)
    nrm = np.linalg.norm(dirs, axis=1, keepdims=True) + 1e-3
    dirs = dirs / nrm + _rng.normal(0, 0.35, (k, 3)).astype(np.float32)
    vit = dirs * _rng.uniform(70, 240, (k, 1)).astype(np.float32) * force
    vit[:, 1] -= _rng.uniform(60, 260, k).astype(np.float32) * force          # y négatif = vers le haut
    particules.emettre(centres, demi, vit, np.array(couleur, np.float32),
                       _rng.uniform(0.9, 1.7, k).astype(np.float32), sol_y,
                       _rng.uniform(-6, 6, k).astype(np.float32))


def etincelles(pos, couleur, n=8, vitesse=260.0, taille=8.0):
    """Gerbe de petits traits (impact de tir en ROUGE VIF, dash, atterrissage...)."""
    n = max(1, int(n))
    d = _rng.normal(0, 1, (n, 3)).astype(np.float32)
    d /= (np.linalg.norm(d, axis=1, keepdims=True) + 1e-6)
    c = np.tile(np.asarray(pos, np.float32), (n, 1))
    h = d * _rng.uniform(0.4, 1.0, (n, 1)).astype(np.float32) * taille * 0.5
    v = d * _rng.uniform(0.35, 1.0, (n, 1)).astype(np.float32) * vitesse
    particules.emettre(c, h, v, np.array(couleur, np.float32),
                       _rng.uniform(0.25, 0.55, n).astype(np.float32), float(pos[1]) + 400.0,
                       _rng.uniform(-10, 10, n).astype(np.float32))


# =============================================================
#  ONDULATION DE GRILLE (Grid Wave)
# =============================================================
class OndesGrille:
    MAX = 14

    def __init__(self):
        self.impulsions = []        # (x, z, t0, amp, vitesse, longueur, duree)
        self.sources = []           # (x, z, amp, sigma) -- distorsions continues (Phasme), réécrites chaque frame

    def impulsion(self, x, z, amp, vitesse=420.0, longueur=300.0, duree=0.85):
        if not reglages.get("fx_grille"):
            return
        if len(self.impulsions) >= self.MAX:
            self.impulsions.pop(0)
        self.impulsions.append((float(x), float(z), temps, float(amp), float(vitesse), float(longueur), float(duree)))

    def vider(self):
        self.impulsions.clear()
        self.sources = []

    def deplacement(self, X, Z):
        """Décalage vertical (en unités monde, y négatif = vers le haut) pour chaque sommet (X, Z), ou None."""
        t = temps
        if self.impulsions:
            self.impulsions = [i for i in self.impulsions if t - i[2] < i[6]]
        if not self.impulsions and not self.sources:
            return None
        val = np.zeros(len(X), np.float32)
        for x, z, t0, amp, vit, lg, dur in self.impulsions:
            age = t - t0
            fade = 1.0 - age / dur
            r = np.hypot(X - x, Z - z)
            e = r - vit * age                                              # distance au front de l'onde
            val += (amp * fade) * np.sin(e * (2 * math.pi / (lg * 0.9))) * np.exp(-(e / lg) ** 2)
            val += (amp * 0.6 * fade * fade) * np.exp(-(r / (lg * 0.45)) ** 2)    # bosse à l'impact
        for x, z, amp, sigma in self.sources:
            r2 = (X - x) ** 2 + (Z - z) ** 2
            g = np.exp(-r2 / (2.0 * sigma * sigma))
            val += amp * g * (0.75 + 0.25 * math.sin(t * 9.0))
            val += 0.35 * amp * g * np.cos(np.sqrt(r2) * 0.06 - t * 11.0)
        return -val


ondes = OndesGrille()


def onde(x, z, amp=8.0, vitesse=420.0, longueur=300.0, duree=0.85):
    ondes.impulsion(x, z, amp, vitesse, longueur, duree)


# =============================================================
#  FOV DYNAMIQUE
# =============================================================
class FovDynamique:
    def __init__(self):
        self.t_dash = 0.0
        self.sprint = 0.0
        self.boost = 0.0

    def declencher_dash(self):
        self.t_dash = config.FOV_DASH_DUREE

    def maj(self, dt, en_sprint):
        if not reglages.get("fx_fov"):
            self.t_dash, self.sprint, self.boost = 0.0, 0.0, 0.0
            config.FOCALE = config.FOCALE_BASE
            return
        self.t_dash = max(0.0, self.t_dash - dt)
        p = self.t_dash / config.FOV_DASH_DUREE                        # 1 -> 0
        monte = min(1.0, (1.0 - p) / 0.10)                             # montée rapide (10% du temps), puis retombée douce
        impulsion = config.FOV_DASH_BOOST * monte * p * p
        cible = config.FOV_SPRINT_BOOST if en_sprint else 0.0
        self.sprint += (cible - self.sprint) * min(1.0, config.FOV_LISSAGE * dt)
        self.boost = impulsion + self.sprint
        config.FOCALE = config.FOCALE_BASE * (1.0 + self.boost)


fov = FovDynamique()


# =============================================================
#  Pilotage global
# =============================================================
def maj(dt, t, en_sprint=False):
    global temps
    temps = t
    particules.maj(dt)
    fov.maj(dt, en_sprint)


def reinitialiser():
    global glitch_moteur
    glitch_moteur = False
    particules.vider()
    ondes.vider()
    fov.t_dash = fov.sprint = fov.boost = 0.0
    config.FOCALE = config.FOCALE_BASE
