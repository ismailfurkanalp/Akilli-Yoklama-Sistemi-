"""Kamera kapalı/engelli algılama testleri (gerçek kamera gerekmez)."""
import unittest

import numpy as np

from src.kamera import EngelTakibi, karanlik_mi


def kapali_kare():
    """Windows'un kamera kapalıyken gönderdiği resme benzer: siyah zemin, ortada küçük beyaz simge."""
    k = np.zeros((480, 640, 3), np.uint8)
    k[200:280, 280:360] = 255
    return k


class KameraTestleri(unittest.TestCase):
    def test_kapali_kare_karanlik(self):
        self.assertTrue(karanlik_mi(kapali_kare()))

    def test_normal_kare_karanlik_degil(self):
        rng = np.random.default_rng(0)
        self.assertFalse(karanlik_mi(rng.integers(40, 220, (480, 640, 3), dtype=np.uint8)))

    def test_uyari_ardisik_karelerden_sonra(self):
        t = EngelTakibi(esik_kare=5)
        sonuc = [t.guncelle(kapali_kare()) for _ in range(5)]
        self.assertEqual(sonuc, [False] * 4 + [True])
        self.assertFalse(t.guncelle(np.full((480, 640, 3), 128, np.uint8)))   # görüntü geldi: sıfırlanır


if __name__ == "__main__":
    unittest.main()
