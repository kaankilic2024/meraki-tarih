# -*- coding: utf-8 -*-
"""
PEXELS GORSEL KAYNAGI
Pollinations ve Gemini ucretsiz AI gorsel uretimini kapattiktan sonra
gecilen kaynak. Gercek fotograf saglar, AI uretimi degil.

Onemli fark: AI'ya uzun betimleme veriyorduk ("a white airplane parked at
an airport under bright daylight, cinematic lighting..."). Pexels bir arama
motoru; uzun cumle yerine kisa anahtar kelime istiyor ("airplane airport").
Bu modul promptu arama terimine cevirir.
"""
import random
import re
from pathlib import Path
from typing import List, Optional, Tuple

import config
from utils import logger

ARAMA_URL = "https://api.pexels.com/v1/search"

# Prompt'ta gecen ama arama icin ise yaramayan kelimeler
GEREKSIZ = {
    # stil
    "digital", "illustration", "painting", "cinematic", "dramatic", "clean",
    "modern", "detailed", "realistic", "painterly", "style", "render",
    "artwork", "art", "rich", "vibrant", "warm", "soft", "gentle", "smooth",
    "high", "quality", "composition", "atmospheric", "depth", "field",
    "photorealistic", "storybook", "cartoon", "rounded", "friendly",
    "consistent", "character", "design", "palette", "tones", "colors",
    "color", "lighting", "light", "lit", "glow", "glowing", "bright",
    "dark", "dim", "shadow", "shadows", "highlights", "contrast",
    # cekim
    "shot", "wide", "medium", "close", "closeup", "macro", "overhead",
    "angle", "low", "eye", "level", "view", "perspective", "framing",
    "vertical", "horizontal", "centered", "focal", "subject", "frame",
    "background", "foreground", "blurred", "focus", "bokeh",
    # olumsuzlamalar
    "no", "not", "text", "letters", "watermark", "modern", "objects",
    # baglaclar
    "a", "an", "the", "of", "in", "on", "at", "with", "and", "or", "to",
    "from", "by", "for", "into", "over", "under", "near", "through",
    "its", "their", "his", "her", "this", "that", "these", "those",
    "is", "are", "was", "were", "be", "being", "been",
    "large", "small", "big", "little", "tiny", "huge", "giant",
    "single", "one", "two", "few", "some", "many", "several",
    # fiil ve edatlar
    "only", "off", "out", "up", "down", "filled", "rows", "row", "seen",
    "surrounded", "covered", "placed", "standing", "sitting", "lying",
    "showing", "depicting", "featuring", "including", "while", "very",
    "empty", "full", "old", "new", "young",
}


class PexelsHatasi(Exception):
    pass


def _arama_terimi(prompt: str, en_fazla: int = 4) -> str:
    """Uzun gorsel promptunu kisa arama terimine cevirir.

    Prompt'un basindaki kelimeler genelde asil konuyu anlatir; stil ve cekim
    bilgisi sonda olur. Bu yuzden bastan basliyoruz.
    """
    # Virgule kadar olan ilk bolum genelde asil konudur
    ilk_bolum = prompt.split(",")[0]
    kelimeler = re.findall(r"[a-zA-Z]{3,}", ilk_bolum.lower())

    secilen = [k for k in kelimeler if k not in GEREKSIZ]

    # Yetmezse promptun tamamina bak
    if len(secilen) < 2:
        tum = re.findall(r"[a-zA-Z]{3,}", prompt.lower())
        for k in tum:
            if k not in GEREKSIZ and k not in secilen:
                secilen.append(k)
            if len(secilen) >= en_fazla:
                break

    return " ".join(secilen[:en_fazla]) or "abstract background"


def _istek(terim: str, dikey: bool, sayfa: int = 1) -> List[dict]:
    import requests

    if not config.PEXELS_ANAHTARI:
        raise PexelsHatasi(
            "PEXELS_ANAHTARI tanimli degil. "
            "https://www.pexels.com/api/ adresinden ucretsiz alinir, "
            ".env dosyasina eklenir."
        )

    cevap = requests.get(
        ARAMA_URL,
        params={
            "query": terim,
            "per_page": config.PEXELS_SONUC_SAYISI,
            "page": sayfa,
            "orientation": "portrait" if dikey else "landscape",
            "size": "large",
        },
        headers={"Authorization": config.PEXELS_ANAHTARI},
        timeout=60,
    )

    if cevap.status_code == 429:
        raise PexelsHatasi("saatlik istek limiti doldu")
    if cevap.status_code != 200:
        raise PexelsHatasi(f"HTTP {cevap.status_code}: {cevap.text[:120]}")

    return cevap.json().get("photos", [])


def gorsel_url_bul(
    prompt: str, dikey: bool, kullanilanlar: Optional[set] = None
) -> Tuple[str, str, str]:
    """Prompta uygun bir fotograf bulur.

    Ayni videoda ayni fotografin tekrar etmemesi icin kullanilanlar kumesine
    bakar. Dondurur: (indirme_url, arama_terimi, fotografci_adi)
    """
    kullanilanlar = kullanilanlar or set()
    terim = _arama_terimi(prompt)

    denenecek_terimler = [terim]
    # Sonuc bulunamazsa terimi kisaltarak tekrar dene
    parcalar = terim.split()
    if len(parcalar) > 2:
        denenecek_terimler.append(" ".join(parcalar[:2]))
    if len(parcalar) > 1:
        denenecek_terimler.append(parcalar[0])

    for t in denenecek_terimler:
        try:
            sonuclar = _istek(t, dikey)
        except PexelsHatasi:
            raise
        except Exception as e:                          # noqa: BLE001
            raise PexelsHatasi(str(e)[:80])

        yeni = [f for f in sonuclar if f["id"] not in kullanilanlar]
        aday = yeni or sonuclar
        if aday:
            secim = random.choice(aday[:max(len(aday) // 2, 1)])
            kullanilanlar.add(secim["id"])
            boyut = "portrait" if dikey else "landscape"
            url = secim["src"].get(boyut) or secim["src"]["large2x"]
            return url, t, secim.get("photographer", "")

    raise PexelsHatasi(f"'{terim}' icin fotograf bulunamadi")


def kaynak_bilgisi(fotografcilar: List[str]) -> str:
    """Video aciklamasina eklenecek kaynak metni.

    Pexels atif zorunlu tutmuyor ama tavsiye ediyor; ayrica izleyiciye
    gorsellerin stok fotograf oldugunu bildirmek durustlik acisindan iyi.
    """
    benzersiz = sorted({f for f in fotografcilar if f})
    if not benzersiz:
        return ""
    liste = ", ".join(benzersiz[:8])
    if len(benzersiz) > 8:
        liste += " ve digerleri"
    return f"Görseller: Pexels — {liste}"
