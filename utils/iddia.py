# -*- coding: utf-8 -*-
"""
IDDIA YUMUSATMA
Senaryoda kalan riskli kesinlik iddialarini otomatik olarak duzeltir.

Neden gerekli: yapay zeka "dunyanin ilk", "tam 3.472 kisi", "12 Mart 1453'te"
gibi ifadeleri emin bir dille uretiyor ve bunlarin yanlis cikma ihtimali yuksek.
Her videoyu elle kontrol etmek yerine, bu modul riskli cumleleri tespit edip
yapay zekaya geri gonderiyor ve daha temkinli bir ifadeyle degistiriyor.

Iki asamali calisir:
  1) Basit kaliplar dogrudan degistirilir (hizli, API gerektirmez)
  2) Kalan riskli cumleler yapay zekaya yeniden yazdirilir
"""
import re
from typing import Any, Dict, List, Tuple

import config
from utils import ai, logger

# ------------------------------------------------------------------ 1. asama
# Dogrudan degistirilebilecek kaliplar: (arama, yerine)
# SADECE cumle yapisini bozmayan, tek kelimelik guvenli degisimler.
# "dunyanin ilk" gibi ifadeler kelime kelime degistirilemez ("bilinen erken kez"
# gibi bozuk sonuclar cikiyor); onlar yapay zekaya birakiliyor.
BASIT_DEGISIMLER: List[Tuple[str, str]] = [
    (r"\bkesinlikle\b", "büyük olasılıkla"),
    (r"\bhiç şüphesiz\b", "büyük olasılıkla"),
    (r"\bhic suphesiz\b", "büyük olasılıkla"),
    (r"\bmuhakkak ki\b", "büyük olasılıkla"),
    (r"\bkanıtlanmıştır\b", "düşünülmektedir"),
    (r"\bkanitlanmistir\b", "düşünülmektedir"),
    (r"\bispatlanmıştır\b", "düşünülmektedir"),
]

# Bu kaliplar kaliyorsa yapay zekaya gonderilir (basit degisim yetmez)
KARMASIK_RISKLER = [
    # Kanitlanmasi zor ustunluk iddialari
    r"\b(dünyanın|dunyanin|tarihin|tarihteki)\s+(ilk|en)\b",
    r"\btarihte ilk\b",
    r"\bilk (kez|defa|olarak|kişi|insan|toplum|uygarlık|uygarlik)\b",
    r"\ben (eski|büyük|kucuk|küçük|uzun|kısa|kisa|hızlı|hizli|zengin|güçlü|guclu|onemli|önemli)\b",
    r"\btek (örneği|ornegi|örnek|ornek)\b",
    # Kesin sayi ve tarih
    r"\btam \d[\d.,]*\b",
    r"\b\d{1,2}\s+(ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|"
    r"ağustos|agustos|eylül|eylul|ekim|kasım|kasim|aralık|aralik)\s+\d{3,4}\b",
    # Kanit iddiasi
    r"\bbilim insanları kanıtladı\b",
    r"\bkanıtlanmış\b",
]

SISTEM = """Sen bir tarih metni editorusun.

GOREVIN: Verilen cumlelerdeki KANITLANMASI ZOR iddialari, anlami koruyarak
daha temkinli ifadelerle degistirmek.

KURALLAR:
- "ilk / en / tek" iddialarini kaldir. Bunlar tartismalidir.
- Kesin gun-ay tarihlerini yuzyila veya on yila cevir.
- Kesin sayilari yaklasik ifadelere cevir.
- Cumlenin ANLAMINI ve AKICILIGINI koru. Kisaltma, uzatma.
- Turkce dilbilgisi kurallarina uy.
- Fazladan aciklama ekleme, sadece riskli kismi degistir.

ORNEKLER:
  "Catali ilk kez Bizanslilar kullandi."
  -> "Catal, Bizans saraylarinda kullanilan bir aracti."

  "12 Mart 1453'te sehir kusatildi."
  -> "15. yuzyilin ortalarinda sehir kusatildi."

  "Tam 3.472 kisi bu yolculuga katildi."
  -> "Binlerce kisi bu yolculuga katildi."

  "Dunyanin en eski tarifi buydu."
  -> "Bilinen eski tariflerden biri buydu."

Cevabini SADECE su JSON formatinda ver:
{{
  "duzeltmeler": [
    {{"no": 1, "yeni_metin": "duzeltilmis cumle"}}
  ]
}}"""


