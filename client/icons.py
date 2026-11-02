"""Vector-style icons drawn locally with Pillow (no internet, no icon fonts)."""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Callable, Dict, Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw

from . import theme

SS = 4  # supersampling factor


def _canvas(size: int):
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), s


def _ellipse_pts(cx, cy, rx, ry, rot, n=60):
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return pts


def _line(d, pts, c, w):
    d.line(pts, fill=c, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=c)


def _glyph(name: str, d: ImageDraw.ImageDraw, s: int, c: str) -> None:
    w = max(2, round(s / 11))
    P = lambda *pts: [(x * s, y * s) for x, y in pts]
    if name == "dashboard":
        for x, y in ((.14, .14), (.54, .14), (.14, .54), (.54, .54)):
            d.rounded_rectangle([x * s, y * s, (x + .32) * s, (y + .32) * s], radius=s * .06, outline=c, width=w)
    elif name == "send":
        _line(d, P((.1, .5), (.9, .12), (.62, .9), (.5, .58), (.1, .5)), c, w)
        _line(d, P((.5, .58), (.9, .12)), c, w)
    elif name in ("inbox", "sent"):
        _line(d, P((.12, .55), (.3, .55), (.36, .72), (.64, .72), (.7, .55), (.88, .55)), c, w)
        _line(d, P((.12, .55), (.24, .2), (.76, .2), (.88, .55), (.88, .86), (.12, .86), (.12, .55)), c, w)
        if name == "sent":
            _line(d, P((.5, .55), (.5, .3)), c, w); _line(d, P((.4, .4), (.5, .3), (.6, .4)), c, w)
    elif name == "file":
        _line(d, P((.22, .1), (.62, .1), (.8, .28), (.8, .9), (.22, .9), (.22, .1)), c, w)
        _line(d, P((.62, .1), (.62, .28), (.8, .28)), c, w)
        _line(d, P((.34, .52), (.68, .52)), c, w); _line(d, P((.34, .7), (.68, .7)), c, w)
    elif name == "lab":
        for rot in (0, math.pi / 3, -math.pi / 3):
            d.line(_ellipse_pts(.5 * s, .5 * s, .42 * s, .16 * s, rot), fill=c, width=w, joint="curve")
        d.ellipse([.42 * s, .42 * s, .58 * s, .58 * s], fill=c)
    elif name == "activity":
        _line(d, P((.08, .55), (.3, .55), (.4, .2), (.55, .85), (.66, .45), (.72, .55), (.92, .55)), c, w)
    elif name == "profile":
        d.ellipse([.33 * s, .12 * s, .67 * s, .46 * s], outline=c, width=w)
        d.arc([.14 * s, .55 * s, .86 * s, 1.25 * s], 180, 360, fill=c, width=w)
    elif name == "settings":
        for i in range(8):
            a = i * math.pi / 4
            _line(d, [(s / 2 + .3 * s * math.cos(a), s / 2 + .3 * s * math.sin(a)),
                      (s / 2 + .43 * s * math.cos(a), s / 2 + .43 * s * math.sin(a))], c, w + 1)
        d.ellipse([.24 * s, .24 * s, .76 * s, .76 * s], outline=c, width=w)
        d.ellipse([.4 * s, .4 * s, .6 * s, .6 * s], outline=c, width=w)
    elif name == "about":
        d.ellipse([.1 * s, .1 * s, .9 * s, .9 * s], outline=c, width=w)
        _line(d, P((.5, .44), (.5, .72)), c, w); d.ellipse([.45 * s, .26 * s, .55 * s, .36 * s], fill=c)
    elif name == "logout":
        _line(d, P((.42, .12), (.14, .12), (.14, .88), (.42, .88)), c, w)
        _line(d, P((.35, .5), (.88, .5)), c, w); _line(d, P((.7, .3), (.9, .5), (.7, .7)), c, w)
    elif name == "sun":
        d.ellipse([.3 * s, .3 * s, .7 * s, .7 * s], outline=c, width=w)
        for i in range(8):
            a = i * math.pi / 4
            _line(d, [(s / 2 + .32 * s * math.cos(a), s / 2 + .32 * s * math.sin(a)),
                      (s / 2 + .45 * s * math.cos(a), s / 2 + .45 * s * math.sin(a))], c, w)
    elif name == "moon":
        d.ellipse([.14 * s, .14 * s, .86 * s, .86 * s], fill=c)
        d.ellipse([.34 * s, .04 * s, 1.0 * s, .7 * s], fill=(0, 0, 0, 0))
    elif name == "lock":
        d.rounded_rectangle([.2 * s, .44 * s, .8 * s, .9 * s], radius=s * .08, outline=c, width=w)
        d.arc([.3 * s, .1 * s, .7 * s, .7 * s], 180, 360, fill=c, width=w)
        d.ellipse([.45 * s, .58 * s, .55 * s, .68 * s], fill=c)
    elif name == "shield":
        _line(d, P((.5, .08), (.86, .22), (.82, .58), (.5, .92), (.18, .58), (.14, .22), (.5, .08)), c, w)
        _line(d, P((.34, .5), (.46, .62), (.68, .38)), c, w)
    elif name == "check":
        _line(d, P((.18, .52), (.4, .74), (.84, .26)), c, w + 1)
    elif name == "warning":
        _line(d, P((.5, .1), (.92, .86), (.08, .86), (.5, .1)), c, w)
        _line(d, P((.5, .38), (.5, .62)), c, w); d.ellipse([.45 * s, .7 * s, .55 * s, .8 * s], fill=c)
    elif name == "error":
        d.ellipse([.1 * s, .1 * s, .9 * s, .9 * s], outline=c, width=w)
        _line(d, P((.33, .33), (.67, .67)), c, w); _line(d, P((.67, .33), (.33, .67)), c, w)
    elif name == "search":
        d.ellipse([.12 * s, .12 * s, .62 * s, .62 * s], outline=c, width=w)
        _line(d, P((.56, .56), (.88, .88)), c, w)
    elif name in ("download", "upload"):
        y0, y1 = (.12, .68) if name == "download" else (.68, .12)
        _line(d, P((.5, y0), (.5, y1)), c, w)
        tip = y1
        _line(d, P((.28, tip - .2 if name == "download" else tip + .2), (.5, tip), (.72, tip - .2 if name == "download" else tip + .2)), c, w)
        _line(d, P((.14, .88), (.86, .88)), c, w)
    elif name in ("eye", "eye_off"):
        d.line(_ellipse_pts(.5 * s, .5 * s, .42 * s, .26 * s, 0), fill=c, width=w, joint="curve")
        d.ellipse([.38 * s, .38 * s, .62 * s, .62 * s], outline=c, width=w)
        if name == "eye_off":
            _line(d, P((.14, .86), (.86, .14)), c, w + 1)
    elif name == "refresh":
        d.arc([.14 * s, .14 * s, .86 * s, .86 * s], 30, 320, fill=c, width=w)
        _line(d, P((.78, .1), (.86, .3), (.66, .34)), c, w)
    elif name == "user_add":
        _glyph("profile", d, s, c)
    elif name == "dot":
        d.ellipse([.2 * s, .2 * s, .8 * s, .8 * s], fill=c)
    else:
        d.rounded_rectangle([.2 * s, .2 * s, .8 * s, .8 * s], radius=s * .1, outline=c, width=w)


