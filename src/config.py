"""Projenin tüm ayarları tek yerde."""
from pathlib import Path

# Klasörler
PROJE_KOKU = Path(__file__).resolve().parent.parent
VERI_KLASORU = PROJE_KOKU / "data"
SEMA_DOSYASI = PROJE_KOKU / "database" / "schema.sql"
DB_YOLU = VERI_KLASORU / "yoklama.db"

# Yoklama kuralları
BEKLEME_SURESI_DK = 10      # Aynı kişi için iki kayıt arasındaki en az süre (cooldown)
ROLLER = ("Öğrenci", "Hoca", "Personel")

# Kamera / yüz tanıma
KAMERA_INDEX = 0            # Dahili kamera genelde 0'dır
ESLESME_ESIGI = 0.5         # Öklid mesafesi eşiği. face_recognition varsayılanı 0.6; yanlış
                            # eşleşmeyi azaltmak için biraz daha katı. Küçük = daha katı.
VEKTOR_BOYUTU = 128
ISLEME_OLCEGI = 0.5         # Hız için kare bu oranda küçültülerek işlenir
KAYIT_ORNEK_SAYISI = 5      # Kayıtta alınacak yüz örneği sayısı (ortalaması saklanır)
VEKTOR_YENILEME_SN = 30     # Tanıma döngüsü kayıtlı yüzleri bu aralıkla yeniden okur
MESAJ_SURESI_SN = 3         # Ekrandaki "Yoklama alındı" mesajının kalma süresi
