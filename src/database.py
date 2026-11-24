"""Veri tabanı katmanı (5. hafta: Veri Tabanı Uygulaması ve CRUD).

Projenin geri kalanı (kayıt modülü, tanıma döngüsü, web paneli) veri tabanına
yalnızca bu dosyadaki fonksiyonlar üzerinden erişir.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import numpy as np

from src import config

VEKTOR_DTYPE = np.float64


# ---------------------------------------------------------------- bağlantı
def baglanti_ac(db_yolu: Path | str | None = None) -> sqlite3.Connection:
    """Yeni bir bağlantı açar. Yabancı anahtarlar her bağlantıda açılmalıdır."""
    db_yolu = Path(db_yolu or config.DB_YOLU)
    db_yolu.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_yolu)
    conn.row_factory = sqlite3.Row          # Satırlara isimle erişim: satir["Ad"]
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def baglanti(db_yolu=None):
    """with bloğu bitince işlemi kaydeder (hata olursa geri alır) ve bağlantıyı kapatır."""
    conn = baglanti_ac(db_yolu)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def veritabanini_olustur(db_yolu=None) -> None:
    """Tablolar yoksa schema.sql dosyasından oluşturur."""
    sema = config.SEMA_DOSYASI.read_text(encoding="utf-8")
    with baglanti(db_yolu) as conn:
        conn.executescript(sema)


# ---------------------------------------------------------------- KULLANICI
def _rol_kontrol(rol: str) -> None:
    if rol not in config.ROLLER:
        raise ValueError(f"Geçersiz rol: {rol!r}. Geçerli roller: {', '.join(config.ROLLER)}")


def kullanici_ekle(ad: str, soyad: str, rol: str, db_yolu=None) -> int:
    """Yeni kullanıcı ekler ve oluşan Kullanici_ID'yi döndürür."""
    ad, soyad = ad.strip(), soyad.strip()
    if not ad or not soyad:
        raise ValueError("Ad ve soyad boş olamaz.")
    _rol_kontrol(rol)
    with baglanti(db_yolu) as conn:
        cur = conn.execute(
            "INSERT INTO KULLANICI (Ad, Soyad, Rol) VALUES (?, ?, ?)", (ad, soyad, rol)
        )
        return cur.lastrowid


def kullanici_getir(kullanici_id: int, db_yolu=None) -> dict | None:
    with baglanti(db_yolu) as conn:
        satir = conn.execute(
            "SELECT * FROM KULLANICI WHERE Kullanici_ID = ?", (kullanici_id,)
        ).fetchone()
        return dict(satir) if satir else None


def kullanicilari_listele(db_yolu=None) -> list[dict]:
    """Tüm kullanıcılar; yüz vektörü kayıtlı mı bilgisiyle birlikte."""
    with baglanti(db_yolu) as conn:
        satirlar = conn.execute(
            """SELECT K.*, (V.Vektor_ID IS NOT NULL) AS Yuz_Kayitli
               FROM KULLANICI K LEFT JOIN YUZ_VEKTORU V ON V.Kullanici_ID = K.Kullanici_ID
               ORDER BY K.Soyad, K.Ad"""
        ).fetchall()
        return [dict(s) for s in satirlar]


def kullanici_guncelle(kullanici_id: int, ad=None, soyad=None, rol=None, db_yolu=None) -> bool:
    """Verilen alanları günceller. Kullanıcı bulunduysa True döner."""
    alanlar, degerler = [], []
    if ad is not None:
        alanlar.append("Ad = ?"); degerler.append(ad.strip())
    if soyad is not None:
        alanlar.append("Soyad = ?"); degerler.append(soyad.strip())
    if rol is not None:
        _rol_kontrol(rol); alanlar.append("Rol = ?"); degerler.append(rol)
    if not alanlar:
        return kullanici_getir(kullanici_id, db_yolu) is not None
    with baglanti(db_yolu) as conn:
        cur = conn.execute(
            f"UPDATE KULLANICI SET {', '.join(alanlar)} WHERE Kullanici_ID = ?",
            (*degerler, kullanici_id),
        )
        return cur.rowcount == 1


