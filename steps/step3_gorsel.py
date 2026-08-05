# -*- coding: utf-8 -*-
"""
ADIM 3 - GORSEL URETIMI
Her sahne icin Pollinations.ai uzerinden gorsel uretir.

Ozellikler:
- API anahtari gerektirmez, ucretsizdir
- Ayni proje icin sabit seed kullanir (karakter tutarliligi icin)
- Basarisiz gorseli tekrar dener
- Bozuk/eksik dosyayi tespit eder
- Zaten indirilmis gorselleri atlar (yarim kalirsa kaldigi yerden devam eder)
"""
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

import config
from utils import logger

try:
    from PIL import Image
except ImportError:
    Image = None


class GorselHatasi(Exception):
    pass


def _pexels_indir(sahne, hedef: Path, dikey: bool, kullanilanlar: set) -> str:
    """Pexels'ten fotograf indirir. Fotografci adini dondurur."""
    from utils import pexels_kaynak

    url, terim, fotografci = pexels_kaynak.gorsel_url_bul(
        sahne["gorsel_prompt"], dikey, kullanilanlar
    )
    _indir(url, hedef)
    sahne["_arama_terimi"] = terim
    sahne["_fotografci"] = fotografci
    return fotografci


def _url_olustur(prompt: str, genislik: int, yukseklik: int, seed: int) -> str:
    kodlu = urllib.parse.quote(prompt[:1800], safe="")
    parametreler = urllib.parse.urlencode({
        "width": genislik,
        "height": yukseklik,
        "seed": seed,
        "model": config.GORSEL_MODEL,
        "nologo": "true",
        "enhance": "false",
        "safe": "true",          # cocuk icerigi -- guvenli mod acik
    })
    return f"{config.POLLINATIONS_URL}/{kodlu}?{parametreler}"


def _sahne_seed(temel: int, sahne_no: int, tazele: int = 0) -> int:
    """Sahne icin seed hesaplar.

    'sahne_basi' modunda her sahne farkli seed alir -> kadraj ve aci degisir.
    'sabit' modunda hepsi ayni seed'i kullanir -> kompozisyon da ayni kalir.
    tazele: gorseli yeniden uretirken farkli sonuc almak icin kaydirma.
    """
    if config.SEED_MODU == "sabit":
        return (temel + tazele * 7919) % 1_000_000
    return (temel + sahne_no * 1013 + tazele * 7919) % 1_000_000


def _gorsel_gecerli_mi(yol: Path, min_kb: int = 15) -> bool:
    """Indirilen dosya gercekten kullanilabilir bir gorsel mi?"""
    if not yol.exists():
        return False
    if yol.stat().st_size < min_kb * 1024:
        return False
    if Image is None:
        return True
    try:
        with Image.open(yol) as im:
            im.verify()
        with Image.open(yol) as im:
            if im.width < 200 or im.height < 200:
                return False
            # Tamamen tek renk mi? (hata sayfasi / bos kare)
            kucuk = im.convert("RGB").resize((32, 32))
            renkler = kucuk.getcolors(32 * 32)
            if renkler and len(renkler) <= 2:
                return False
        return True
    except Exception:
        return False


def _indir(url: str, hedef: Path) -> None:
    import requests

    basliklar = {}
    if getattr(config, "POLLINATIONS_TOKEN", ""):
        basliklar["Authorization"] = f"Bearer {config.POLLINATIONS_TOKEN}"

    cevap = requests.get(
        url, headers=basliklar,
        timeout=config.GORSEL_ZAMAN_ASIMI, stream=True,
    )
    if cevap.status_code != 200:
        raise GorselHatasi(f"HTTP {cevap.status_code}: {cevap.text[:200]}")

    tur = cevap.headers.get("Content-Type", "")
    if "image" not in tur:
        raise GorselHatasi(f"Gorsel yerine '{tur}' geldi.")

    gecici = hedef.with_suffix(".indiriliyor")
    with open(gecici, "wb") as f:
        for parca in cevap.iter_content(chunk_size=65536):
            f.write(parca)

    if not _gorsel_gecerli_mi(gecici):
        boyut = gecici.stat().st_size if gecici.exists() else 0
        gecici.unlink(missing_ok=True)
        raise GorselHatasi(f"Indirilen dosya bozuk veya bos ({boyut} bayt).")

    gecici.replace(hedef)


