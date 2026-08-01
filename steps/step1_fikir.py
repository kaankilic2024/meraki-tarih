# -*- coding: utf-8 -*-
"""
ADIM 1 - ICERIK FIKRI URETIMI
Kanal kimligine uygun, daha once kullanilmamis bir video fikri uretir.
"""
import json
import random
from datetime import datetime
from typing import Any, Dict, List

import config
from utils import ai, logger

SISTEM = """Sen bir YouTube tarih kanalinin icerik yoneticisisin.

KANAL: {kanal_adi}
TANIM: {kanal_tanimi}

GOREVIN: Kanala uygun, merak uyandiran TEK bir video fikri uretmek.

DOGRULUK KURALLARI (en onemlisi):
- SADECE genel kabul gormus, yaygin olarak bilinen tarihi bilgiler onerebilirsin.
- Emin olmadigin hicbir sey yazma. Supheliysen o fikri hic onerme.
- Uydurma olay, uydurma isim, uydurma istatistik KESINLIKLE YASAK.
- "Ilk", "en", "tek" gibi iddialarda cok dikkatli ol; tartismali olabilirler.
- Komplo teorisi, kanitlanmamis iddia, "gizlenen gercek" turu icerik URETME.

KACINILACAK KONULAR:
- Guncel siyaset ve son 50 yilin siyasi tartismalari
- Dini inanislarin dogrulugu/yanlisligi tartismasi
- Etnik veya milli gruplar arasi catisma konulari
- Soykirim, katliam, savas sucu gibi hassas konular
- Cinsel icerik, siddet detayi, iskence tasviri
- Yasayan veya yakin donemde yasamis kisiler hakkinda iddia

TERCIH EDILEN ALANLAR:
- Gecmiste gunluk hayat: yemek, uyku, temizlik, is, eglence, moda
- Nesnelerin ve adetlerin kokeni
- Unutulmus meslekler ve teknolojiler
- Sasirtici ama zararsiz tarihi ayrintilar
- Antik uygarliklarda yasam

Cevabini SADECE su JSON formatinda ver, baska hicbir sey yazma:
{{
  "konu": "Videonun konusu, kisa ve net (max 10 kelime)",
  "donem": "Hangi donem/yuzyil (ornek: Ortacag Avrupasi, 18. yuzyil Osmanli)",
  "ozet": "Videoda ne anlatilacak, 2-3 cumle",
  "mesaj": "Izleyicinin ogrenecegi ana bilgi, tek cumle",
  "neden_ilgi_ceker": "Neden merak uyandirir, tek cumle",
  "guven_seviyesi": "yuksek / orta -- bu bilginin ne kadar yaygin kabul gordugu",
  "anahtar_kelimeler": ["5", "adet", "turkce", "anahtar", "kelime"]
}}"""

ISTEK = """Video tipi: {tip_ad} ({en_boy}, yaklasik {sure} saniye)
Bu tip icin uygun konu turleri: {konu_tipleri}
Bu videoda su tur one cikacak: {secilen_tur}

Daha once kullanilmis konular (bunlara benzeme):
{gecmis}

Simdi yeni ve ozgun bir fikir uret."""

MOCK_FIKIR = {
    "konu": "Ortacagda insanlar neden iki kez uyurdu",
    "donem": "Ortacag Avrupasi",
    "ozet": "Elektrigin olmadigi donemde insanlar geceyi ikiye bolerek uyurdu. "
            "Ilk uykudan sonra birkac saat uyanik kalir, bu sureyi sohbet, dua "
            "veya ev isleriyle gecirirdi. Sanayi devrimiyle bu aliskanlik kayboldu.",
    "mesaj": "Kesintisiz sekiz saat uyku, sanildigindan cok daha yeni bir aliskanlik.",
    "neden_ilgi_ceker": "Herkes kendi uyku duzeniyle kiyaslar ve sasirir.",
    "guven_seviyesi": "yuksek",
    "anahtar_kelimeler": ["tarih", "ortacag", "uyku", "gunluk hayat", "merakli tarih"],
}


# ------------------------------------------------------------------ gecmis
def _gecmis_oku() -> List[Dict[str, Any]]:
    try:
        return json.loads(config.FIKIR_GECMISI.read_text(encoding="utf-8"))
    except Exception:
        return []


def _gecmis_yaz(kayit: Dict[str, Any]) -> None:
    gecmis = _gecmis_oku()
    gecmis.append(kayit)
    gecmis = gecmis[-200:]          # son 200 kayit yeter
    config.FIKIR_GECMISI.write_text(
        json.dumps(gecmis, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _gecmis_metni(adet: int = 30) -> str:
    gecmis = _gecmis_oku()[-adet:]
    if not gecmis:
        return "(henuz kullanilmis konu yok)"
    return "\n".join(f"- {k['konu']}" for k in gecmis)


# ------------------------------------------------------------------ ana fonksiyon
def fikir_uret(video_tipi: str) -> Dict[str, Any]:
    """video_tipi: 'shorts' veya 'uzun'"""
    if video_tipi not in config.VIDEO_TIPLERI:
        raise ValueError(f"Bilinmeyen video tipi: {video_tipi}")

    profil = config.VIDEO_TIPLERI[video_tipi]
    secilen_tur = random.choice(profil["konu_tipleri"])

    logger.bilgi(f"Fikir araniyor... (tip: {profil['ad']}, tur: {secilen_tur})")

    sistem = SISTEM.format(
        kanal_adi=config.KANAL_ADI, kanal_tanimi=config.KANAL_TANIMI
    )
    istek = ISTEK.format(
        tip_ad=profil["ad"],
        en_boy=profil["en_boy"],
        sure=profil["hedef_saniye"],
        konu_tipleri=", ".join(profil["konu_tipleri"]),
        secilen_tur=secilen_tur,
        gecmis=_gecmis_metni(),
    )

    fikir = ai.sor(sistem, istek, sicaklik=1.0, mock_cevap=MOCK_FIKIR)

    # Zorunlu alan kontrolu
    for alan in ("konu", "ozet", "mesaj", "anahtar_kelimeler"):
        if not fikir.get(alan):
            raise ai.AIHatasi(f"Fikirde '{alan}' alani eksik: {fikir}")

    fikir["video_tipi"] = video_tipi
    fikir["konu_turu"] = secilen_tur
    fikir["tarih"] = datetime.now().isoformat(timespec="seconds")

    _gecmis_yaz({"konu": fikir["konu"], "tarih": fikir["tarih"], "tip": video_tipi})

    logger.ok(f"Fikir hazir: {fikir['konu']}")
    return fikir
