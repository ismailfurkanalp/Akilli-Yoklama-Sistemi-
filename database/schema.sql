-- Akıllı Yoklama Sistemi - Veri tabanı şeması (SQLite)
-- Not: PRAGMA foreign_keys = ON; her bağlantıda database.py tarafından açılır.

-- 1) KULLANICI: sisteme kayıtlı kişiler
CREATE TABLE IF NOT EXISTS KULLANICI (
    Kullanici_ID  INTEGER PRIMARY KEY AUTOINCREMENT,
    Ad            TEXT NOT NULL,
    Soyad         TEXT NOT NULL,
    Rol           TEXT NOT NULL
                  CHECK (Rol IN ('Öğrenci', 'Hoca', 'Personel'))
);

-- 2) YUZ_VEKTORU: kişi başına tek yüz vektörü (1:1)
CREATE TABLE IF NOT EXISTS YUZ_VEKTORU (
    Vektor_ID     INTEGER PRIMARY KEY AUTOINCREMENT,
    Vektor_Verisi BLOB NOT NULL,           -- 128 boyutlu dizi (float64)
    Kullanici_ID  INTEGER NOT NULL UNIQUE, -- UNIQUE => 1:1
    FOREIGN KEY (Kullanici_ID) REFERENCES KULLANICI(Kullanici_ID)
        ON DELETE CASCADE
);

-- 3) YOKLAMA: giriş-çıkış kayıtları (1:N)
CREATE TABLE IF NOT EXISTS YOKLAMA (
    Log_ID        INTEGER PRIMARY KEY AUTOINCREMENT,
    Tarih         TEXT NOT NULL,           -- 'YYYY-MM-DD'
    Saat          TEXT NOT NULL,           -- 'HH:MM'
    Kullanici_ID  INTEGER NOT NULL,
    FOREIGN KEY (Kullanici_ID) REFERENCES KULLANICI(Kullanici_ID)
        ON DELETE CASCADE
);

-- Mükerrer kayıt (10 dk) sorgusunu hızlandırmak için indeks
CREATE INDEX IF NOT EXISTS idx_yoklama_kisi_tarih ON YOKLAMA (Kullanici_ID, Tarih, Saat);
