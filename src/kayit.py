"""Yeni kullanıcı ve yüz kaydı (6. hafta: Backend I).

Kullanım (proje klasöründe, sanal ortam açıkken):
    python -m src.kayit              -> yeni kişi ekler
    python -m src.kayit --id 3       -> 3 numaralı kişinin yüzünü yeniden kaydeder
    python -m src.kayit --liste      -> kayıtlı kişileri listeler
"""
from __future__ import annotations

import argparse
import sys

import cv2

from src import config, database as db, ekran, kamera as kmr, yuz_isleme as yi

PENCERE = "Yuz Kaydi"
MIN_YUZ_ALANI = 90 * 90      # Bundan küçük yüzler (uzakta duran kişi) örnek olarak alınmaz


def _secim_sor(soru: str, secenekler: tuple[str, ...]) -> str:
    for i, s in enumerate(secenekler, 1):
        print(f"  {i}) {s}")
    while True:
        cevap = input(f"{soru} [1-{len(secenekler)}]: ").strip()
        if cevap.isdigit() and 1 <= int(cevap) <= len(secenekler):
            return secenekler[int(cevap) - 1]
        print("  Geçersiz seçim.")


def _bos_olmayan(soru: str) -> str:
    while True:
        deger = input(soru).strip()
        if deger:
            return deger
        print("  Boş bırakılamaz.")


def ornek_topla(kisi_adi: str, adet: int = config.KAYIT_ORNEK_SAYISI) -> list | None:
    """Kameradan 'adet' kadar yüz vektörü toplar. İptal edilirse None döner."""
    kamera = kmr.kamera_ac()
    if kamera is None:
        return None
    engel = kmr.EngelTakibi()
    ornekler = []
    durum, durum_renk = "", ekran.BEYAZ
    print("\nKamera penceresi açıldı. BOŞLUK: örnek al  |  ESC: iptal")
    try:
        while len(ornekler) < adet:
            ok, kare = kamera.read()
            if not ok:
                print("HATA: Kameradan görüntü alınamadı.")
                return None
            kare = cv2.flip(kare, 1)               # ayna görüntüsü: kullanıcı için daha doğal
            yuzler = yi.yuzleri_bul(kare, vektor_cikar=False)

            uygun = len(yuzler) == 1 and yuzler[0].alan >= MIN_YUZ_ALANI
            engelli = engel.guncelle(kare)
            if not yuzler and engelli:
                ipucu = kmr.ENGEL_MESAJI
            elif not yuzler:
                ipucu = "Yüz bulunamadı - kameraya bakın"
            elif len(yuzler) > 1:
                ipucu = "Karede yalnızca bir kişi olmalı"
            elif not uygun:
                ipucu = "Kameraya biraz yaklaşın"
            else:
                ipucu = "Hazır - BOŞLUK tuşuna basın"
            for y in yuzler:
                ekran.kutu_ciz(kare, y, ekran.YESIL if uygun else ekran.SARI)

            yazilar = [
                (f"Kayıt: {kisi_adi}", (10, 10), ekran.BEYAZ, 20),
                (f"Örnek {len(ornekler)}/{adet}  ·  {ipucu}", (10, 42), ekran.YESIL if uygun else ekran.SARI, 18),
                ("Her örnekte başınızı hafifçe çevirin  ·  ESC: iptal", (10, kare.shape[0] - 34), ekran.BEYAZ, 16),
            ]
            if durum:
                yazilar.append((durum, (10, 72), durum_renk, 18))
            cv2.imshow(PENCERE, ekran.yazilar_ciz(kare, yazilar))

            tus = cv2.waitKey(1) & 0xFF
            if tus == 27:                           # ESC
                return None
            if tus == 32:                           # BOŞLUK
                if not uygun:
                    durum, durum_renk = "Örnek alınamadı: " + ipucu, ekran.KIRMIZI
                    continue
                yuz = yi.yuzleri_bul(kare)          # bu kez vektörüyle birlikte
                if len(yuz) == 1 and yuz[0].vektor is not None:
                    ornekler.append(yuz[0].vektor)
                    durum, durum_renk = f"Örnek {len(ornekler)} alındı", ekran.YESIL
                else:
                    durum, durum_renk = "Yüz kayboldu, tekrar deneyin", ekran.KIRMIZI
        return ornekler
    finally:
        kamera.release()
        cv2.destroyAllWindows()


