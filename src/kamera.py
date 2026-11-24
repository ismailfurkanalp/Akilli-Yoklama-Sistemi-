"""Kamera yardımcıları: açma ve "kamera kapalı/engelli" durumunu fark etme.

Kamera gizlilik kapağı/tuşu kapalıyken Windows hata vermez; programa siyah bir
"üstü çizili kamera" resmi gönderir. Bu dosya o durumu fark edip kullanıcıyı uyarır.
"""
from __future__ import annotations

import cv2
import numpy as np

from src import config

ENGEL_MESAJI = "Kamera kapalı görünüyor - kamera kapağını kontrol edin"


def kamera_ac() -> cv2.VideoCapture | None:
    kam = cv2.VideoCapture(config.KAMERA_INDEX, cv2.CAP_DSHOW)
    if not kam.isOpened():
        print("HATA: Kamera açılamadı. Başka bir program kamerayı kullanıyor olabilir "
              f"veya KAMERA_INDEX ({config.KAMERA_INDEX}) yanlış.")
        return None
    return kam


def karanlik_mi(kare: np.ndarray) -> bool:
    """Karenin %85'ten fazlası neredeyse siyahsa True (kamera kapalı/engelli ya da ortam çok karanlık)."""
    gri = cv2.cvtColor(cv2.resize(kare, (160, 120)), cv2.COLOR_BGR2GRAY)
    return float((gri < 20).mean()) > 0.85


class EngelTakibi:
    """Art arda belirli sayıda karanlık kare gelirse uyarı verir (tek karelik kararmada uyarmaz)."""

    def __init__(self, esik_kare: int = 20):
        self.esik_kare = esik_kare
        self.sayac = 0

    def guncelle(self, kare: np.ndarray) -> bool:
        self.sayac = self.sayac + 1 if karanlik_mi(kare) else 0
        return self.sayac >= self.esik_kare
