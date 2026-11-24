"""Canlı yüz tanıma ve otomatik yoklama döngüsü (7. hafta: Backend II).

Kullanım (proje klasöründe, sanal ortam açıkken):
    python -m src.tanima

Akış (3. hafta algoritma şemasıyla aynı):
    kare oku -> yüz var mı? -> vektör çıkar -> kayıtlı vektörlerle Öklid mesafesi
    -> mesafe <= eşik mi? -> son kayıttan bu yana 10 dk geçti mi? -> YOKLAMA'ya ekle
"""
from __future__ import annotations

import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

import cv2
import numpy as np

from src import config, database as db, ekran, kamera as kmr, yuz_isleme as yi

PENCERE = "Akilli Yoklama"
ONAY_KARE_SAYISI = 3     # Aynı kişi art arda bu kadar işlenen karede tanınınca yoklama alınır
TEKRAR_SORGU_SN = 60     # İşlenmiş bir kişi için veri tabanı bu süre boyunca tekrar sorgulanmaz


@dataclass
class TanimaDurumu:
    """Kareler arasında taşınan durum. Kamera olmadan test edilebilsin diye ayrı tutuldu."""
    kisiler: list = field(default_factory=list)
    matris: object = None
    ardisik: dict = field(default_factory=dict)      # kullanici_id -> art arda tanınma sayısı
    son_islem: dict = field(default_factory=dict)    # kullanici_id -> (zaman, sonuç)
    mesajlar: deque = field(default_factory=lambda: deque(maxlen=4))

    def vektorleri_yukle(self) -> bool:
        """Kayıtlı yüzleri yeniden okur. Okuma başarısız olursa program çökmez;
        son sağlam liste kullanılmaya devam edilir (bilinen-iyi sürüme dönme)."""
        try:
            self.kisiler, self.matris = db.tum_yuz_vektorleri()
            return True
        except Exception as e:
            print(f"UYARI: Kayıtlı yüzler yeniden okunamadı ({type(e).__name__}: {e}); "
                  "önceki liste kullanılmaya devam ediliyor.")
            if self.matris is None:
                self.kisiler, self.matris = [], np.empty((0, config.VEKTOR_BOYUTU))
            return False

    def mesaj(self, metin: str, renk) -> None:
        self.mesajlar.append((time.time(), metin, renk))
        print(f"[{datetime.now():%H:%M:%S}] {metin}")


def yuzleri_degerlendir(durum: TanimaDurumu, yuzler: list, simdi: float | None = None) -> list:
    """Bulunan yüzleri kayıtlılarla eşleştirir, gerekiyorsa yoklama yazar.
    Dönüş: çizim için [(yuz, etiket, renk), ...]"""
    simdi = simdi or time.time()
    sonuc, gorulen = [], set()
    for yuz in yuzler:
        i, mesafe = yi.en_yakin_eslesme(yuz.vektor, durum.matris)
        if i is None:
            sonuc.append((yuz, "Bilinmeyen Kişi", ekran.KIRMIZI))
            continue
        kisi = durum.kisiler[i]
        kid = kisi["Kullanici_ID"]
        ad = f"{kisi['Ad']} {kisi['Soyad']}"
        gorulen.add(kid)
        durum.ardisik[kid] = durum.ardisik.get(kid, 0) + 1

        onceki = durum.son_islem.get(kid)
        if onceki and simdi - onceki[0] < TEKRAR_SORGU_SN:
            etiket, renk = f"{ad} · alındı", ekran.YESIL                 # yakın zamanda işlendi
        elif durum.ardisik[kid] < ONAY_KARE_SAYISI:
            etiket, renk = f"{ad} ({mesafe:.2f})", ekran.SARI     # henüz doğrulanıyor
        else:
            log_id = db.yoklama_ekle(kid)
            durum.son_islem[kid] = (simdi, log_id)
            if log_id:
                durum.mesaj(f"Yoklama alındı: {ad}", ekran.YESIL)
            else:
                durum.mesaj(f"{ad}: son {config.BEKLEME_SURESI_DK} dk içinde zaten kaydedilmiş",
                            ekran.SARI)
            etiket, renk = f"{ad} · alındı", ekran.YESIL
        sonuc.append((yuz, etiket, renk))

    # Bu karede görünmeyen kişilerin ardışık sayacı sıfırlanır (tek karelik yanlış eşleşmeyi önler)
    for kid in list(durum.ardisik):
        if kid not in gorulen:
            del durum.ardisik[kid]
    return sonuc


