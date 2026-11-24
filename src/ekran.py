"""Kamera penceresine çizim yardımcıları.

OpenCV'nin cv2.putText fonksiyonu Türkçe karakterleri (ş, ğ, ü, ı...) çizemez ("?" basar).
Bu yüzden yazılar Pillow ile çizilir.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Renkler (BGR - OpenCV düzeni)
YESIL = (60, 180, 75)
SARI = (0, 200, 255)
KIRMIZI = (40, 40, 220)
BEYAZ = (255, 255, 255)
SIYAH = (0, 0, 0)

_FONT_ADAYLARI = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


@lru_cache(maxsize=8)
def _font(boyut: int):
    for yol in _FONT_ADAYLARI:
        if Path(yol).exists():
            return ImageFont.truetype(yol, boyut)
    return ImageFont.load_default()


def yazilar_ciz(kare: np.ndarray, yazilar: list[tuple[str, tuple[int, int], tuple, int]],
                arka_plan: bool = True) -> np.ndarray:
    """Birden çok yazıyı tek seferde çizer (hızlı olsun diye tek dönüşüm).
    yazilar: [(metin, (x, y), renk_bgr, punto), ...]  - (x, y) yazının sol üst köşesi."""
    if not yazilar:
        return kare
    img = Image.fromarray(cv2.cvtColor(kare, cv2.COLOR_BGR2RGB))
    ciz = ImageDraw.Draw(img)
    for metin, (x, y), renk, punto in yazilar:
        f = _font(punto)
        rgb = (renk[2], renk[1], renk[0])
        if arka_plan:
            l, t, r, b = ciz.textbbox((x, y), metin, font=f)
            ciz.rectangle((l - 5, t - 4, r + 5, b + 4), fill=(0, 0, 0))
        ciz.text((x, y), metin, font=f, fill=rgb)
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


def kutu_ciz(kare: np.ndarray, yuz, renk, kalinlik: int = 2) -> None:
    cv2.rectangle(kare, (yuz.sol, yuz.ust), (yuz.sag, yuz.alt), renk, kalinlik)
