# Akıllı Yoklama Sistemi (Yüz Tanıma Tabanlı)

Mesleki Çözümleme dersi projesi – İsmail Furkan Alp (254309042)

**Projenin kısa özeti:** Yüz Tanıma Tabanlı Otomatik Yoklama Sistemi, kameralar aracılığıyla kişilerin
yüzlerini tespit edip veri tabanındaki referans verilerle eşleştirerek giriş-çıkış saatlerini otomatik
olarak kaydeden web tabanlı bir otomasyon projesidir.

## Durum (7. hafta sonu)
- [x] Veri tabanı ve CRUD katmanı (SQLite)
- [x] Yüz kayıt modülü (kameradan 5 örnek, ortalama 128 boyutlu vektör)
- [x] Canlı tanıma ve otomatik yoklama (3 kare onayı, 10 dk bekleme süresi, "Bilinmeyen Kişi" uyarısı)
- [x] 27 birim testi
- [ ] Web yönetim paneli ve REST API (Flask) – 8.–9. hafta

KVKK gereği fotoğraf saklanmaz; veri tabanında yalnızca yüz vektörleri tutulur.

## Klasör yapısı
```
database/schema.sql   Veri tabanı tabloları (KULLANICI, YUZ_VEKTORU, YOKLAMA)
src/config.py         Ayarlar (eşik değeri, bekleme süresi, kamera no)
src/database.py       Veri tabanı CRUD fonksiyonları
src/yuz_isleme.py     Yüz tespiti, 128 boyutlu vektör, eşleştirme
src/kayit.py          Yeni kullanıcı + yüz kaydı
src/tanima.py         Canlı tanıma ve otomatik yoklama döngüsü
src/kamera.py         Kamera açma, "kamera kapalı" algılama
src/ekran.py          Kamera penceresine Türkçe yazı çizimi
tests/                Birim testleri (python -m unittest -v)
data/                 yoklama.db burada oluşur (Git'e eklenmez)
*.pdf                 Haftalık ilerleme raporları
```

## Kurulum ve kullanım (Windows)
Proje klasörünün yolunda Türkçe karakter olmamalıdır (ör. `C:\AkilliYoklama`); dlib bu yolları açamaz.

1. `kurulum.bat` – sanal ortamı ve paketleri kurar, ortamı kontrol eder
2. `kayit.bat` – yeni kişi kaydeder
3. `yoklama.bat` – kamerayı açar, tanınan kişilerin yoklamasını alır (Q/ESC: çıkış)
4. `testler.bat` – birim testlerini çalıştırır

Terminalden: `python -m src.kayit --liste` (kayıtlıları listeler), `python -m src.kayit --id 3` (3 numaralı kişinin yüzünü yeniler)

## Kullanılan teknolojiler
Python 3.14 · OpenCV · face_recognition (dlib) · NumPy · SQLite · Pillow · Flask (planlandı)