def ciz(kare, sonuclar, durum: TanimaDurumu, fps: float):
    yazilar = []
    for yuz, etiket, renk in sonuclar:
        ekran.kutu_ciz(kare, yuz, renk)
        yazilar.append((etiket, (yuz.sol, max(0, yuz.ust - 30)), renk, 18))

    simdi = time.time()
    yazilar.append((f"{datetime.now():%d.%m.%Y %H:%M:%S}  ·  Kayıtlı yüz: {len(durum.kisiler)}  ·  "
                    f"{fps:.0f} FPS", (10, 10), ekran.BEYAZ, 16))
    y = kare.shape[0] - 34
    for t, metin, renk in reversed(durum.mesajlar):
        if simdi - t <= config.MESAJ_SURESI_SN:
            yazilar.append((metin, (10, y), renk, 18))
            y -= 32
    yazilar.append(("Çıkış: Q / ESC", (kare.shape[1] - 130, 10), ekran.BEYAZ, 14))
    return ekran.yazilar_ciz(kare, yazilar)


def calistir() -> int:
    db.veritabanini_olustur()
    durum = TanimaDurumu()
    durum.vektorleri_yukle()
    if not durum.kisiler:
        print("UYARI: Henüz yüzü kayıtlı kimse yok. Önce: python -m src.kayit")

    print("Yüz modeli ve kamera açılıyor...")
    kamera = kmr.kamera_ac()
    if kamera is None:
        return 1
    engel = kmr.EngelTakibi()

    son_yukleme = time.time()
    sonuclar, isle, fps, t_onceki = [], True, 0.0, time.time()
    print("Yoklama başladı. Çıkmak için pencere seçiliyken Q veya ESC.")
    try:
        while True:
            ok, kare = kamera.read()
            if not ok:
                print("HATA: Kameradan görüntü alınamadı.")
                return 1
            kare = cv2.flip(kare, 1)  # kayıt modülüyle aynı (ayna) görüntü

            if time.time() - son_yukleme > config.VEKTOR_YENILEME_SN:
                durum.vektorleri_yukle()          # yeni kaydedilen kişiler programı kapatmadan tanınsın
                son_yukleme = time.time()

            if isle:                              # hız için her iki kareden biri işlenir
                sonuclar = yuzleri_degerlendir(durum, yi.yuzleri_bul(kare))
            isle = not isle

            simdi = time.time()
            fps = 0.9 * fps + 0.1 / max(simdi - t_onceki, 1e-3)
            t_onceki = simdi

            goruntu = ciz(kare, sonuclar, durum, fps)
            if engel.guncelle(kare):
                goruntu = ekran.yazilar_ciz(goruntu, [(kmr.ENGEL_MESAJI, (10, 50), ekran.SARI, 16)])
            cv2.imshow(PENCERE, goruntu)
            tus = cv2.waitKey(1) & 0xFF
            if tus in (27, ord("q"), ord("Q")):
                break
            if cv2.getWindowProperty(PENCERE, cv2.WND_PROP_VISIBLE) < 1:   # pencere X ile kapatıldı
                break
    except KeyboardInterrupt:
        pass
    finally:
        kamera.release()
        cv2.destroyAllWindows()
    print("Yoklama durduruldu.")
    return 0


if __name__ == "__main__":
    sys.exit(calistir())
