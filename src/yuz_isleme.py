"""Yüz tespiti, 128 boyutlu vektör çıkarma ve eşleştirme (6. hafta: Backend I).

Kayıt modülü (kayit.py) ve tanıma döngüsü (tanima.py) bu dosyayı ortak kullanır.
Hiçbir yerde fotoğraf saklanmaz; yalnızca vektörler veri tabanına gider (KVKK).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from src import config

_fr = None


def _face_recognition():
    """face_recognition modelleri yüklemesi birkaç saniye sürdüğü için ilk kullanımda yüklenir."""
    global _fr
    if _fr is None:
        import warnings
        warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
        import face_recognition
        _fr = face_recognition
    return _fr


@dataclass
class Yuz:
    """Karede bulunan bir yüz. Konum, ORİJİNAL karenin piksel koordinatlarıdır."""
    ust: int
    sag: int
    alt: int
    sol: int
    vektor: np.ndarray | None = None

    @property
    def alan(self) -> int:
        return (self.alt - self.ust) * (self.sag - self.sol)


def yuzleri_bul(kare_bgr: np.ndarray, vektor_cikar: bool = True,
                olcek: float = config.ISLEME_OLCEGI) -> list[Yuz]:
    """Karedeki yüzleri bulur, istenirse her biri için 128 boyutlu vektör çıkarır.

    Hız için kare önce küçültülür (olcek), bulunan konumlar orijinal boyuta geri çevrilir.
    """
    fr = _face_recognition()
    kucuk = cv2.resize(kare_bgr, (0, 0), fx=olcek, fy=olcek) if olcek != 1 else kare_bgr
    rgb = np.ascontiguousarray(cv2.cvtColor(kucuk, cv2.COLOR_BGR2RGB))  # OpenCV BGR, dlib RGB ister
    konumlar = fr.face_locations(rgb, model="hog")
    vektorler = fr.face_encodings(rgb, konumlar) if (vektor_cikar and konumlar) else [None] * len(konumlar)
    k = 1 / olcek
    return [Yuz(int(u * k), int(s * k), int(a * k), int(l * k), v)
            for (u, s, a, l), v in zip(konumlar, vektorler)]


def mesafeler(vektor: np.ndarray, kayitli: np.ndarray) -> np.ndarray:
    """Bir vektörün kayıtlı tüm vektörlere Öklid mesafesi (face_recognition.face_distance ile aynı)."""
    if len(kayitli) == 0:
        return np.empty(0)
    return np.linalg.norm(kayitli - np.asarray(vektor), axis=1)


def en_yakin_eslesme(vektor: np.ndarray, kayitli: np.ndarray,
                     esik: float = config.ESLESME_ESIGI) -> tuple[int | None, float]:
    """En yakın kayıtlı yüzü bulur.
    Dönüş: (kayitli içindeki sıra numarası veya eşik aşıldıysa None, en küçük mesafe)."""
    m = mesafeler(vektor, kayitli)
    if m.size == 0:
        return None, float("inf")
    i = int(np.argmin(m))
    return (i if m[i] <= esik else None), float(m[i])


def ortalama_vektor(ornekler: list[np.ndarray]) -> np.ndarray:
    """Kayıt sırasında alınan birkaç örneğin ortalaması: tek kareye göre daha kararlı bir vektör verir."""
    if not ornekler:
        raise ValueError("En az bir örnek gerekli.")
    return np.mean(np.vstack(ornekler), axis=0)
