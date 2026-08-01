# -*- coding: utf-8 -*-
"""
GEMINI TTS DENEMESI
Gemini'nin ses uretme modelinin ucretsiz kotada calisip calismadigini test eder.
Calisirsa edge-tts'e alternatif olarak birden fazla ses karakteri kullanabiliriz.

Kullanim:
    python gemini_ses_dene.py
"""
import base64
import struct
import sys
import wave
from pathlib import Path

import config

try:
    import requests
except ImportError:
    print("HATA: requests kurulu degil.")
    sys.exit(1)

# Gemini'nin sunduğu ses karakterleri (bir kismi)
SESLER = [
    ("Kore", "kararli, net"),
    ("Puck", "neseli, canli"),
    ("Charon", "derin, bilgilendirici"),
    ("Aoede", "havadar, yumusak"),
    ("Fenrir", "heyecanli"),
    ("Leda", "genc, parlak"),
]

ORNEK = (
    "Ortaçağda insanlar geceyi ikiye bölerek uyurdu. "
    "Birinci uykudan sonra saatlerce uyanık kalırlardı."
)

MODELLER = [
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
    "gemini-3.1-flash-tts-preview",
]


def cizgi(b=""):
    print("\n" + "=" * 64)
    if b:
        print(f"  {b}\n" + "=" * 64)


def pcm_to_wav(pcm: bytes, yol: Path, hiz=24000, kanal=1, genislik=2) -> None:
    """Gemini ham PCM donduruyor; WAV basligi ekliyoruz."""
    with wave.open(str(yol), "wb") as f:
        f.setnchannels(kanal)
        f.setsampwidth(genislik)
        f.setframerate(hiz)
        f.writeframes(pcm)


def dene(model: str, ses: str, hedef: Path) -> tuple:
    """Tek bir ses uretmeyi dener. (basarili, mesaj) dondurur."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    govde = {
        "contents": [{"parts": [{"text": ORNEK}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": ses}
                }
            },
        },
    }
    basliklar = {
        "x-goog-api-key": config.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    import time
    c = None
    for deneme in range(1, 4):
        try:
            c = requests.post(url, json=govde, headers=basliklar, timeout=120)
            break
        except Exception as e:                          # noqa: BLE001
            if deneme == 3:
                kisa = str(e).split("(Caused by")[0][:70]
                return False, f"baglanti kurulamadi: {kisa}"
            time.sleep(3 * deneme)

    if c is None:
        return False, "baglanti kurulamadi"

    if c.status_code == 429:
        metin = c.text
        if "limit: 0" in metin:
            return False, "ucretsiz kotasi YOK"
        return False, "anlik hiz limiti (model kullanilabilir olabilir)"

    if c.status_code != 200:
        return False, f"HTTP {c.status_code}: {c.text[:150]}"

    try:
        parcalar = c.json()["candidates"][0]["content"]["parts"]
        veri = None
        for p in parcalar:
            if "inlineData" in p:
                veri = p["inlineData"]["data"]
                break
        if not veri:
            return False, "cevapta ses verisi yok"

        pcm = base64.b64decode(veri)
        pcm_to_wav(pcm, hedef)
        kb = hedef.stat().st_size // 1024
        return True, f"{kb} KB"
    except Exception as e:                              # noqa: BLE001
        return False, f"cevap islenemedi: {e}"


def main() -> int:

    if not config.GEMINI_API_KEY:
        print("HATA: .env dosyasinda GEMINI_API_KEY yok.")
        return 1

    klasor = config.ASSETS_DIR / "gemini_ses_ornekleri"
    klasor.mkdir(parents=True, exist_ok=True)

    cizgi("1) HANGI TTS MODELI CALISIYOR?")

    calisan_model = None
    for model in MODELLER:
        print(f"  {model:36} ", end="", flush=True)
        ok, mesaj = dene(model, "Kore", klasor / "_test.wav")
        print("✓ CALISIYOR" if ok else f"✗ {mesaj}")
        if ok and not calisan_model:
            calisan_model = model

    if not calisan_model:
        cizgi("SONUC")
        print("✗ Hicbir TTS modeli ucretsiz kotada calismiyor.")
        print("  edge-tts (Emel / Ahmet) ile devam etmek gerekiyor.")
        (klasor / "_test.wav").unlink(missing_ok=True)
        return 1

    (klasor / "_test.wav").unlink(missing_ok=True)

    cizgi(f"2) SES KARAKTERLERI  ({calisan_model})")

    basarili = []
    for ses, aciklama in SESLER:
        hedef = klasor / f"{ses}.wav"
        print(f"  {ses:10} ({aciklama:22}) ", end="", flush=True)
        if hedef.exists() and hedef.stat().st_size > 10240:
            print("✓ zaten var")
            basarili.append(ses)
            continue
        ok, mesaj = dene(calisan_model, ses, hedef)
        print(f"✓ {mesaj}" if ok else f"✗ {mesaj}")
        if ok:
            basarili.append(ses)

    cizgi("SONUC")
    if basarili:
        print(f"✓ {len(basarili)} ses karakteri calisiyor: {', '.join(basarili)}")
        print(f"\nOrnekler burada: {klasor}")
        print("\nDinle, begendigin olursa bana soyle; kodu buna gecirelim.")
        print("Turkce telaffuza ve dogalliga dikkat et -- bu sesler cok dilli,")
        print("Turkce'de aksan veya vurgu sorunu olabilir.")
    else:
        print("✗ Ses uretilemedi. edge-tts ile devam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
