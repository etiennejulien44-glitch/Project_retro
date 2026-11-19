"""Faux module `pygame` MINIMAL pour tester la logique du jeu sans fenetre (CI / sandbox).
Il compte les appels de dessin et estime le cout de remplissage (aire des bbox).
Utilisation : `import tests.fake_pygame as fp; fp.installer()` AVANT d'importer le jeu."""
import sys, types, time as _time

STATS = {"calls": 0, "px": 0, "poly": 0, "line": 0, "rect": 0, "blit": 0, "surf_new": 0, "font_new": 0}

def reset_stats():
    for k in STATS: STATS[k] = 0

class Surface:
    def __init__(self, size=(1, 1), flags=0, *a, **k):
        self._s = (int(size[0]), int(size[1])); STATS["surf_new"] += 1
    def get_size(self): return self._s
    def get_width(self): return self._s[0]
    def get_height(self): return self._s[1]
    def get_rect(self): return (0, 0) + self._s
    def fill(self, *a, **k): STATS["calls"] += 1; STATS["px"] += self._s[0] * self._s[1] * 0.2
    def blit(self, *a, **k): STATS["calls"] += 1; STATS["blit"] += 1; STATS["px"] += 0.5 * self._s[0] * self._s[1] * 0.1
    def set_alpha(self, *a): pass
    def set_clip(self, *a): pass
    def set_colorkey(self, *a): pass
    def convert(self, *a): return self
    def convert_alpha(self, *a): return self
    def copy(self): return Surface(self._s)
    def subsurface(self, r): return Surface((r[2], r[3]) if len(r) == 4 else r[2:])
    def get_bounding_rect(self): return _Rect(10, 10, 60, 120)
    def union(self, o): return self

def _bbox_area(pts):
    try:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return max(0, min(max(xs), 4000) - max(min(xs), -100)) * max(0, min(max(ys), 3000) - max(min(ys), -100))
    except Exception:
        return 0

class _Rect(tuple):
    def __new__(cls, *a): return tuple.__new__(cls, a)
    def union(self, o): return self
    @property
    def w(self): return self[2]

class _Draw:
    def polygon(self, s, c, pts, w=0):
        STATS["calls"] += 1; STATS["poly"] += 1; STATS["px"] += _bbox_area(pts) * (0.5 if w == 0 else 0.0) + (len(pts) * 60 * max(w, 1))
    def line(self, s, c, a, b, w=1):
        STATS["calls"] += 1; STATS["line"] += 1; STATS["px"] += (abs(a[0] - b[0]) + abs(a[1] - b[1]) + 2) * max(w, 1) * 0.5
    def lines(self, s, c, closed, pts, w=1):
        STATS["calls"] += 1; STATS["line"] += 1; STATS["px"] += len(pts) * 80 * max(w, 1)
    def rect(self, s, c, r, w=0):
        STATS["calls"] += 1; STATS["rect"] += 1
        try: STATS["px"] += (r[2] * r[3] if w == 0 else (r[2] + r[3]) * 2 * w)
        except Exception: pass
    def circle(self, s, c, p, r, w=0): STATS["calls"] += 1; STATS["px"] += 3.14 * r * r * (1 if w == 0 else 0.2)

class _Font:
    def __init__(self, *a, **k): STATS["font_new"] += 1
    def render(self, txt, aa, col, *a): return Surface((len(str(txt)) * 8, 16))
    def size(self, txt): return (len(str(txt)) * 12, 16)
    def get_height(self): return 16
    def get_linesize(self): return 16

class _Clock:
    def __init__(self): self._t = _time.perf_counter()
    def tick(self, fps=0): return 16
    def get_fps(self): return 60.0

def installer():
    m = types.ModuleType("pygame"); m.error = type("error", (Exception,), {})
    m.Surface = Surface; m.draw = _Draw(); m.SRCALPHA = 65536; m.RESIZABLE = 16; m.SCALED = 512
    m.FULLSCREEN = 1; m.DOUBLEBUF = 1073741824; m.QUIT = 256; m.KEYDOWN = 768; m.MOUSEMOTION = 1024
    m.MOUSEBUTTONDOWN = 1025
    for i, n in enumerate("ESCAPE TAB RETURN BACKSPACE UP DOWN SPACE LSHIFT F3 a f r z s d q e c v PAGEUP PAGEDOWN".split()):
        setattr(m, "K_" + n, 1000 + i)
    m.init = lambda: None; m.quit = lambda: None
    disp = types.SimpleNamespace(set_mode=lambda *a, **k: Surface(a[0]), flip=lambda: None,
                                 set_caption=lambda *a: None, get_surface=lambda: Surface((1920, 1080)),
                                 toggle_fullscreen=lambda: None, Info=lambda: types.SimpleNamespace(current_w=1920, current_h=1080))
    m.display = disp
    m.font = types.SimpleNamespace(Font=_Font, SysFont=_Font, init=lambda: None)
    m.time = types.SimpleNamespace(Clock=_Clock, get_ticks=lambda: int(_time.perf_counter() * 1000))
    m.event = types.SimpleNamespace(get=lambda: [], set_grab=lambda *a: None)
    m.mouse = types.SimpleNamespace(set_visible=lambda *a: None)
    m.key = types.SimpleNamespace(get_pressed=lambda: _KeyDict(), name=lambda k: "k%d" % (k % 100))
    m.transform = types.SimpleNamespace(scale=lambda s, size, *a: Surface(size), smoothscale=lambda s, size, *a: Surface(size))
    m.Rect = lambda *a: a
    m.image = types.SimpleNamespace(load=lambda p: Surface((1024, 768)))
    sys.modules["pygame"] = m
    return m

class _KeyDict(dict):
    def __missing__(self, k): return 0
