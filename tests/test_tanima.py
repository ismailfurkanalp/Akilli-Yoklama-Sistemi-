"""Eşleştirme ve yoklama karar mantığı testleri (kamera gerekmez).
Gerçek yüz yerine yapay 128 boyutlu vektörler kullanılır."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from src import config, database as db, yuz_isleme as yi
from src.tanima import ONAY_KARE_SAYISI, TanimaDurumu, yuzleri_degerlendir


def vektor(tohum, gurultu=0.0):
    rng = np.random.default_rng(tohum)
    v = rng.normal(0, 0.1, 128)
    if gurultu:
        v = v + np.random.default_rng(tohum + 1000).normal(0, gurultu, 128)
    return v


class EslestirmeTestleri(unittest.TestCase):
    def test_bos_liste(self):
        self.assertEqual(yi.en_yakin_eslesme(vektor(1), np.empty((0, 128)))[0], None)

    def test_en_yakin_bulunur(self):
        kayitli = np.vstack([vektor(1), vektor(2), vektor(3)])
        i, m = yi.en_yakin_eslesme(vektor(2, gurultu=0.01), kayitli)
        self.assertEqual(i, 1)
        self.assertLess(m, config.ESLESME_ESIGI)

    def test_esik_ustu_bilinmeyen(self):
        kayitli = np.vstack([vektor(1)])
        i, m = yi.en_yakin_eslesme(vektor(1) + 1.0, kayitli)   # çok uzak
        self.assertIsNone(i)
        self.assertGreater(m, config.ESLESME_ESIGI)

    def test_ortalama_vektor(self):
        o = yi.ortalama_vektor([np.zeros(128), np.ones(128) * 2])
        self.assertTrue(np.allclose(o, 1))
        with self.assertRaises(ValueError):
            yi.ortalama_vektor([])


class YoklamaKarariTestleri(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.yama = mock.patch.object(config, "DB_YOLU", Path(self.gecici.name) / "t.db")
        self.yama.start()
        db.veritabanini_olustur()
        self.ali = db.kullanici_ve_yuz_ekle("Ali", "Yılmaz", "Öğrenci", vektor(1))
        self.ayse = db.kullanici_ve_yuz_ekle("Ayşe", "Demir", "Öğrenci", vektor(2))
        self.durum = TanimaDurumu()
        self.durum.vektorleri_yukle()

    def tearDown(self):
        self.yama.stop()
        self.gecici.cleanup()

    def kare(self, *vektorler, t=1000.0):
        yuzler = [yi.Yuz(0, 10, 10, 0, v) for v in vektorler]
        return yuzleri_degerlendir(self.durum, yuzler, simdi=t)

    def test_onay_icin_ardisik_kare_gerekir(self):
        for _ in range(ONAY_KARE_SAYISI - 1):
            self.kare(vektor(1, 0.01))
        self.assertEqual(db.yoklamalari_listele(), [])           # henüz kayıt yok
        self.kare(vektor(1, 0.01))
        kayitlar = db.yoklamalari_listele()
        self.assertEqual([k["Kullanici_ID"] for k in kayitlar], [self.ali])

    def test_kesintide_sayac_sifirlanir(self):
        self.kare(vektor(1, 0.01))
        self.kare(vektor(1, 0.01))
        self.kare()                                               # kişi kadrajdan çıktı
        self.kare(vektor(1, 0.01))
        self.assertEqual(db.yoklamalari_listele(), [])

    def test_bilinmeyen_kaydedilmez(self):
        for _ in range(ONAY_KARE_SAYISI + 2):
            sonuc = self.kare(vektor(99))
        self.assertEqual(sonuc[0][1], "Bilinmeyen Kişi")
        self.assertEqual(db.yoklamalari_listele(), [])

    def test_iki_kisi_ayni_anda(self):
        for _ in range(ONAY_KARE_SAYISI):
            self.kare(vektor(1, 0.01), vektor(2, 0.01))
        self.assertEqual({k["Kullanici_ID"] for k in db.yoklamalari_listele()}, {self.ali, self.ayse})

    def test_kadrajda_bekleyen_tek_kayit(self):
        for i in range(30):                                      # 30 kare boyunca kamerada duruyor
            self.kare(vektor(1, 0.01), t=1000.0 + i * 0.2)
        self.assertEqual(len(db.yoklamalari_listele()), 1)


class DayaniklilikTestleri(unittest.TestCase):
    """Cloudflare 18 Kasım 2025 kesintisinden alınan ders: yüklenen veri doğrulanmalı,
    hatalı veri tüm sistemi çökertmemeli."""

    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.yama = mock.patch.object(config, "DB_YOLU", Path(self.gecici.name) / "t.db")
        self.yama.start()
        db.veritabanini_olustur()
        self.ali = db.kullanici_ve_yuz_ekle("Ali", "Yılmaz", "Öğrenci", vektor(1))
        self.ayse = db.kullanici_ve_yuz_ekle("Ayşe", "Demir", "Öğrenci", vektor(2))

    def tearDown(self):
        self.yama.stop()
        self.gecici.cleanup()

    def test_bozuk_vektor_atlanir_digerleri_calisir(self):
        with db.baglanti() as conn:   # Ayşe'nin vektörünü yarı boyuta düşürerek boz
            conn.execute("UPDATE YUZ_VEKTORU SET Vektor_Verisi = ? WHERE Kullanici_ID = ?",
                         (np.zeros(64).tobytes(), self.ayse))
        kisiler, matris = db.tum_yuz_vektorleri()
        self.assertEqual([k["Kullanici_ID"] for k in kisiler], [self.ali])
        self.assertEqual(matris.shape, (1, 128))

    def test_okuma_hatasinda_onceki_liste_korunur(self):
        durum = TanimaDurumu()
        self.assertTrue(durum.vektorleri_yukle())
        with mock.patch.object(db, "tum_yuz_vektorleri", side_effect=RuntimeError("disk hatası")):
            self.assertFalse(durum.vektorleri_yukle())
        self.assertEqual(len(durum.kisiler), 2)          # son sağlam liste duruyor


class AtomikKayitTesti(unittest.TestCase):
    def test_hatali_vektorde_kullanici_da_eklenmez(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "t.db"
            db.veritabanini_olustur(yol)
            with self.assertRaises(ValueError):
                db.kullanici_ve_yuz_ekle("Ali", "Yılmaz", "Öğrenci", np.zeros(10), db_yolu=yol)
            self.assertEqual(db.kullanicilari_listele(db_yolu=yol), [])


if __name__ == "__main__":
    unittest.main()