def _basit_duzelt(metin: str) -> Tuple[str, List[str]]:
    """Kalip eslesmesiyle dogrudan degistirilebilecekleri duzeltir."""
    degisenler = []
    for kalip, yerine in BASIT_DEGISIMLER:
        yeni, sayi = re.subn(kalip, yerine, metin, flags=re.IGNORECASE)
        if sayi:
            eslesme = re.search(kalip, metin, flags=re.IGNORECASE)
            degisenler.append(f"'{eslesme.group(0)}' -> '{yerine}'")
            metin = yeni
    return metin, degisenler


def _riskli_mi(metin: str) -> str | None:
    """Cumlede karmasik risk varsa eslesen ifadeyi dondurur."""
    for kalip in KARMASIK_RISKLER:
        e = re.search(kalip, metin, flags=re.IGNORECASE)
        if e:
            return e.group(0)
    return None


def yumusat(senaryo: Dict[str, Any]) -> int:
    """Senaryodaki riskli iddialari duzeltir. Duzeltilen sahne sayisini dondurur."""
    if not config.IDDIA_YUMUSAT:
        return 0

    sahneler = senaryo["sahneler"]

    # --- 1. asama: basit kalip degisimleri
    basit_sayac = 0
    for sahne in sahneler:
        yeni, degisenler = _basit_duzelt(sahne["anlatim"])
        if degisenler:
            sahne["anlatim"] = yeni
            sahne.setdefault("_duzeltmeler", []).extend(degisenler)
            basit_sayac += 1

    if basit_sayac:
        logger.ok(f"{basit_sayac} sahnede riskli ifade otomatik yumusatildi")

    # --- 2. asama: kalan riskler icin yapay zeka
    riskliler = []
    for sahne in sahneler:
        risk = _riskli_mi(sahne["anlatim"])
        if risk:
            riskliler.append((sahne, risk))

    if not riskliler:
        return basit_sayac

    logger.bilgi(f"{len(riskliler)} sahne yapay zekaya yeniden yazdiriliyor...")

    liste = "\n".join(
        f"{i}. {sahne['anlatim']}   [riskli kisim: {risk}]"
        for i, (sahne, risk) in enumerate(riskliler, 1)
    )
    istek = f"Su cumlelerdeki riskli iddialari yumusat:\n\n{liste}"

    mock = {"duzeltmeler": [
        {"no": i, "yeni_metin": sahne["anlatim"]}
        for i, (sahne, _) in enumerate(riskliler, 1)
    ]}

    try:
        cevap = ai.sor(SISTEM, istek, sicaklik=0.4, mock_cevap=mock)
    except Exception as e:                              # noqa: BLE001
        logger.uyari(
            f"Iddia yumusatma basarisiz ({e}). "
            "Senaryo oldugu gibi birakildi, elle kontrol et."
        )
        return basit_sayac

    duzeltildi = 0
    for d in cevap.get("duzeltmeler", []):
        try:
            sira = int(d["no"]) - 1
            yeni = str(d["yeni_metin"]).strip()
        except Exception:
            continue
        if not (0 <= sira < len(riskliler)) or len(yeni) < 10:
            continue

        sahne, risk = riskliler[sira]
        eski = sahne["anlatim"]

        # Yeni metin hala riskliyse kabul etme
        if _riskli_mi(yeni):
            logger.uyari(f"  Sahne {sahne['no']}: duzeltme yetersiz, elle kontrol et")
            continue

        # Uzunluk cok degistiyse anlam kaymis olabilir
        if not (0.5 <= len(yeni) / max(len(eski), 1) <= 1.8):
            logger.uyari(f"  Sahne {sahne['no']}: duzeltme cok farkli, atlandi")
            continue

        sahne["anlatim"] = yeni
        sahne.setdefault("_duzeltmeler", []).append(f"'{risk}' -> yeniden yazildi")
        logger.ok(f"  Sahne {sahne['no']}: '{risk}' duzeltildi")
        duzeltildi += 1

    return basit_sayac + duzeltildi