@lru_cache(maxsize=None)
def _render(name: str, size: int, color: str) -> Image.Image:
    img, d, s = _canvas(size)
    _glyph(name, d, s, color)
    return img.resize((size, size), Image.LANCZOS)


def icon(name: str, size: int = 20, color: Optional[theme.Pair] = None) -> ctk.CTkImage:
    """CTkImage that follows the light/dark theme automatically."""
    light, dark = color or theme.TEXT
    return ctk.CTkImage(light_image=_render(name, size * 2, light), dark_image=_render(name, size * 2, dark),
                        size=(size, size))


def fixed_icon(name: str, size: int, color: str) -> ctk.CTkImage:
    img = _render(name, size * 2, color)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ---------------------------------------------------------------- logo / art
def _logo_image(size: int, shield: str, accent: str, cross: str = "#FFFFFF") -> Image.Image:
    img, d, s = _canvas(size)
    pts = [(.5, .04), (.9, .18), (.86, .58), (.5, .96), (.14, .58), (.1, .18)]
    d.polygon([(x * s, y * s) for x, y in pts], fill=shield)
    inner = [(.5, .12), (.82, .24), (.79, .56), (.5, .88), (.21, .56), (.18, .24)]
    d.line([(x * s, y * s) for x, y in inner + [inner[0]]], fill=accent, width=max(2, s // 40), joint="curve")
    t = .09
    d.rectangle([(.5 - t) * s, .26 * s, (.5 + t) * s, .74 * s], fill=cross)
    d.rectangle([.26 * s, (.5 - t) * s, .74 * s, (.5 + t) * s], fill=cross)
    for x, y in ((.5, .26), (.5, .74), (.26, .5), (.74, .5)):   # quantum-circuit nodes
        d.ellipse([(x - .045) * s, (y - .045) * s, (x + .045) * s, (y + .045) * s], fill=accent)
    return img.resize((size, size), Image.LANCZOS)


def logo(size: int = 40) -> ctk.CTkImage:
    return ctk.CTkImage(light_image=_logo_image(size * 2, "#0A6CB5", "#19C6D6"),
                        dark_image=_logo_image(size * 2, "#1E88D8", "#5EE0EC"), size=(size, size))


def hero_illustration(width: int = 520, height: int = 340) -> ctk.CTkImage:
    def make(dark: bool) -> Image.Image:
        S = 2
        W, H = width * S, height * S
        bg, card, line = ("#0F2A43", "#173A58", "#2C5878") if dark else ("#E4EEF6", "#FFFFFF", "#B9CEDF")
        blue, teal, green = ("#3B9CE8", "#3CCBE8", "#2BC48A") if dark else ("#0A6CB5", "#0B8F9C", "#0F9D6A")
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=28 * S, fill=bg)

        def doc(x, y, accent):
            d.rounded_rectangle([x, y, x + 110 * S, y + 140 * S], radius=12 * S, fill=card, outline=line, width=2 * S)
            d.rectangle([x + 46 * S, y + 22 * S, x + 64 * S, y + 60 * S], fill=accent)
            d.rectangle([x + 32 * S, y + 36 * S, x + 78 * S, y + 46 * S], fill=accent)
            for i in range(3):
                d.rounded_rectangle([x + 20 * S, y + (78 + i * 16) * S, x + (90 - i * 12) * S, y + (84 + i * 16) * S],
                                    radius=3 * S, fill=line)
        doc(40 * S, 100 * S, blue)
        doc(W - 150 * S, 100 * S, teal)
        cx, cy = W // 2, 170 * S
        for i in range(12):   # dotted quantum channel
            x = 160 * S + i * ((W - 320 * S) // 11)
            r = 4 * S if i % 2 else 3 * S
            d.ellipse([x - r, cy - r, x + r, cy + r], fill=teal if i % 2 else blue)
        pts = [(cx, cy - 62 * S), (cx + 46 * S, cy - 44 * S), (cx + 42 * S, cy + 12 * S), (cx, cy + 62 * S),
               (cx - 42 * S, cy + 12 * S), (cx - 46 * S, cy - 44 * S)]
        d.polygon(pts, fill=blue, outline=teal, width=3 * S)
        d.rounded_rectangle([cx - 18 * S, cy - 8 * S, cx + 18 * S, cy + 24 * S], radius=5 * S, fill="#FFFFFF")
        d.arc([cx - 12 * S, cy - 30 * S, cx + 12 * S, cy + 2 * S], 180, 360, fill="#FFFFFF", width=4 * S)
        d.ellipse([cx - 4 * S, cy + 4 * S, cx + 4 * S, cy + 12 * S], fill=green)
        return img.resize((width, height), Image.LANCZOS)
    return ctk.CTkImage(light_image=make(False), dark_image=make(True), size=(width, height))


def empty_illustration(kind: str = "inbox", size: int = 150) -> ctk.CTkImage:
    def make(dark: bool) -> Image.Image:
        S = 2
        n = size * S
        card, line = ("#173A58", "#2C5878") if dark else ("#FFFFFF", "#B9CEDF")
        blue, teal = ("#3B9CE8", "#3CCBE8") if dark else ("#0A6CB5", "#0B8F9C")
        img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([n * .08, n * .08, n * .92, n * .92], fill=("#0F2A43" if dark else "#E4EEF6"))
        d.rounded_rectangle([n * .3, n * .2, n * .7, n * .72], radius=n * .05, fill=card, outline=line, width=2 * S)
        for i in range(3):
            d.rounded_rectangle([n * .38, n * (.32 + i * .1), n * (.62 - i * .05), n * (.35 + i * .1)], radius=3, fill=line)
        d.polygon([(n * .62, n * .5), (n * .84, n * .58), (n * .82, n * .76), (n * .62, n * .9), (n * .42, n * .76),
                   (n * .4, n * .58)], fill=blue if kind == "inbox" else teal)
        d.line([(n * .53, n * .72), (n * .6, n * .8), (n * .73, n * .64)], fill="#FFFFFF", width=3 * S, joint="curve")
        return img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=make(False), dark_image=make(True), size=(size, size))
