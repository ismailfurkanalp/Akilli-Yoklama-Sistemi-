"""Kamera teşhisi: hangi kamera numarasında GERÇEK görüntü var?
Fotoğraf kaydetmez; yalnızca sayısal ölçümleri kamera_teshis.txt dosyasına yazar.
Çalıştırma: kamera_teshis.bat"""
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

RAPOR = Path(__file__).with_name("kamera_teshis.txt")
sat = []


def yaz(s=""):
    print(s)
    sat.append(str(s))


# 1) Windows'un gördüğü kamera aygıtları
yaz("=== Windows kamera aygitlari ===")
try:
    cikti = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-PnpDevice -Class Camera,Image -ErrorAction SilentlyContinue | "
         "Select-Object Status,FriendlyName | Format-Table -AutoSize | Out-String -Width 200"],
        capture_output=True, text=True, timeout=30)
    yaz(cikti.stdout.strip() or "(liste bos)")
except Exception as e:
    yaz(f"Aygit listesi alinamadi: {e}")

# 2) Windows gizlilik ayarları (kamera izni)
yaz("\n=== Kamera gizlilik ayarlari ===")
try:
    import winreg
    anahtar = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"
    for kok, ad in ((winreg.HKEY_LOCAL_MACHINE, "HKLM (cihaz geneli)"), (winreg.HKEY_CURRENT_USER, "HKCU (kullanici)")):
        for alt in ("", r"\NonPackaged"):
            try:
                with winreg.OpenKey(kok, anahtar + alt) as k:
                    deger, _ = winreg.QueryValueEx(k, "Value")
                    yaz(f"{ad}{' masaustu uygulamalari' if alt else ''}: {deger}")
            except FileNotFoundError:
                yaz(f"{ad}{' masaustu uygulamalari' if alt else ''}: (ayar yok)")
except Exception as e:
    yaz(f"Ayarlar okunamadi: {e}")


# 3) Her kamera numarası ve iki farklı Windows sürücü arayüzü için görüntü ölçümü
def olc(index, backend, ad):
    kam = cv2.VideoCapture(index, backend)
    if not kam.isOpened():
        return f"kamera {index} [{ad}]: ACILAMADI"
    try:
        kareler = []
        bas = time.time()
        while time.time() - bas < 3 and len(kareler) < 30:   # kameranın ısınması için ~3 sn
            ok, k = kam.read()
            if ok and k is not None:
                kareler.append(cv2.cvtColor(k, cv2.COLOR_BGR2GRAY).astype(np.float32))
        if not kareler:
            return f"kamera {index} [{ad}]: acildi ama goruntu YOK"
        son = kareler[-1]
        siyah = float((son < 20).mean() * 100)
        hareket = float(np.mean([np.abs(a - b).mean() for a, b in zip(kareler, kareler[1:])])) if len(kareler) > 1 else 0
        h, w = son.shape
        tahmin = ("SAHTE/KAPALI goruntu (siyah ve hareketsiz)" if siyah > 80 and hareket < 0.5
                  else "GERCEK goruntu gibi")
        return (f"kamera {index} [{ad}]: {w}x{h}, kare={len(kareler)}, siyah=%{siyah:.0f}, "
                f"parlaklik={son.mean():.0f}, kareler arasi degisim={hareket:.2f} -> {tahmin}")
    finally:
        kam.release()


yaz("\n=== Goruntu olcumleri (kameraya bakin, 3 sn surer) ===")
for i in range(4):
    for backend, ad in ((cv2.CAP_DSHOW, "DSHOW"), (cv2.CAP_MSMF, "MSMF")):
        try:
            yaz(olc(i, backend, ad))
        except Exception as e:
            yaz(f"kamera {i} [{ad}]: HATA {e}")

RAPOR.write_text("\n".join(sat), encoding="utf-8")
print(f"\nRapor yazildi: {RAPOR}")