def kullanici_sil(kullanici_id: int, db_yolu=None) -> bool:
    """Kullanıcıyı siler; yüz vektörü ve yoklamaları CASCADE ile silinir."""
    with baglanti(db_yolu) as conn:
        cur = conn.execute("DELETE FROM KULLANICI WHERE Kullanici_ID = ?", (kullanici_id,))
        return cur.rowcount == 1


# ---------------------------------------------------------------- YUZ_VEKTORU
def _vektor_to_blob(vektor) -> bytes:
    dizi = np.asarray(vektor, dtype=VEKTOR_DTYPE).ravel()
    if dizi.size != config.VEKTOR_BOYUTU:
        raise ValueError(f"Yüz vektörü {config.VEKTOR_BOYUTU} boyutlu olmalı, gelen: {dizi.size}")
    return dizi.tobytes()


def _blob_to_vektor(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=VEKTOR_DTYPE).copy()


def yuz_vektoru_kaydet(kullanici_id: int, vektor, db_yolu=None) -> None:
    """Kullanıcının yüz vektörünü kaydeder; zaten varsa yenisiyle değiştirir."""
    blob = _vektor_to_blob(vektor)
    with baglanti(db_yolu) as conn:
        conn.execute(
            """INSERT INTO YUZ_VEKTORU (Vektor_Verisi, Kullanici_ID) VALUES (?, ?)
               ON CONFLICT(Kullanici_ID) DO UPDATE SET Vektor_Verisi = excluded.Vektor_Verisi""",
            (blob, kullanici_id),
        )


def kullanici_ve_yuz_ekle(ad: str, soyad: str, rol: str, vektor, db_yolu=None) -> int:
    """Kayıt modülü için: kullanıcıyı ve yüz vektörünü TEK işlemde ekler.
    Herhangi biri başarısız olursa hiçbiri kaydedilmez (yüzü olmayan yarım kayıt oluşmaz)."""
    ad, soyad = ad.strip(), soyad.strip()
    if not ad or not soyad:
        raise ValueError("Ad ve soyad boş olamaz.")
    _rol_kontrol(rol)
    blob = _vektor_to_blob(vektor)
    with baglanti(db_yolu) as conn:
        kid = conn.execute(
            "INSERT INTO KULLANICI (Ad, Soyad, Rol) VALUES (?, ?, ?)", (ad, soyad, rol)
        ).lastrowid
        conn.execute(
            "INSERT INTO YUZ_VEKTORU (Vektor_Verisi, Kullanici_ID) VALUES (?, ?)", (blob, kid)
        )
        return kid


def yuz_vektoru_getir(kullanici_id: int, db_yolu=None) -> np.ndarray | None:
    with baglanti(db_yolu) as conn:
        satir = conn.execute(
            "SELECT Vektor_Verisi FROM YUZ_VEKTORU WHERE Kullanici_ID = ?", (kullanici_id,)
        ).fetchone()
        return _blob_to_vektor(satir[0]) if satir else None


def tum_yuz_vektorleri(db_yolu=None) -> tuple[list[dict], np.ndarray]:
    """Tanıma döngüsü için: (kişi bilgileri listesi, N x 128 vektör matrisi)."""
    with baglanti(db_yolu) as conn:
        satirlar = conn.execute(
            """SELECT K.Kullanici_ID, K.Ad, K.Soyad, K.Rol, V.Vektor_Verisi
               FROM YUZ_VEKTORU V JOIN KULLANICI K ON K.Kullanici_ID = V.Kullanici_ID
               ORDER BY K.Kullanici_ID"""
        ).fetchall()
    # Veri tabanından gelen veri de "dış girdi" gibi doğrulanır: bozuk tek bir kayıt
    # (yanlış boyut, NaN vb.) tüm tanıma döngüsünü çökertmesin, yalnızca o kayıt atlansın.
    kisiler, vektorler = [], []
    beklenen = config.VEKTOR_BOYUTU * np.dtype(VEKTOR_DTYPE).itemsize
    for s in satirlar:
        blob = s["Vektor_Verisi"]
        v = _blob_to_vektor(blob) if isinstance(blob, bytes) and len(blob) == beklenen else None
        if v is None or not np.isfinite(v).all():
            print(f"UYARI: Kullanıcı {s['Kullanici_ID']} için yüz vektörü bozuk, atlandı. "
                  f"Yeniden kayıt: python -m src.kayit --id {s['Kullanici_ID']}")
            continue
        kisiler.append({k: s[k] for k in ("Kullanici_ID", "Ad", "Soyad", "Rol")})
        vektorler.append(v)
    if not vektorler:
        return kisiler, np.empty((0, config.VEKTOR_BOYUTU), dtype=VEKTOR_DTYPE)
    return kisiler, np.vstack(vektorler)


