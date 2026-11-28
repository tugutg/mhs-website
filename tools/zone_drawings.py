#!/usr/bin/env python3
"""Draws the five machines of the protected-zones selector (excavator, haul truck, wheel loader, dozer,
reach stacker) and writes them into docs/index.html.

Each machine is a side elevation facing left, drawn in metres at real proportions (x grows to the rear,
h is height above the ground line) and scaled into the 640 x 320 viewBox. The red hatched zones and their
numbers must stay the same set as the legend beside each drawing; the script refuses to write otherwise.
The hatch pattern (#zh) lives once in the zero-size <svg class="zdefs"> beside the tabs.

Usage: python3 tools/zone_drawings.py [docs/index.html]
Not part of the build: run it by hand after changing a drawing, then build and check as usual.
"""
import math, re, sys

G = 281  # ground line y (px)

class D:
    """Side-view drawing in metres: x grows to the rear (machine faces left), h is height above ground."""
    def __init__(s, scale, x0):
        s.s, s.x0, s.out, s.zones = scale, x0, [], []
    def X(s, x): return s.x0 + x * s.s
    def Y(s, h): return G - h * s.s
    def P(s, x, h): return '%.1f %.1f' % (s.X(x), s.Y(h))
    def add(s, el): s.out.append(el)
    def path(s, cmds, cls='ml'):
        d = []
        for c in cmds:
            op, a = c[0], c[1:]
            if op in 'ML': d.append(op + s.P(*a))
            elif op == 'Q': d.append('Q' + s.P(a[0], a[1]) + ' ' + s.P(a[2], a[3]))
            elif op == 'C': d.append('C' + s.P(a[0], a[1]) + ' ' + s.P(a[2], a[3]) + ' ' + s.P(a[4], a[5]))
            elif op == 'A':
                rx, ry, large, sweep, x, h = a
                d.append('A%.1f %.1f 0 %d %d %s' % (rx * s.s, ry * s.s, large, sweep, s.P(x, h)))
            elif op == 'Z': d.append('Z')
        s.add('<path class="%s" d="%s"/>' % (cls, ''.join(d)))
    def poly(s, pts, cls='ml', close=True):
        s.path([('M',) + tuple(pts[0])] + [('L',) + tuple(p) for p in pts[1:]] + ([('Z',)] if close else []), cls)
    def rect(s, x, h, w, hh, cls='ml', r=0):
        s.add('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"%s/>' % (
            cls, s.X(x), s.Y(h + hh), w * s.s, hh * s.s, (' rx="%.1f"' % (r * s.s)) if r else ''))
    def circle(s, x, h, r, cls='ml'):
        s.add('<circle class="%s" cx="%.1f" cy="%.1f" r="%.1f"/>' % (cls, s.X(x), s.Y(h), r * s.s))
    def line(s, x1, h1, x2, h2, cls='mt'):
        s.add('<line class="%s" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>' % (cls, s.X(x1), s.Y(h1), s.X(x2), s.Y(h2)))
    def lines(s, segs, cls='mx'):
        d = ''.join('M%sL%s' % (s.P(a, b), s.P(c, e)) for a, b, c, e in segs)
        s.add('<path class="%s" d="%s"/>' % (cls, d))
    def pin(s, x, h, r=0.12):
        s.circle(x, h, r, 'ml'); s.circle(x, h, r * 0.35, 'mdot')
    def cyl(s, x1, h1, x2, h2, frac=0.58, w=0.24, rod=0.09):
        """Hydraulic cylinder from base (x1,h1) to rod end (x2,h2): outlined barrel, rod, pins."""
        L = math.hypot(x2 - x1, h2 - h1); ux, uh = (x2 - x1) / L, (h2 - h1) / L; nx, nh = -uh, ux
        bx, bh = x1 + ux * L * frac, h1 + uh * L * frac
        r = w / 2
        s.poly([(x1 + nx * r, h1 + nh * r), (bx + nx * r, bh + nh * r), (bx - nx * r, bh - nh * r), (x1 - nx * r, h1 - nh * r)], 'ml')
        q = rod / 2
        s.poly([(bx + nx * q, bh + nh * q), (x2 + nx * q, h2 + nh * q), (x2 - nx * q, h2 - nh * q), (bx - nx * q, bh - nh * q)], 'ml')
        s.pin(x1, h1, r * 0.8); s.pin(x2, h2, r * 0.7)
    def wheel(s, x, r, rim=0.55, lugs=30, hub=0.2):
        h = r
        s.circle(x, h, r, 'mf')
        segs = []
        for i in range(lugs):
            a = 2 * math.pi * (i + 0.5) / lugs
            segs.append((x + math.cos(a) * r * 0.86, h + math.sin(a) * r * 0.86, x + math.cos(a) * r, h + math.sin(a) * r))
        s.lines(segs, 'mx')
        s.circle(x, h, r * 0.86, 'mt')
        s.circle(x, h, r * rim, 'ml')
        s.circle(x, h, r * rim * 0.78, 'mt')
        s.circle(x, h, r * hub, 'ml')
        bolts = []
        for i in range(10):
            a = 2 * math.pi * i / 10
            s.circle(x + math.cos(a) * r * hub * 1.55, h + math.sin(a) * r * hub * 1.55, r * 0.022, 'mdot')
    def track(s, xf, xr, hgt, t=0.2, rollers=7, carriers=2, sprocket='rear', grouser=0.2):
        """Crawler track: chain (grey band), idler and sprocket, track frame, rollers."""
        r = hgt / 2
        s.path([('M', xf + r, hgt), ('L', xr - r, hgt), ('A', r, r, 0, 1, xr - r, 0), ('L', xf + r, 0), ('A', r, r, 0, 1, xf + r, hgt), ('Z',)], 'mf')
        ri = r - t
        s.path([('M', xf + r, hgt - t), ('L', xr - r, hgt - t), ('A', ri, ri, 0, 1, xr - r, t), ('L', xf + r, t), ('A', ri, ri, 0, 1, xf + r, hgt - t), ('Z',)], 'ml')
        # grouser marks on the band
        segs = []
        x = xf + r
        while x < xr - r:
            segs.append((x, 0, x, t * 0.75)); segs.append((x + grouser / 2, hgt, x + grouser / 2, hgt - t * 0.75)); x += grouser
        s.lines(segs, 'mx')
        # idler (front) and sprocket (rear)
        s.circle(xf + r, r, ri * 0.92, 'ml'); s.circle(xf + r, r, ri * 0.55, 'mt'); s.circle(xf + r, r, ri * 0.22, 'ml')
        sx = xr - r
        teeth = 11; pts = []
        for i in range(teeth * 2):
            a = math.pi * i / teeth
            rr = ri * (0.95 if i % 2 == 0 else 0.8)
            pts.append((sx + math.cos(a) * rr, r + math.sin(a) * rr))
        s.poly(pts, 'ml'); s.circle(sx, r, ri * 0.55, 'mt'); s.circle(sx, r, ri * 0.22, 'ml')
        # track frame and rollers
        fx0, fx1 = xf + r + ri * 0.75, xr - r - ri * 0.75
        step = (fx1 - fx0) / (rollers - 1)
        for i in range(rollers):
            s.circle(fx0 + i * step, t + 0.11, 0.11, 'ml')
        cstep = (fx1 - fx0) / (carriers + 1)
        for i in range(carriers):
            s.circle(fx0 + (i + 1) * cstep, hgt - t - 0.08, 0.08, 'ml')
        s.rect(fx0 - 0.05, t + 0.2, fx1 - fx0 + 0.1, hgt - 2 * t - 0.36, 'ml', r=0.08)
        s.line(fx0 + 0.1, hgt * 0.5, fx1 - 0.1, hgt * 0.5, 'mx')
    def zone(s, n, x, h, w, hh):
        s.zones.append((n, x, h, w, hh))
    def render_zones(s):
        out = []
        for n, x, h, w, hh in s.zones:
            out.append('<rect class="z" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (s.X(x), s.Y(h + hh), w * s.s, hh * s.s))
        for n, x, h, w, hh in s.zones:
            cx, cy = s.X(x + w / 2), s.Y(h + hh / 2)
            out.append('<circle class="zc" cx="%.1f" cy="%.1f" r="11"/><text class="zt" x="%.1f" y="%.1f">%d</text>' % (cx, cy, cx, cy + 4.5, n))
        return out

def unit(dx, dh):
    L = math.hypot(dx, dh); return dx / L, dh / L


def excavator():
    d = D(40, 404)          # swing centre at x=0
    # crawler
    d.track(-2.95, 2.95, 1.35, t=0.2, rollers=8, carriers=2)
    d.rect(-1.05, 1.32, 2.1, 0.16, 'ml')                       # swing bearing / car body
    # upper structure (front deck for the cab, pump bay, engine hood, counterweight)
    d.path([('M', -2.02, 1.48), ('L', 3.72, 1.48), ('Q', 4.06, 1.48, 4.06, 1.84), ('L', 4.06, 2.72), ('Q', 4.06, 2.98, 3.78, 2.98),
            ('L', 2.96, 2.98), ('L', 2.96, 3.08), ('L', 0.56, 3.08), ('L', 0.56, 2.80), ('L', -0.30, 2.80), ('L', -0.30, 1.74),
            ('L', -2.02, 1.74), ('Z',)], 'ml')
    d.lines([(2.96, 1.48, 2.96, 2.98), (0.56, 1.48, 0.56, 2.80), (1.76, 1.62, 1.76, 2.98)], 'mt')
    d.lines([(0.75 + i * 0.0, 1.95 + i * 0.17, 1.62, 1.95 + i * 0.17) for i in range(5)] +
            [(1.9, 1.95 + i * 0.17, 2.78, 1.95 + i * 0.17) for i in range(5)], 'mx')       # engine-bay louvres
    d.lines([(3.05, 1.62, 3.9, 1.62)], 'mx')
    d.rect(-0.18, 1.86, 0.62, 0.8, 'mx')                                                 # pump-bay door
    d.rect(2.22, 3.08, 0.17, 0.52, 'ml'); d.poly([(2.2, 3.6), (2.41, 3.6), (2.43, 3.68), (2.18, 3.64)], 'ml')   # exhaust
    d.rect(1.05, 3.08, 0.3, 0.3, 'ml', r=0.04)                                            # pre-cleaner
    d.lines([(0.7, 3.08, 0.7, 3.78), (1.7, 3.08, 1.7, 3.78), (2.8, 3.08, 2.8, 3.78), (0.7, 3.78, 2.8, 3.78), (0.7, 3.45, 2.8, 3.45)], 'mt')  # handrails
    # boom (banana boom: foot F, knee K, tip T)
    F = (-0.78, 2.12)
    u1 = unit(-math.cos(math.radians(48)), math.sin(math.radians(48)))
    K = (F[0] + 3.3 * u1[0], F[1] + 3.3 * u1[1])
    u2 = unit(-math.cos(math.radians(13)), math.sin(math.radians(13)))
    T = (K[0] + 3.85 * u2[0], K[1] + 3.85 * u2[1])
    t1 = (u1[1], -u1[0]); t2 = (u2[1], -u2[0]); tk = unit(t1[0] + t2[0], t1[1] + t2[1])
    dF, dK, dT = 0.62, 1.0, 0.52
    def off(p, n, k): return (p[0] + n[0] * k, p[1] + n[1] * k)
    Ft, Fb = off(F, t1, dF / 2), off(F, t1, -dF / 2)
    Tt, Tb = off(T, t2, dT / 2), off(T, t2, -dT / 2)
    Kt, Kb = off(K, tk, dK / 2), off(K, tk, -dK / 2)
    a = lambda p, u, k: (p[0] + u[0] * k, p[1] + u[1] * k)
    d.path([('M',) + Ft, ('L',) + a(Kt, u1, -0.7), ('Q',) + Kt + a(Kt, u2, 0.7), ('L',) + Tt,
            ('A', dT / 2, dT / 2, 0, 0) + Tb, ('L',) + a(Kb, u2, 0.5), ('Q',) + Kb + a(Kb, u1, -0.5), ('L',) + Fb,
            ('A', dF / 2, dF / 2, 0, 0) + Ft, ('Z',)], 'ml')
    d.path([('M',) + a(off(K, tk, 0.22), u1, -1.6), ('Q',) + off(K, tk, 0.22) + a(off(K, tk, 0.22), u2, 2.2)], 'mx')
    # boom cylinder (base low on the upper frame, rod on the boom underside)
    c2 = off(a(F, u1, 2.55), t1, -0.42)
    d.cyl(-1.3, 1.64, c2[0], c2[1], frac=0.6, w=0.26, rod=0.12)
    # stick
    us = unit(-0.22, -0.976); ns = (us[1], -us[0])            # ns points to the front face
    B = a(T, us, 3.55); S = a(T, us, -0.95)
    d.path([('M',) + off(S, ns, 0.26), ('L',) + off(T, ns, 0.34), ('L',) + off(B, ns, 0.2), ('A', 0.2, 0.2, 0, 0) + off(B, ns, -0.2),
            ('L',) + off(T, ns, -0.3), ('L',) + off(S, ns, -0.22), ('A', 0.24, 0.24, 0, 0) + off(S, ns, 0.26), ('Z',)], 'ml')
    d.line(*off(a(T, us, 0.5), ns, 0.12), *off(a(B, us, -0.6), ns, 0.06), cls='mx')
    # stick (crowd) cylinder on top of the boom, to the stick tail
    cb = off(a(K, u2, 0.75), t2, dK / 2 - 0.02)
    d.cyl(cb[0], cb[1], S[0], S[1], frac=0.55, w=0.24, rod=0.11)
    d.pin(*T, r=0.16); d.pin(*F, r=0.17)
    # bucket (curled), pivot at B
    bx, bh = B
    pts = lambda L: [(bx + x, bh + y) for x, y in L]
    d.path([('M', bx + 0.12, bh + 0.16), ('L', bx - 0.42, bh - 0.12), ('C', bx - 0.76, bh - 0.32, bx - 0.8, bh - 0.78, bx - 0.64, bh - 1.02),
            ('C', bx - 0.5, bh - 1.28, bx - 0.36, bh - 1.46, bx - 0.12, bh - 1.52), ('C', bx + 0.12, bh - 1.56, bx + 0.32, bh - 1.5, bx + 0.48, bh - 1.42),
            ('L', bx + 0.62, bh - 1.22), ('L', bx + 0.32, bh - 0.2), ('Z',)], 'ml')
    d.poly(pts([(0.44, -1.44), (0.8, -1.24), (0.56, -1.2)]), 'ml')                    # tooth
    d.path([('M', bx - 0.5, bh - 0.32), ('C', bx - 0.66, bh - 0.7, bx - 0.5, bh - 1.2, bx - 0.12, bh - 1.34)], 'mx')
    # bucket linkage: cylinder along the stick's front face, links to the bucket
    cb2 = off(a(T, us, 0.38), ns, 0.48); re = off(a(B, us, -0.5), ns, 0.42)
    d.cyl(cb2[0], cb2[1], re[0], re[1], frac=0.6, w=0.22, rod=0.1)
    lk = (bx + 0.16, bh + 0.16); gl = off(a(B, us, -0.42), ns, 0.08)
    d.poly([re, lk, (lk[0] - 0.05, lk[1] - 0.08), (re[0] - 0.02, re[1] - 0.09)], 'ml')
    d.poly([re, gl, (gl[0] + 0.03, gl[1] - 0.06), (re[0] + 0.03, re[1] - 0.08)], 'ml')
    d.pin(*re, r=0.08); d.pin(*lk, r=0.08); d.pin(*B, r=0.11)
    # cab (in front of the boom foot)
    d.path([('M', -1.98, 1.74), ('L', -1.82, 3.62), ('L', -1.9, 3.66), ('L', -1.88, 3.78), ('L', -0.28, 3.78), ('L', -0.28, 1.74), ('Z',)], 'ml')
    d.poly([(-1.76, 2.38), (-1.66, 3.56), (-0.98, 3.56), (-0.98, 2.38)], 'mw')
    d.poly([(-0.88, 2.38), (-0.88, 3.56), (-0.42, 3.56), (-0.42, 2.38)], 'mw')
    d.poly([(-1.88, 1.86), (-1.8, 2.28), (-1.4, 2.28), (-1.4, 1.86)], 'mw')
    d.line(-1.06, 2.2, -1.06, 2.05, 'mt')
    d.lines([(-2.28, 1.35, -2.28, 1.74), (-2.02, 1.35, -2.02, 1.74), (-2.28, 1.48, -2.02, 1.48), (-2.28, 1.61, -2.02, 1.61)], 'mt')   # step
    # protected zones
    d.zone(1, 1.12, 1.98, 1.7, 0.94)      # engine
    d.zone(5, 1.12, 1.52, 1.18, 0.38)     # fuel filters / pumps, below the engine (owner, 28 Nov 2026)
    d.zone(2, -0.22, 1.5, 0.76, 1.24)     # hydraulic pumps: the whole pump bay
    d.zone(4, 0.6, 1.5, 0.44, 0.4)        # battery box
    return d


def truck():
    d = D(41, 56)           # x=0 at the front bumper, facing left
    fa, ra, R = 2.95, 8.85, 1.78
    # frame rails and rear axle housing
    d.poly([(1.0, 1.55), (10.6, 1.55), (10.6, 2.25), (1.0, 2.25)], 'ml')
    d.rect(ra - 1.15, 1.35, 2.3, 0.62, 'ml', r=0.15)                       # rear axle / final drives
    # front: bumper, radiator, engine bay under the deck
    d.poly([(0.0, 1.62), (1.25, 1.62), (1.25, 2.38), (0.0, 2.38)], 'ml')   # bumper
    d.poly([(0.32, 2.38), (1.3, 2.38), (1.3, 3.78), (0.32, 3.78)], 'ml')   # radiator housing
    d.lines([(0.42, 2.55 + i * 0.19, 1.2, 2.55 + i * 0.19) for i in range(6)], 'mx')
    d.poly([(1.3, 2.25), (4.55, 2.25), (4.55, 3.78), (1.3, 3.78)], 'ml')   # engine bay
    d.lines([(2.45, 2.25, 2.45, 3.78), (3.55, 2.25, 3.55, 3.78)], 'mt')
    d.lines([(1.45, 2.5 + i * 0.22, 2.3, 2.5 + i * 0.22) for i in range(5)], 'mx')
    # upper deck with handrails and the cab
    d.poly([(0.18, 3.78), (4.75, 3.78), (4.75, 3.98), (0.18, 3.98)], 'ml')
    d.lines([(0.3, 3.98, 0.3, 4.92), (0.3, 4.92, 1.05, 4.92), (0.3, 4.45, 1.05, 4.45)], 'mt')
    d.path([('M', 1.05, 3.98), ('L', 1.05, 5.45), ('Q', 1.05, 5.58, 1.2, 5.58), ('L', 3.38, 5.58), ('L', 3.38, 3.98), ('Z',)], 'ml')   # cab
    d.poly([(1.2, 4.55), (1.2, 5.42), (2.15, 5.42), (2.15, 4.55)], 'mw')
    d.poly([(2.28, 4.55), (2.28, 5.42), (3.22, 5.42), (3.22, 4.55)], 'mw')
    d.line(2.05, 4.42, 2.05, 4.28, 'mt')
    # access ladder at the front
    d.lines([(0.08, 0.55, 0.08, 3.78), (0.38, 0.55, 0.38, 1.62)], 'mt')
    d.lines([(0.08, 0.7 + i * 0.3, 0.38, 0.7 + i * 0.3) for i in range(4)], 'mt')
    # fuel tank and hydraulic tank on the frame
    d.rect(4.9, 1.6, 1.75, 0.95, 'ml', r=0.18)
    d.lines([(5.05, 2.35, 6.5, 2.35)], 'mx')
    d.rect(4.65, 2.55, 0.85, 0.8, 'ml', r=0.08)
    # hoist cylinder
    d.cyl(6.9, 1.95, 7.55, 3.18, frac=0.6, w=0.3, rod=0.13)
    # dump body with canopy over the cab
    d.path([('M', 4.35, 3.32), ('L', 4.35, 5.62), ('L', 0.42, 5.82), ('L', 0.42, 6.0), ('L', 4.55, 6.08), ('L', 11.35, 5.42),
            ('L', 12.85, 4.42), ('L', 12.85, 4.12), ('L', 11.55, 2.86), ('L', 5.6, 2.98), ('Z',)], 'ml')
    d.lines([(0.42, 5.82, 4.35, 5.62)], 'mt')
    d.lines([(5.9 + i * 1.25, 3.0, 5.9 + i * 1.25, 5.92 - i * 0.12) for i in range(5)], 'mx')     # side ribs
    d.path([('M', 4.55, 5.75), ('L', 11.25, 5.12), ('L', 12.55, 4.3)], 'mt')                      # top rail
    d.lines([(0.42, 5.9, 4.4, 5.85)], 'mx')
    # wheels
    d.wheel(fa, R, rim=0.5); d.wheel(ra, R, rim=0.5)
    # protected zones
    d.zone(1, 1.42, 2.36, 2.98, 1.3)      # engine bay
    d.zone(2, 4.68, 2.58, 0.8, 0.74)      # hydraulic tank / pumps
    d.zone(3, 5.6, 1.62, 2.0, 0.5)        # transmission / torque converter
    d.zone(4, 0.45, 1.66, 0.75, 0.66)     # battery box at the bumper
    d.zone(5, 4.92, 1.62, 0.66, 0.9)      # fuel filters / pumps
    return d


def loader():
    d = D(56, 66)           # x=0 near the bucket lip, facing left
    fa, ra, R = 2.95, 6.55, 0.9
    # rear frame: engine hood and counterweight
    d.path([('M', 4.62, 0.98), ('L', 9.02, 0.98), ('Q', 9.36, 0.98, 9.36, 1.3), ('L', 9.36, 2.08), ('Q', 9.36, 2.4, 9.04, 2.43),
            ('L', 8.78, 2.43), ('L', 8.62, 2.56), ('L', 5.76, 2.7), ('L', 5.76, 1.92), ('L', 4.62, 1.92), ('Z',)], 'ml')
    d.lines([(8.62, 0.98, 8.62, 2.56), (7.12, 1.2, 7.12, 2.63)], 'mt')
    d.lines([(5.98, 1.52 + i * 0.16, 6.92, 1.52 + i * 0.16) for i in range(6)] +
            [(7.32, 1.52 + i * 0.16, 8.42, 1.52 + i * 0.16) for i in range(6)], 'mx')        # louvres
    d.rect(6.3, 2.67, 0.13, 0.66, 'ml'); d.poly([(6.28, 3.33), (6.45, 3.33), (6.47, 3.4), (6.26, 3.37)], 'ml')   # exhaust
    d.rect(7.3, 2.62, 0.26, 0.3, 'ml', r=0.04)                                        # pre-cleaner
    d.rect(9.22, 1.55, 0.08, 0.28, 'mdot')                                               # tail light
    # front frame with the lift-arm tower, articulation
    d.poly([(2.4, 0.98), (4.66, 0.98), (4.66, 1.76), (3.98, 1.76), (3.9, 3.08), (3.38, 3.08), (3.3, 1.7), (2.4, 1.7)], 'ml')
    d.circle(4.64, 1.37, 0.13, 'ml'); d.circle(4.64, 1.37, 0.05, 'mdot')
    # cab
    d.path([('M', 4.12, 1.92), ('L', 4.26, 3.58), ('L', 4.16, 3.62), ('L', 4.19, 3.72), ('L', 5.76, 3.72), ('L', 5.76, 1.92), ('Z',)], 'ml')
    d.poly([(4.34, 2.32), (4.42, 3.52), (5.08, 3.52), (5.08, 2.32)], 'mw')
    d.poly([(5.18, 2.32), (5.18, 3.52), (5.62, 3.52), (5.62, 2.32)], 'mw')
    d.line(4.98, 2.2, 4.98, 2.06, 'mt')
    d.lines([(5.06, 0.52, 5.06, 1.92), (5.36, 0.52, 5.36, 1.92)] + [(5.06, 0.68 + i * 0.3, 5.36, 0.68 + i * 0.3) for i in range(4)], 'mt')   # ladder
    # wheels with fenders
    d.wheel(fa, R, rim=0.55); d.wheel(ra, R, rim=0.55)
    d.path([('M', ra - 1.04, 1.62), ('Q', ra - 0.98, 2.04, ra, 2.04), ('Q', ra + 0.98, 2.04, ra + 1.04, 1.62)], 'mt')
    # lift arm (bucket carried just off the ground)
    A, Bp = (3.64, 2.72), (1.24, 0.62)
    ux, uh = Bp[0] - A[0], Bp[1] - A[1]; L = math.hypot(ux, uh); ux, uh = ux / L, uh / L; nx, nh = -uh, ux
    mid = (A[0] + ux * L * 0.5 - nx * 0.06, A[1] + uh * L * 0.5 - nh * 0.06)
    w0, w1 = 0.23, 0.16
    d.path([('M', A[0] + nx * w0, A[1] + nh * w0), ('Q', mid[0] + nx * 0.3, mid[1] + nh * 0.3, Bp[0] + nx * w1, Bp[1] + nh * w1),
            ('A', w1, w1, 0, 0, Bp[0] - nx * w1, Bp[1] - nh * w1), ('Q', mid[0] - nx * 0.18, mid[1] - nh * 0.18, A[0] - nx * w0, A[1] - nh * w0),
            ('A', w0, w0, 0, 0, A[0] + nx * w0, A[1] + nh * w0), ('Z',)], 'ml')
    # Z-bar: tilt cylinder on the tower, bell crank on the arm, link to the bucket
    C, Ct, Cb, Lp = (2.62, 2.12), (2.8, 2.62), (2.42, 1.64), (1.3, 1.45)
    d.cyl(3.62, 3.0, Ct[0], Ct[1], frac=0.6, w=0.22, rod=0.1)
    d.poly([(Ct[0] + 0.07, Ct[1] + 0.02), (Cb[0] + 0.07, Cb[1] - 0.02), (Cb[0] - 0.07, Cb[1] + 0.01), (Ct[0] - 0.07, Ct[1] - 0.02)], 'ml')
    d.poly([(Cb[0], Cb[1] + 0.05), (Lp[0], Lp[1] + 0.05), (Lp[0], Lp[1] - 0.05), (Cb[0], Cb[1] - 0.05)], 'ml')
    d.pin(*Ct, r=0.07); d.pin(*C, r=0.08); d.pin(*Cb, r=0.06); d.pin(*A, r=0.12)
    # bucket (rolled back), hinge Bp and link pin Lp on its back
    d.path([('M', -0.16, 0.22), ('L', 1.0, 0.18), ('C', 1.3, 0.2, 1.44, 0.5, 1.44, 0.86), ('L', 1.42, 1.52), ('L', 1.2, 1.8),
            ('L', -0.08, 0.42), ('Z',)], 'ml')
    d.path([('M', 0.08, 0.42), ('L', 1.18, 1.62)], 'mx')
    d.poly([(-0.3, 0.2), (-0.12, 0.17), (-0.13, 0.3)], 'ml')                        # tooth
    d.pin(*Bp, r=0.1); d.pin(*Lp, r=0.06)
    # protected zones
    d.zone(1, 6.0, 1.48, 2.48, 1.06)      # engine bay
    d.zone(2, 4.0, 1.0, 0.62, 0.72)       # hydraulic pumps / valve block
    d.zone(3, 4.72, 1.02, 0.86, 0.56)     # transmission / torque converter
    d.zone(4, 5.66, 1.02, 0.76, 0.42)     # battery box, between the transmission and the fuel tank (owner, 28 Nov 2026)
    d.zone(5, 7.4, 1.02, 0.8, 0.38)       # fuel filters / pumps
    return d


def dozer():
    d = D(55, 80)           # x=0 at the blade's cutting edge, facing left
    # crawler (oval track)
    d.track(1.95, 6.85, 1.38, t=0.2, rollers=7, carriers=1)
    # main frame / engine hood / radiator guard
    d.path([('M', 2.05, 1.42), ('L', 6.6, 1.42), ('L', 6.6, 1.92), ('L', 4.95, 1.92), ('L', 4.95, 2.86), ('L', 2.62, 2.74),
            ('L', 2.32, 2.66), ('L', 2.05, 2.5), ('Z',)], 'ml')
    d.lines([(2.32, 1.42, 2.32, 2.66), (3.65, 1.42, 3.65, 2.8)], 'mt')
    d.lines([(2.1, 1.6 + i * 0.16, 2.26, 1.6 + i * 0.16) for i in range(6)], 'mx')            # radiator guard
    d.lines([(2.5, 1.62 + i * 0.17, 3.5, 1.62 + i * 0.17) for i in range(6)] + [(3.8, 1.62 + i * 0.17, 4.8, 1.62 + i * 0.17) for i in range(6)], 'mx')
    d.rect(3.0, 2.76, 0.14, 0.72, 'ml'); d.poly([(2.98, 3.48), (3.16, 3.48), (3.18, 3.56), (2.96, 3.52)], 'ml')   # exhaust
    d.rect(4.05, 2.82, 0.3, 0.34, 'ml', r=0.05)                                            # pre-cleaner
    # cab (ROPS) and fuel tank behind it
    d.path([('M', 4.88, 1.92), ('L', 5.02, 4.02), ('L', 4.92, 4.06), ('L', 4.95, 4.18), ('L', 6.52, 4.18), ('L', 6.52, 1.92), ('Z',)], 'ml')
    d.poly([(5.1, 2.62), (5.2, 3.96), (5.86, 3.96), (5.86, 2.62)], 'mw')
    d.poly([(5.96, 2.62), (5.96, 3.96), (6.38, 3.96), (6.38, 2.62)], 'mw')
    d.line(5.78, 2.48, 5.78, 2.32, 'mt')
    d.path([('M', 6.52, 1.42), ('L', 7.12, 1.42), ('Q', 7.3, 1.42, 7.3, 1.62), ('L', 7.3, 2.48), ('Q', 7.3, 2.66, 7.12, 2.66), ('L', 6.52, 2.66), ('Z',)], 'ml')
    d.rect(6.88, 2.66, 0.14, 0.12, 'ml')                                                   # filler cap
    # ripper (parallelogram frame, shank, tip)
    d.poly([(7.2, 1.0), (7.5, 1.0), (7.5, 1.7), (7.2, 1.7)], 'ml')                         # mounting bracket
    d.poly([(7.45, 1.62), (8.15, 1.42), (8.18, 1.52), (7.48, 1.72)], 'ml')                 # upper link
    d.poly([(7.45, 1.08), (8.12, 0.92), (8.15, 1.02), (7.48, 1.18)], 'ml')                 # lower link
    d.poly([(8.05, 0.8), (8.42, 0.8), (8.42, 1.6), (8.05, 1.6)], 'ml')                     # beam
    d.path([('M', 8.22, 0.85), ('L', 8.38, 0.85), ('L', 8.42, 0.28), ('Q', 8.46, 0.06, 8.7, 0.02), ('L', 8.66, 0.12), ('Q', 8.52, 0.2, 8.5, 0.32), ('L', 8.36, 0.88)], 'ml')
    d.cyl(7.25, 2.0, 8.2, 1.58, frac=0.6, w=0.2, rod=0.09)
    # blade with push arm, lift cylinder and tilt brace
    d.path([('M', 0.05, 0.02), ('L', 0.42, 0.02), ('L', 0.62, 0.3), ('L', 0.62, 2.28), ('L', 0.3, 2.42), ('L', 0.0, 2.42), ('L', 0.08, 2.3),
            ('Q', 0.52, 1.24, 0.08, 0.2), ('Z',)], 'ml')
    d.path([('M', 0.1, 2.3), ('Q', 0.56, 1.24, 0.12, 0.18)], 'mx')
    d.poly([(0.6, 0.55), (3.1, 0.62), (3.1, 0.88), (0.6, 0.86)], 'ml')                     # push arm
    d.circle(3.05, 0.75, 0.12, 'ml'); d.circle(3.05, 0.75, 0.04, 'mdot')
    d.cyl(2.3, 2.38, 0.66, 1.62, frac=0.58, w=0.22, rod=0.1)                               # lift cylinder
    d.cyl(1.95, 1.0, 0.66, 2.0, frac=0.55, w=0.16, rod=0.08)                               # tilt brace / cylinder
    # protected zones
    d.zone(1, 2.42, 1.5, 2.44, 1.18)      # engine bay
    d.zone(2, 4.98, 1.48, 0.66, 0.4)      # hydraulic pumps / valves
    d.zone(3, 5.7, 1.48, 0.86, 0.4)       # transmission / torque converter
    d.zone(4, 6.6, 2.04, 0.62, 0.52)      # battery box
    d.zone(5, 6.6, 1.48, 0.62, 0.5)       # fuel filters / pumps
    return d


def stacker():
    """45 t reach stacker (XCMG-type): 6.0 m wheelbase, 18.00-25 tyres, engine room between the axles with the cab on top,
    boom foot on a pedestal over the rear axle, counterweight at the rear, spreader turned across (seen end-on)."""
    d = D(40, 68)           # x=0 at the front end of the spreader, facing left
    fa, ra, R = 4.3, 10.3, 0.81
    # chassis with the front nose, counterweight at the rear
    d.poly([(3.05, 0.9), (11.05, 0.9), (11.05, 1.85), (3.35, 1.85), (3.05, 1.55)], 'ml')
    d.rect(2.9, 0.98, 0.26, 0.5, 'ml', r=0.05)                                      # front buffer
    d.rect(3.42, 1.58, 0.22, 0.14, 'mdot')                                          # work light
    d.lines([(3.6, 1.38, 10.9, 1.38)], 'mx')
    d.path([('M', 11.0, 0.72), ('L', 11.8, 0.72), ('Q', 12.18, 0.72, 12.18, 1.1), ('L', 12.18, 2.35), ('Q', 12.18, 2.78, 11.75, 2.78),
            ('L', 11.0, 2.78), ('Z',)], 'ml')                                        # counterweight
    d.lines([(11.15, 1.25, 12.0, 1.25), (11.15, 2.3, 12.0, 2.3)], 'mx')
    d.rect(12.06, 1.62, 0.08, 0.26, 'mdot')                                         # tail light
    # engine room between the axles (the cab sits on it)
    d.rect(5.3, 0.9, 4.0, 1.5, 'ml', r=0.06)
    d.lines([(6.38, 0.9, 6.38, 2.4), (7.42, 0.9, 7.42, 2.4)], 'mt')
    d.lines([(a, 1.12 + i * 0.16, b, 1.12 + i * 0.16) for i in range(8) for a, b in ((5.45, 6.25), (7.6, 9.15))], 'mx')   # grilles
    d.rect(8.95, 2.4, 0.13, 0.6, 'ml'); d.poly([(8.93, 3.0), (9.1, 3.0), (9.12, 3.07), (8.91, 3.04)], 'ml')   # exhaust
    # boom foot pedestal over the rear axle
    d.poly([(9.42, 1.85), (10.72, 1.85), (10.24, 3.4), (9.76, 3.4)], 'ml')
    # boom: outer section from the pivot, inner section to the head
    P, H = (10.0, 3.3), (1.7, 6.0)
    ux, uh = H[0] - P[0], H[1] - P[1]; L = math.hypot(ux, uh); ux, uh = ux / L, uh / L; nx, nh = -uh, ux
    J = (P[0] + ux * L * 0.6, P[1] + uh * L * 0.6)
    def q(p, k): return (p[0] + nx * k, p[1] + nh * k)
    d.cyl(5.25, 1.9, 5.92, 4.18, frac=0.6, w=0.34, rod=0.15)                       # lift cylinder (leans back to the boom)
    d.path([('M',) + q(H, 0.34), ('L',) + q(J, 0.34), ('L',) + q(J, -0.34), ('L',) + q(H, -0.34), ('Z',)], 'ml')   # inner boom
    d.path([('M',) + q(P, 0.46), ('L',) + q(J, 0.46), ('L',) + q(J, -0.46), ('L',) + q(P, -0.46), ('A', 0.46, 0.46, 0, 0) + q(P, 0.46), ('Z',)], 'ml')
    d.line(*q((P[0] + ux * 0.6, P[1] + uh * 0.6), 0.28), *q((J[0] - ux * 0.2, J[1] - uh * 0.2), 0.28), cls='mx')
    d.pin(*P, r=0.17)
    # head block, rotator and spreader turned across the machine (seen end-on)
    d.poly([(1.22, 5.2), (2.18, 5.2), (2.0, 5.86), (1.4, 5.86)], 'ml')
    d.circle(H[0], H[1], 0.22, 'ml'); d.circle(H[0], H[1], 0.08, 'mdot')
    d.rect(0.45, 4.6, 2.5, 0.6, 'ml')
    d.lines([(0.75, 4.6, 0.75, 5.2), (2.65, 4.6, 2.65, 5.2), (0.75, 4.9, 2.65, 4.9)], 'mt')
    d.rect(0.45, 4.36, 0.3, 0.24, 'ml'); d.rect(2.65, 4.36, 0.3, 0.24, 'ml')          # twistlock housings
    # cab on the engine room (beside the boom, nearer the viewer)
    d.path([('M', 6.6, 2.4), ('L', 6.74, 4.18), ('L', 6.64, 4.22), ('L', 6.67, 4.32), ('L', 8.2, 4.32), ('L', 8.2, 2.4), ('Z',)], 'ml')
    d.poly([(6.82, 2.92), (6.9, 4.12), (7.52, 4.12), (7.52, 2.92)], 'mw')
    d.poly([(7.62, 2.92), (7.62, 4.12), (8.06, 4.12), (8.06, 2.92)], 'mw')
    d.line(7.44, 2.78, 7.44, 2.64, 'mt')
    d.lines([(8.36, 0.5, 8.36, 2.4), (8.66, 0.5, 8.66, 2.4)] + [(8.36, 0.68 + i * 0.3, 8.66, 0.68 + i * 0.3) for i in range(6)], 'mt')   # ladder to the cab
    # wheels (twin drive tyres at the front, steer axle at the rear) with the front fender
    d.wheel(fa, R, rim=0.56); d.wheel(ra, R, rim=0.56)
    d.path([('M', fa - 0.98, 1.4), ('Q', fa - 0.92, 1.92, fa, 1.92), ('Q', fa + 0.92, 1.92, fa + 0.98, 1.4)], 'mt')
    # protected zones in the engine room: 2, then 3 over 4, then 1 over 5 (owner, 28 Nov 2026)
    d.zone(2, 5.42, 1.0, 0.86, 1.3)       # hydraulic pumps
    d.zone(3, 6.48, 1.58, 0.84, 0.72)     # transmission / torque converter
    d.zone(4, 6.48, 1.0, 0.84, 0.46)      # battery box
    d.zone(1, 7.52, 1.58, 1.66, 0.72)     # engine
    d.zone(5, 7.52, 1.0, 1.12, 0.46)      # fuel filters / pumps
    return d

ORDER = [('excavator', excavator, 'Экскаваторын'), ('truck', truck, 'Автосамосвалын'), ('loader', loader, 'Дугуйт ачигчийн'),
         ('dozer', dozer, 'Бульдозерын'), ('stacker', stacker, 'Ричстакерын')]

def main(path='docs/index.html'):
    h = open(path, encoding='utf-8').read()
    figs = list(re.finditer(r'(<figure class="zdraw">)(<svg [^>]*>)(.*?)(</svg></figure>)', h, re.S))
    if len(figs) != len(ORDER):
        sys.exit('expected %d zone drawings, found %d' % (len(ORDER), len(figs)))
    out, last = [], 0
    for m, (name, fn, label) in zip(figs, ORDER):
        if label not in m.group(2):
            sys.exit('drawing order changed: %s is not where %s was expected' % (m.group(2)[:80], name))
        d = fn()
        inner = '<line class="mg" x1="24" y1="%d" x2="616" y2="%d"/>' % (G, G) + ''.join(d.out) + ''.join(d.render_zones())
        old = sorted(re.findall(r'<text class="zt"[^>]*>(\d)</text>', m.group(3)))
        new = sorted(re.findall(r'<text class="zt"[^>]*>(\d)</text>', inner))
        if old != new:
            sys.exit('%s: zones %s do not match the page (%s); change the legend first' % (name, new, old))
        out += [h[last:m.start()], m.group(1) + m.group(2) + inner + m.group(4)]
        last = m.end()
    out.append(h[last:])
    open(path, 'w', encoding='utf-8').write(''.join(out))
    print('wrote %d drawings to %s' % (len(ORDER), path))

if __name__ == '__main__':
    main(*sys.argv[1:])