def benzer_kayit_var_mi(vektor, haric_id: int | None = None) -> dict | None:
    """Bu yüz başka bir isimle zaten kayıtlı mı? (aynı kişinin iki kez kaydedilmesini önler)"""
    kisiler, matris = db.tum_yuz_vektorleri()
    i, mesafe = yi.en_yakin_eslesme(vektor, matris)
    if i is not None and kisiler[i]["Kullanici_ID"] != haric_id:
        return {**kisiler[i], "mesafe": mesafe}
    return None


def _onay(soru: str) -> bool:
    return input(f"{soru} (e/h): ").strip().lower() in ("e", "evet", "y")


def yeni_kayit() -> None:
    print("\n=== YENİ KULLANICI KAYDI ===")
    ad = _bos_olmayan("Ad     : ")
    soyad = _bos_olmayan("Soyad  : ")
    print("Rol:")
    rol = _secim_sor("Seçiminiz", config.ROLLER)

    print("\nYüz modeli yükleniyor...")
    ornekler = ornek_topla(f"{ad} {soyad}")
    if not ornekler:
        print("Kayıt iptal edildi, hiçbir şey kaydedilmedi.")
        return
    vektor = yi.ortalama_vektor(ornekler)

    benzer = benzer_kayit_var_mi(vektor)
    if benzer:
        print(f"\nUYARI: Bu yüz zaten '{benzer['Ad']} {benzer['Soyad']}' (ID {benzer['Kullanici_ID']}) "
              f"olarak kayıtlı görünüyor (mesafe {benzer['mesafe']:.2f}).")
        if not _onay("Yine de yeni kişi olarak kaydedilsin mi?"):
            print("Kayıt iptal edildi.")
            return

    kid = db.kullanici_ve_yuz_ekle(ad, soyad, rol, vektor)
    print(f"\nKaydedildi: {ad} {soyad} ({rol}) - Kullanıcı ID: {kid}")


def yuz_yenile(kullanici_id: int) -> None:
    kisi = db.kullanici_getir(kullanici_id)
    if not kisi:
        print(f"HATA: {kullanici_id} numaralı kullanıcı bulunamadı.")
        return
    ad = f"{kisi['Ad']} {kisi['Soyad']}"
    print(f"\n=== YÜZ GÜNCELLEME: {ad} ===\nYüz modeli yükleniyor...")
    ornekler = ornek_topla(ad)
    if not ornekler:
        print("İptal edildi, eski yüz kaydı korundu.")
        return
    vektor = yi.ortalama_vektor(ornekler)
    benzer = benzer_kayit_var_mi(vektor, haric_id=kullanici_id)
    if benzer and not _onay(f"UYARI: Bu yüz '{benzer['Ad']} {benzer['Soyad']}' kaydına benziyor. Devam edilsin mi?"):
        print("İptal edildi.")
        return
    db.yuz_vektoru_kaydet(kullanici_id, vektor)
    print(f"Yüz kaydı güncellendi: {ad}")


def listele() -> None:
    kisiler = db.kullanicilari_listele()
    if not kisiler:
        print("Kayıtlı kullanıcı yok.")
        return
    print(f"\n{'ID':>4}  {'Ad Soyad':<30} {'Rol':<10} Yüz")
    for k in kisiler:
        print(f"{k['Kullanici_ID']:>4}  {k['Ad'] + ' ' + k['Soyad']:<30} {k['Rol']:<10} "
              f"{'var' if k['Yuz_Kayitli'] else 'YOK'}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Akıllı Yoklama - kullanıcı/yüz kaydı")
    p.add_argument("--id", type=int, help="Var olan kullanıcının yüzünü yeniden kaydet")
    p.add_argument("--liste", action="store_true", help="Kayıtlı kullanıcıları listele")
    args = p.parse_args(argv)

    db.veritabanini_olustur()
    try:
        if args.liste:
            listele()
        elif args.id is not None:
            yuz_yenile(args.id)
        else:
            yeni_kayit()
    except KeyboardInterrupt:
        print("\nİptal edildi.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
