"""
orbital_sim.py — Pure orbital mechanics simulation.

No rendering, no trame. Computes the full orbit using RK4 integration
and exposes the position arrays for use by driver apps.

Usage:
    from orbital_sim import r_e, r_j, t_arr, N
"""

import math
import numpy as np

# ---------------------------------------------------------------------------
# Physical constants (normalised units)
# ---------------------------------------------------------------------------
MM = 6e24                       # normalising mass (Earth mass)
RR = 1.496e11                   # normalising distance (1 AU in metres)
TT = 365 * 24 * 60 * 60.0      # normalising time (1 year in seconds)
G  = 6.673e-11                  # gravitational constant

GG = (MM * G * TT**2) / RR**3  # dimensionless gravitational constant

Me = 6e24        / MM           # Earth mass (normalised)
Ms = 2e30        / MM           # Sun mass (normalised)
Mj = 500*1.9e27  / MM           # Super Jupiter mass (normalised, 500x Jupiter)


# ---------------------------------------------------------------------------
# Force functions
# ---------------------------------------------------------------------------
def _force(r: np.ndarray, m1: float, m2: float) -> np.ndarray:
    """Gravitational force on body with mass m1 at position r due to body m2 at origin."""
    n  = np.linalg.norm(r) + 1e-20
    th = math.atan(abs(r[1]) / (abs(r[0]) + 1e-20))
    fx = GG * m1 * m2 / n**2 * math.cos(th)
    fy = GG * m1 * m2 / n**2 * math.sin(th)
    if r[0] > 0: fx = -fx
    if r[1] > 0: fy = -fy
    return np.array([fx, fy])


def force_earth(re: np.ndarray, rj: np.ndarray) -> np.ndarray:
    """Net force on Earth: gravity from Sun + gravity from Super Jupiter."""
    return _force(re, Me, Ms) + _force(re - rj, Me, Mj)


def force_jupiter(rj: np.ndarray, re: np.ndarray) -> np.ndarray:
    """Net force on Super Jupiter: gravity from Sun + gravity from Earth."""
    return _force(rj, Mj, Ms) + _force(rj - re, Mj, Me)


# ---------------------------------------------------------------------------
# RK4 integrator
# ---------------------------------------------------------------------------
def rk4(r: np.ndarray, v: np.ndarray, h: float, f_func, other_r: np.ndarray):
    """
    One RK4 step for a body with position r, velocity v, timestep h.
    @param f_func  - force function f(r, other_r) -> acceleration
    @param other_r - position of the other gravitating body
    @returns (r_new, v_new)
    """
    k11 = v;               k21 = f_func(r, other_r)
    k12 = v + .5*h*k21;   k22 = f_func(r + .5*h*k11, other_r)
    k13 = v + .5*h*k22;   k23 = f_func(r + .5*h*k12, other_r)
    k14 = v +    h*k23;   k24 = f_func(r +    h*k13, other_r)
    r1 = r + h * (k11 + 2*k12 + 2*k13 + k14) / 6
    v1 = v + h * (k21 + 2*k22 + 2*k23 + k24) / 6
    return r1, v1


# ---------------------------------------------------------------------------
# Pre-compute full orbit on import
# ---------------------------------------------------------------------------
YEARS        = 120
PTS_PER_YEAR = 100

N     = YEARS * PTS_PER_YEAR
t_arr = np.linspace(0, YEARS, N)
h     = t_arr[1] - t_arr[0]

r_e = np.zeros((N, 2));  v_e = np.zeros((N, 2))
r_j = np.zeros((N, 2));  v_j = np.zeros((N, 2))

r_e[0] = [1.0, 0.0]
v_e[0] = [0.0, math.sqrt(Ms * GG / 1.0)]
r_j[0] = [5.2, 0.0]
v_j[0] = [0.0, 13.06e3 * TT / RR]

print("orbital_sim: pre-computing orbit …")
for i in range(N - 1):
    r_e[i+1], v_e[i+1] = rk4(r_e[i], v_e[i], h, force_earth,   r_j[i])
    r_j[i+1], v_j[i+1] = rk4(r_j[i], v_j[i], h, force_jupiter, r_e[i])
print(f"orbital_sim: orbit ready — {N} frames over {YEARS} years.")