def yuz_vektoru_sil(kullanici_id: int, db_yolu=None) -> bool:
    with baglanti(db_yolu) as conn:
        cur = conn.execute("DELETE FROM YUZ_VEKTORU WHERE Kullanici_ID = ?", (kullanici_id,))
        return cur.rowcount == 1


# ---------------------------------------------------------------- YOKLAMA
def son_yoklama_zamani(kullanici_id: int, db_yolu=None) -> datetime | None:
    with baglanti(db_yolu) as conn:
        satir = conn.execute(
            """SELECT Tarih, Saat FROM YOKLAMA WHERE Kullanici_ID = ?
               ORDER BY Tarih DESC, Saat DESC, Log_ID DESC LIMIT 1""",
            (kullanici_id,),
        ).fetchone()
    if not satir:
        return None
    return datetime.strptime(f"{satir['Tarih']} {satir['Saat']}", "%Y-%m-%d %H:%M")


def yoklama_ekle(kullanici_id: int, zaman: datetime | None = None, db_yolu=None) -> int | None:
    """Bekleme süresi dolduysa yoklama kaydı ekler ve Log_ID döndürür.
    Son kayıttan bu yana BEKLEME_SURESI_DK dolmadıysa kayıt atmaz, None döndürür."""
    zaman = (zaman or datetime.now()).replace(second=0, microsecond=0)
    son = son_yoklama_zamani(kullanici_id, db_yolu)
    if son is not None and (zaman - son).total_seconds() < config.BEKLEME_SURESI_DK * 60:
        return None
    with baglanti(db_yolu) as conn:
        cur = conn.execute(
            "INSERT INTO YOKLAMA (Tarih, Saat, Kullanici_ID) VALUES (?, ?, ?)",
            (zaman.strftime("%Y-%m-%d"), zaman.strftime("%H:%M"), kullanici_id),
        )
        return cur.lastrowid


def yoklamalari_listele(tarih: str | None = None, kullanici_id: int | None = None,
                        db_yolu=None) -> list[dict]:
    """Yoklama kayıtlarını kişi bilgileriyle listeler. Tarih: 'YYYY-MM-DD'."""
    sql = """SELECT Y.Log_ID, Y.Tarih, Y.Saat, K.Kullanici_ID, K.Ad, K.Soyad, K.Rol
             FROM YOKLAMA Y JOIN KULLANICI K ON K.Kullanici_ID = Y.Kullanici_ID"""
    kosullar, degerler = [], []
    if tarih:
        kosullar.append("Y.Tarih = ?"); degerler.append(tarih)
    if kullanici_id is not None:
        kosullar.append("Y.Kullanici_ID = ?"); degerler.append(kullanici_id)
    if kosullar:
        sql += " WHERE " + " AND ".join(kosullar)
    sql += " ORDER BY Y.Tarih DESC, Y.Saat DESC, Y.Log_ID DESC"
    with baglanti(db_yolu) as conn:
        return [dict(s) for s in conn.execute(sql, degerler).fetchall()]


def yoklama_sil(log_id: int, db_yolu=None) -> bool:
    with baglanti(db_yolu) as conn:
        cur = conn.execute("DELETE FROM YOKLAMA WHERE Log_ID = ?", (log_id,))
        return cur.rowcount == 1


if __name__ == "__main__":
    veritabanini_olustur()
    print(f"Veri tabanı hazır: {config.DB_YOLU}")
