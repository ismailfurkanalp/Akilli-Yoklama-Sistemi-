"""Geliştirme ortamını kontrol eder ve sonucu ortam_raporu.txt dosyasına yazar.
Çalıştırma: python ortam_kontrol.py"""
import platform
import sys
import traceback
from pathlib import Path

RAPOR = Path(__file__).with_name("ortam_raporu.txt")
satirlar = []


def yaz(s=""):
    print(s)
    satirlar.append(str(s))


def dene(baslik, fonk):
    try:
        sonuc = fonk()
        yaz(f"[TAMAM] {baslik}: {sonuc}")
        return True
    except Exception as e:
        yaz(f"[HATA ] {baslik}: {type(e).__name__}: {e}")
        satirlar.append(traceback.format_exc())
        return False


yaz(f"Python : {sys.version}")
yaz(f"Yol    : {sys.executable}")
yaz(f"Sistem : {platform.platform()}")
yaz()

dene("numpy", lambda: __import__("numpy").__version__)
dene("opencv", lambda: __import__("cv2").__version__)
dene("flask", lambda: __import__("importlib.metadata").metadata.version("flask"))


def fr_test():
    import face_recognition  # noqa: F401
    import dlib
    import numpy as np
    bos = np.zeros((100, 100, 3), dtype=np.uint8)
    face_recognition.face_locations(bos)  # modeller gerçekten yükleniyor mu
    return f"dlib {dlib.__version__}"


fr_var = dene("face_recognition + dlib", fr_test)


def sface_test():
    import cv2
    assert hasattr(cv2, "FaceDetectorYN") and hasattr(cv2, "FaceRecognizerSF")
    return "OpenCV YuNet + SFace sinifleri mevcut (yedek plan icin)"


dene("OpenCV yuz modulleri", sface_test)


def kamera_test():
    import cv2
    from src import config
    kam = cv2.VideoCapture(config.KAMERA_INDEX, cv2.CAP_DSHOW)
    try:
        ok, kare = kam.read()
        if not ok or kare is None:
            raise RuntimeError("Kamera acildi ama goruntu alinamadi (baska program kullaniyor olabilir)")
        from src.kamera import karanlik_mi
        if karanlik_mi(kare):
            raise RuntimeError("Goruntu siyah: kamera kapagi/tusu kapali olabilir")
        return f"goruntu {kare.shape[1]}x{kare.shape[0]}"
    finally:
        kam.release()


dene("Kamera", kamera_test)


def db_test():
    from src import database, config
    database.veritabanini_olustur()
    return f"{config.DB_YOLU}"


dene("Veri tabani", db_test)

yaz()
yaz("SONUC: " + ("face_recognition kullanilabilir." if fr_var
                 else "face_recognition YOK -> yedek plan (OpenCV SFace) gerekebilir."))
RAPOR.write_text("\n".join(satirlar), encoding="utf-8")
print(f"\nRapor yazildi: {RAPOR}")