def gorselleri_uret(
    proje_dir: Path,
    senaryo: Dict[str, Any],
    sadece_sahne: int | None = None,
    yeniden: bool = False,
) -> List[Path]:
    """Senaryodaki her sahne icin bir gorsel uretir.

    sadece_sahne: sadece bu sahne numarasi uretilir (None ise hepsi)
    yeniden: dosya zaten varsa bile farkli bir seed ile tekrar uretilir
    """
    gorsel_dir = proje_dir / "gorseller"
    gorsel_dir.mkdir(exist_ok=True)

    genislik = senaryo["genislik"]
    yukseklik = senaryo["yukseklik"]
    seed = senaryo.get("seed")
    if seed is None:
        import random
        seed = random.randint(1, 999_999)
        senaryo["seed"] = seed

    sahneler = senaryo["sahneler"]
    if sadece_sahne is not None:
        sahneler = [s for s in sahneler if s["no"] == sadece_sahne]
        if not sahneler:
            raise GorselHatasi(f"Sahne {sadece_sahne} senaryoda yok.")
    logger.bilgi(
        f"{len(sahneler)} gorsel uretilecek ({genislik}x{yukseklik}, "
        f"temel seed={seed}, seed modu={config.SEED_MODU}, "
        f"model={config.GORSEL_MODEL})"
    )
    logger.bilgi("Bu adim uzun surebilir; her gorsel 10-30 saniye alabilir.")

    yollar, basarisiz = [], []
    kullanilanlar = set()      # ayni foto tekrar etmesin

    # Her sahne icin (dosya_soneki, prompt_alani) ciftleri
    for sahne in sahneler:
        isler = [("", "gorsel_prompt")]
        if config.IKI_KARE and sahne.get("gorsel_prompt_2"):
            isler.append(("b", "gorsel_prompt_2"))

        for sonek, alan in isler:
            _tek_gorsel(
                sahne, sonek, alan, gorsel_dir, genislik, yukseklik,
                seed, yeniden, yollar, basarisiz, kullanilanlar,
            )

    if basarisiz:
        logger.uyari(f"{len(basarisiz)} gorsel uretilemedi (sahne {basarisiz}).")
        logger.bilgi(
            "Gorsel servisi gecici olarak sorunlu olabilir. Biraz bekleyip "
            "su komutu calistir; sadece eksikler denenir:\n"
            f"    python main.py --devam {proje_dir.name}"
        )
    else:
        logger.ok(f"Tum gorseller hazir ({len(yollar)} adet)")

    return yollar


def _tek_gorsel(sahne, sonek, alan, gorsel_dir, genislik, yukseklik,
                seed, yeniden, yollar, basarisiz, kullanilanlar) -> None:
    """Tek bir gorseli uretir. sonek='' ana kare, sonek='b' ikinci poz."""
    no = sahne["no"]
    hedef = gorsel_dir / f"sahne_{no:02d}{sonek}.jpg"

    # Zaten var mi? (yarim kalan isi tekrarlamayalim)
    etiket = f"Sahne {no:2d}{' (2. poz)' if sonek else ''}"

    if not yeniden and _gorsel_gecerli_mi(hedef):
        logger.bilgi(f"  {etiket}: zaten var, atlaniyor.")
        yollar.append(hedef)
        sahne["gorsel" + sonek] = hedef.name
        return

    # Yeniden uretiliyorsa her denemede farkli seed kullan
    tazele = sahne.get("_tazeleme", 0) + (1 if yeniden else 0)
    sahne_seed = _sahne_seed(seed, no, tazele)
    if yeniden:
        sahne["_tazeleme"] = tazele

    pexels_modu = config.GORSEL_KAYNAGI == "pexels"
    if not pexels_modu:
        url = _url_olustur(sahne[alan], genislik, yukseklik, sahne_seed)

    for deneme in range(1, config.GORSEL_DENEME + 1):
        try:
            basla = time.time()
            if pexels_modu:
                fotografci = _pexels_indir(
                    sahne, hedef, yukseklik > genislik, kullanilanlar
                )
                ek = f", {fotografci}" if fotografci else ""
            else:
                _indir(url, hedef)
                ek = ""
            sure = time.time() - basla
            kb = hedef.stat().st_size // 1024
            logger.ok(f"  {etiket}: hazir ({kb} KB, {sure:.0f} sn{ek})")
            yollar.append(hedef)
            sahne["gorsel" + sonek] = hedef.name
            break
        except Exception as e:                      # noqa: BLE001
            if deneme < config.GORSEL_DENEME:
                logger.uyari(f"  {etiket}: deneme {deneme} basarisiz ({e})")
                time.sleep(config.GORSEL_BEKLEME * deneme * 2)
            else:
                logger.hata(f"  {etiket}: URETILEMEDI - {e}")
                # 2. poz uretilemezse video yine calisir, sadece hareketsiz olur
                if not sonek:
                    basarisiz.append(no)

    time.sleep(config.GORSEL_BEKLEME)
