@echo off
chcp 65001 >nul
cd /d "%~dp0"
set LOG=kurulum_log.txt
echo ==== Kurulum %date% %time% ==== > %LOG%

rem --- Python bul (once py baslaticisi, yoksa python)
set PY=
where py >nul 2>&1 && set PY=py -3
if "%PY%"=="" where python >nul 2>&1 && set PY=python
if "%PY%"=="" (
  echo [HATA] Python bulunamadi. >> %LOG%
  echo Python bulunamadi. python.org'dan kurup "Add python.exe to PATH" kutusunu isaretleyin.
  pause & exit /b 1
)
echo Kullanilan Python komutu: %PY% >> %LOG%
%PY% --version >> %LOG% 2>&1

rem --- Sanal ortam
if not exist .venv (
  echo [1/5] Sanal ortam olusturuluyor...
  %PY% -m venv .venv >> %LOG% 2>&1
)
call .venv\Scripts\activate.bat
if errorlevel 1 ( echo [HATA] Sanal ortam etkinlestirilemedi >> %LOG% & pause & exit /b 1 )

echo [2/5] pip guncelleniyor...
python -m pip install --upgrade pip >> %LOG% 2>&1

echo [3/5] Temel paketler kuruluyor (numpy, opencv, flask)...
pip install -r requirements.txt >> %LOG% 2>&1
if errorlevel 1 echo [HATA] requirements.txt kurulamadi >> %LOG%

echo [4/5] Yuz tanima kutuphanesi deneniyor (dlib)... birkac dakika surebilir
echo ---- dlib denemesi ---- >> %LOG%
pip install dlib-bin >> %LOG% 2>&1
if errorlevel 1 (
  echo [UYARI] dlib-bin kurulamadi >> %LOG%
) else (
  pip install face_recognition_models >> %LOG% 2>&1
  pip install face_recognition --no-deps >> %LOG% 2>&1
)

echo [5/5] Ortam kontrol ediliyor ve testler calistiriliyor...
echo ---- ortam_kontrol ---- >> %LOG%
python ortam_kontrol.py >> %LOG% 2>&1
echo ---- testler ---- >> %LOG%
python -m unittest -v >> %LOG% 2>&1

rem --- Git (kuruluysa)
where git >nul 2>&1
if errorlevel 1 (
  echo [BILGI] Git kurulu degil >> %LOG%
) else (
  if not exist .git git init >> %LOG% 2>&1
  git --version >> %LOG% 2>&1
)

echo ---- pip list ---- >> %LOG%
pip list >> %LOG% 2>&1
echo.
echo Bitti. Sonuclar: kurulum_log.txt ve ortam_raporu.txt
echo Claude'a "kurulum bitti" yazabilirsiniz.
pause
