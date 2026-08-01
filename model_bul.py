# -*- coding: utf-8 -*-
"""
CALISAN MODEL BULUCU
Anahtarinin erisebildigi modelleri tek tek deneyip hangisinin
ucretsiz calistigini bulur ve istersen .env dosyasina yazar.

Kullanim:
    python model_bul.py
"""
import re
import sys
import time
from pathlib import Path

import config

try:
    import requests
except ImportError:
    print("HATA: 'requests' kurulu degil -> python -m pip install -r requirements.txt")
    sys.exit(1)

# Metin uretmeyen / bizim isimize yaramayan modeller
ELE = (
    "image", "tts", "audio", "robotics", "computer-use", "deep-research",
    "lyria", "nano-banana", "embedding", "antigravity", "customtools",
    "omni", "veo", "imagen",
)

# Kalite/hiz tercihi: normal flash en dengelisi, lite daha zayif, pro en pahali
KADEME = ("flash-lite", "flash", "pro")


def _surum(ad: str) -> float:
    """'gemini-3.5-flash' -> 3.5. Surum yoksa (…-latest) orta deger verilir."""
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", ad)
    return float(m.group(1)) if m else 3.0


def _kademe(ad: str) -> int:
    if "flash-lite" in ad:
        return 1
    if "flash" in ad:
        return 0        # tercihimiz
    if "pro" in ad:
        return 2
    return 3


def puan(ad: str) -> tuple:
    """Kucuk puan = once denenir. Once yeni surum, sonra flash kademesi."""
    onizleme = 1 if "preview" in ad else 0
    return (onizleme, -_surum(ad), _kademe(ad), ad)


def cizgi(b=""):
    print("\n" + "=" * 64)
    if b:
        print(f"  {b}\n" + "=" * 64)


def main() -> int:
    # ------------------------------------------------------------ model listesi
    anahtar = config.GEMINI_API_KEY
    if not anahtar:
        print("HATA: .env dosyasinda GEMINI_API_KEY yok.")
        return 1

    basliklar = {"x-goog-api-key": anahtar, "Content-Type": "application/json"}

    cizgi("MODELLER ALINIYOR")
    r = requests.get(config.GEMINI_MODEL_LISTESI_URL, headers=basliklar, timeout=60)
    if r.status_code != 200:
        print(f"Model listesi alinamadi (HTTP {r.status_code}):\n{r.text[:500]}")
        return 1

    hepsi = [
        m["name"].replace("models/", "")
        for m in r.json().get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ]

    adaylar = [a for a in hepsi if not any(k in a for k in ELE)]
    adaylar = sorted(set(adaylar), key=puan)[:14]

    print(f"{len(hepsi)} model bulundu, bunlardan {len(adaylar)} tanesi denenecek.")

    # ------------------------------------------------------------ test
    cizgi("TEST BASLIYOR (her model arasi 2 sn bekleniyor)")

    govde = {
        "contents": [{"role": "user", "parts": [{"text": "Sadece 'merhaba' yaz."}]}],
        "generationConfig": {"maxOutputTokens": 20},
    }

    calisanlar, kotasizlar, digerleri = [], [], []

    for i, model in enumerate(adaylar, 1):
        url = config.GEMINI_URL.format(model=model)
        print(f"  [{i:2}/{len(adaylar)}] {model:<38}", end=" ", flush=True)
        try:
            c = requests.post(url, json=govde, headers=basliklar, timeout=60)
        except Exception as e:                          # noqa: BLE001
            print(f"BAGLANTI HATASI ({e})")
            digerleri.append((model, str(e)[:60]))
            time.sleep(2)
            continue

        if c.status_code == 200:
            print("✓ CALISIYOR")
            calisanlar.append(model)
        elif c.status_code == 429:
            mesaj = c.text
            if "limit: 0" in mesaj:
                print("✗ ucretsiz kotasi yok")
                kotasizlar.append(model)
            else:
                # Dakikalik limit -- model aslinda kullanilabilir
                print("~ anlik limit (model kullanilabilir)")
                calisanlar.append(model)
        else:
            print(f"✗ HTTP {c.status_code}")
            digerleri.append((model, f"HTTP {c.status_code}"))

        time.sleep(2)

    # ------------------------------------------------------------ sonuc
    cizgi("SONUC")

    if not calisanlar:
        print("✗ Ucretsiz calisan model bulunamadi.\n")
        print("Bu, anahtarinin bagli oldugu projede ucretsiz katmanin")
        print("kapali oldugu anlamina gelir. Yapabileceklerin:")
        print("  1) https://aistudio.google.com/apikey adresinden")
        print("     YENI BIR PROJEDE yeni bir anahtar olustur")
        print("     ('Create API key in new project' secenegi)")
        print("  2) Eski Google Cloud projelerinden birini secmediginden emin ol")
        print("\nDenenmis ve kotasi sifir olanlar:")
        for m in kotasizlar:
            print(f"  - {m}")
        return 1

    print("✓ Kullanilabilir modeller (en ustteki onerilir):\n")
    for m in calisanlar:
        print(f"    {m}")

    secim = calisanlar[0]
    print(f"\nOnerilen: {secim}")

    # ------------------------------------------------------------ .env guncelle
    env = Path(".env")
    if not env.exists():
        print("\n.env dosyasi bulunamadi. Su satiri kendin ekle:")
        print(f"    GEMINI_MODEL={secim}")
        return 0

    cevap = input(f"\n.env dosyasindaki modeli '{secim}' yapayim mi? (e/h): ").strip().lower()
    if cevap not in ("e", "evet", "y", "yes"):
        print(f"Degisiklik yapilmadi. Elle yazmak istersen: GEMINI_MODEL={secim}")
        return 0

    satirlar = env.read_text(encoding="utf-8-sig").splitlines()
    yeni, bulundu = [], False
    for s in satirlar:
        if s.strip().startswith("GEMINI_MODEL"):
            yeni.append(f"GEMINI_MODEL={secim}")
            bulundu = True
        else:
            yeni.append(s)
    if not bulundu:
        yeni.append(f"GEMINI_MODEL={secim}")

    env.write_text("\n".join(yeni) + "\n", encoding="utf-8")
    print(f"\n✓ .env guncellendi: GEMINI_MODEL={secim}")
    print("\nSimdi sunu calistirabilirsin:")
    print("    python main.py --tip shorts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
