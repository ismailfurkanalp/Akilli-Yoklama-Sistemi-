"""database.py için birim testleri. Çalıştırma: python -m unittest -v"""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from src import database as db


class VeritabaniTestleri(unittest.TestCase):
    def setUp(self):
        # Her test kendi geçici veri tabanını kullanır; gerçek yoklama.db'ye dokunulmaz.
        self.gecici = tempfile.TemporaryDirectory()
        self.yol = Path(self.gecici.name) / "test.db"
        db.veritabanini_olustur(self.yol)

    def tearDown(self):
        self.gecici.cleanup()

    def _kisi(self, ad="Ali", soyad="Yılmaz", rol="Öğrenci"):
        return db.kullanici_ekle(ad, soyad, rol, db_yolu=self.yol)

    # ---- KULLANICI
    def test_kullanici_ekle_ve_getir(self):
        kid = self._kisi()
        k = db.kullanici_getir(kid, db_yolu=self.yol)
        self.assertEqual((k["Ad"], k["Soyad"], k["Rol"]), ("Ali", "Yılmaz", "Öğrenci"))

    def test_gecersiz_rol_reddedilir(self):
        with self.assertRaises(ValueError):
            self._kisi(rol="Müdür")

    def test_bos_ad_reddedilir(self):
        with self.assertRaises(ValueError):
            self._kisi(ad="  ")

    def test_kullanici_guncelle(self):
        kid = self._kisi()
        self.assertTrue(db.kullanici_guncelle(kid, soyad="Kaya", rol="Hoca", db_yolu=self.yol))
        k = db.kullanici_getir(kid, db_yolu=self.yol)
        self.assertEqual((k["Soyad"], k["Rol"]), ("Kaya", "Hoca"))
        self.assertFalse(db.kullanici_guncelle(999, ad="X", db_yolu=self.yol))

    def test_listele_yuz_kayitli_bilgisi(self):
        a, b = self._kisi("Ali"), self._kisi("Ayşe", "Demir")
        db.yuz_vektoru_kaydet(a, np.ones(128), db_yolu=self.yol)
        liste = {k["Kullanici_ID"]: k["Yuz_Kayitli"] for k in db.kullanicilari_listele(db_yolu=self.yol)}
        self.assertEqual(liste, {a: 1, b: 0})

    # ---- YUZ_VEKTORU
    def test_vektor_kaydet_ve_oku(self):
        kid = self._kisi()
        v = np.random.rand(128)
        db.yuz_vektoru_kaydet(kid, v, db_yolu=self.yol)
        np.testing.assert_array_equal(db.yuz_vektoru_getir(kid, db_yolu=self.yol), v)

    def test_vektor_bire_bir_guncellenir(self):
        kid = self._kisi()
        db.yuz_vektoru_kaydet(kid, np.zeros(128), db_yolu=self.yol)
        db.yuz_vektoru_kaydet(kid, np.ones(128), db_yolu=self.yol)   # ikinci kayıt eskisinin yerine geçer
        kisiler, matris = db.tum_yuz_vektorleri(db_yolu=self.yol)
        self.assertEqual(matris.shape, (1, 128))
        self.assertTrue((matris[0] == 1).all())

    def test_yanlis_boyutlu_vektor_reddedilir(self):
        kid = self._kisi()
        with self.assertRaises(ValueError):
            db.yuz_vektoru_kaydet(kid, np.zeros(64), db_yolu=self.yol)

    def test_olmayan_kullaniciya_vektor_eklenemez(self):
        with self.assertRaises(Exception):   # yabancı anahtar ihlali
            db.yuz_vektoru_kaydet(999, np.zeros(128), db_yolu=self.yol)

    # ---- YOKLAMA
    def test_bekleme_suresi(self):
        kid = self._kisi()
        t0 = datetime(2026, 11, 23, 9, 0)
        self.assertIsNotNone(db.yoklama_ekle(kid, t0, db_yolu=self.yol))
        self.assertIsNone(db.yoklama_ekle(kid, t0 + timedelta(minutes=5), db_yolu=self.yol))
        self.assertIsNotNone(db.yoklama_ekle(kid, t0 + timedelta(minutes=10), db_yolu=self.yol))
        self.assertEqual(len(db.yoklamalari_listele(kullanici_id=kid, db_yolu=self.yol)), 2)

    def test_tarihe_gore_filtre(self):
        kid = self._kisi()
        db.yoklama_ekle(kid, datetime(2026, 11, 23, 9, 0), db_yolu=self.yol)
        db.yoklama_ekle(kid, datetime(2026, 11, 24, 9, 0), db_yolu=self.yol)
        self.assertEqual(len(db.yoklamalari_listele(tarih="2026-11-24", db_yolu=self.yol)), 1)

    def test_silme_cascade(self):
        kid = self._kisi()
        db.yuz_vektoru_kaydet(kid, np.ones(128), db_yolu=self.yol)
        db.yoklama_ekle(kid, datetime(2026, 11, 23, 9, 0), db_yolu=self.yol)
        self.assertTrue(db.kullanici_sil(kid, db_yolu=self.yol))
        self.assertIsNone(db.yuz_vektoru_getir(kid, db_yolu=self.yol))
        self.assertEqual(db.yoklamalari_listele(db_yolu=self.yol), [])


if __name__ == "__main__":
    unittest.main()
