# -*- coding: utf-8 -*-
"""
ADIM 4 - SESLENDIRME
Her sahnenin anlatim metnini Microsoft'un Turkce nöral sesleriyle seslendirir.
edge-tts ucretsizdir ve API anahtari istemez.

Bu modul ayrica KELIME ZAMANLARINI kaydeder (karaoke altyazi icin).
Sessizlik kirpma zamanlari kaydiracagi icin, kirpma "ne kesildigini bilen"
bir yontemle yapilir ve kelime zamanlari buna gore duzeltilir.
"""
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import config
from utils import logger


class SesHatasi(Exception):
    pass


def _ffmpeg() -> str:
    from steps.step5_montaj import ffmpeg_yolu
    return ffmpeg_yolu()


# ------------------------------------------------------------------ sure olcumu
def _sure_olc(yol: Path) -> float:
    """Ses dosyasinin suresini saniye cinsinden dondurur."""
    try:
        from mutagen.mp3 import MP3
        return float(MP3(str(yol)).info.length)
    except Exception:
        pass
    try:
        sonuc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(yol)],
            capture_output=True, text=True, timeout=30,
        )
        if sonuc.returncode == 0 and sonuc.stdout.strip():
            return float(sonuc.stdout.strip())
    except Exception:
        pass
    raise SesHatasi(
        "Ses suresi olculemedi. 'python -m pip install mutagen' calistir."
    )


# ------------------------------------------------------------------ uretim
async def _seslendir_tek(metin: str, hedef: Path) -> List[Dict[str, Any]]:
    """Metni seslendirir ve her kelimenin baslangic anini toplar."""
    import edge_tts

    iletisim = edge_tts.Communicate(
        text=metin, voice=config.SES_ADI,
        rate=config.SES_HIZI, pitch=config.SES_PERDESI,
    )
    gecici = hedef.with_suffix(".uretiliyor")
    kelimeler: List[Dict[str, Any]] = []

    with open(gecici, "wb") as f:
        async for parca in iletisim.stream():
            if parca["type"] == "audio":
                f.write(parca["data"])
            elif parca["type"] == "WordBoundary":
                # Zamanlar 100 nanosaniye biriminde geliyor
                kelimeler.append({
                    "metin": parca["text"],
                    "basla": parca["offset"] / 10_000_000,
                    "sure": parca["duration"] / 10_000_000,
                })

    if not gecici.exists() or gecici.stat().st_size < 1024:
        gecici.unlink(missing_ok=True)
        raise SesHatasi("Uretilen ses dosyasi bos.")

    gecici.replace(hedef)
    return kelimeler


def _uret(metin: str, hedef: Path) -> List[Dict[str, Any]]:
    """Secili motorla seslendirir ve kelime zamanlarini dondurur.

    Gemini basarisiz olursa edge-tts'e duser; uretim durmaz.
    """
    if config.SES_MOTORU == "gemini":
        from utils import gemini_ses

        ok, bilgi = gemini_ses.seslendir_tek(metin, hedef)
        if ok:
            sure = _sure_olc(hedef)
            return gemini_ses.kelime_zamanlari(metin, sure)

        logger.uyari(f"  Gemini ses basarisiz ({bilgi}). edge-tts deneniyor...")

    # edge-tts (varsayilan veya yedek)
    return _calistir(_seslendir_tek(metin, hedef))


def _calistir(coro):
    """Windows'ta asyncio'yu guvenli calistirir."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(coro)


# ------------------------------------------------------------------ sessizlik
def _sessizlikleri_bul(yol: Path) -> List[Tuple[float, float]]:
    """Dosyadaki sessizlik araliklarini dondurur."""
    cikti = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-i", str(yol),
         "-af", f"silencedetect=noise={config.SESSIZLIK_ESIGI}:d=0.12",
         "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr

    araliklar, basla = [], None
    for satir in cikti.splitlines():
        if "silence_start:" in satir:
            basla = float(satir.split("silence_start:")[1].strip())
        elif "silence_end:" in satir and basla is not None:
            bitis = float(satir.split("silence_end:")[1].split("|")[0].strip())
            araliklar.append((basla, bitis))
            basla = None
    return araliklar


def _tutulacaklar(sessizlikler, toplam):
    """Hangi bolumlerin korunacagini hesaplar.

    Bastaki ve sondaki sessizlik tamamen atilir; ic duraklamalar
    CUMLE_ARASI_DURAKLAMA suresine kisaltilir.
    """
    sinir = config.CUMLE_ARASI_DURAKLAMA
    tut, imlec = [], 0.0

    for basla, bitir in sessizlikler:
        if basla > imlec:
            tut.append((imlec, basla))                    # konusma
        bastaki = basla <= 0.08
        sondaki = bitir >= toplam - 0.08
        if not bastaki and not sondaki:
            tut.append((basla, min(basla + sinir, bitir)))  # kisaltilmis duraklama
        imlec = bitir

    if imlec < toplam:
        tut.append((imlec, toplam))

    return [(a, b) for a, b in tut if b - a > 0.01]


def _zaman_esle(tut, eski_an: float) -> float:
    """Kirpma sonrasi bir anin yeni karsiligini hesaplar."""
    yeni = 0.0
    for basla, bitir in tut:
        if eski_an >= bitir:
            yeni += bitir - basla
        elif eski_an > basla:
            yeni += eski_an - basla
            break
        else:
            break
    return yeni


def _kirp(yol: Path, tut) -> bool:
    """Belirlenen bolumleri birlestirip dosyayi yeniden yazar."""
    if not tut:
        return False
    parcalar = [
        f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[p{i}]"
        for i, (a, b) in enumerate(tut)
    ]
    girisler = "".join(f"[p{i}]" for i in range(len(tut)))
    filtre = ";".join(parcalar) + f";{girisler}concat=n={len(tut)}:v=0:a=1[out]"

    gecici = yol.with_suffix(".kirpiliyor.mp3")
    sonuc = subprocess.run(
        [_ffmpeg(), "-y", "-loglevel", "error", "-i", str(yol),
         "-filter_complex", filtre, "-map", "[out]",
         "-c:a", "libmp3lame", "-q:a", "4", str(gecici)],
        capture_output=True, text=True,
    )
    if sonuc.returncode != 0 or not gecici.exists() or gecici.stat().st_size < 512:
        gecici.unlink(missing_ok=True)
        return False
    gecici.replace(yol)
    return True


def _sessizligi_kirp(yol: Path, kelimeler: List[Dict[str, Any]]) -> bool:
    """Sessizlikleri kirpar ve kelime zamanlarini duzeltir."""
    if not config.SESSIZLIK_KIRP:
        return False
    try:
        toplam = _sure_olc(yol)
        sessizlikler = _sessizlikleri_bul(yol)
        if not sessizlikler:
            return False

        tut = _tutulacaklar(sessizlikler, toplam)
        if toplam - sum(b - a for a, b in tut) < 0.1:
            return False
        if not _kirp(yol, tut):
            return False

        for k in kelimeler:
            eski_bitis = k["basla"] + k["sure"]
            k["basla"] = round(_zaman_esle(tut, k["basla"]), 3)
            k["sure"] = round(max(_zaman_esle(tut, eski_bitis) - k["basla"], 0.08), 3)
        return True
    except Exception as e:                              # noqa: BLE001
        logger.uyari(f"Sessizlik kirpilamadi ({e}). Ham ses kullanilacak.")
        return False


# ------------------------------------------------------------------ ton deneme
ORNEK_CUMLE = (
    "Merhaba minik dostum! Bugün çok eğlenceli bir şey öğreneceğiz. "
    "Hazır mısın? Haydi başlayalım!"
)


async def _seslendir_ozel(metin, hedef, ses, hiz, perde):
    import edge_tts
    await edge_tts.Communicate(
        text=metin, voice=ses, rate=hiz, pitch=perde
    ).save(str(hedef))


def tonlari_dene(cumle: str = "") -> None:
    """Her ton ayariyla ayni cumleyi seslendirir."""
    metin = cumle or ORNEK_CUMLE
    klasor = config.ASSETS_DIR / "ton_ornekleri"
    klasor.mkdir(parents=True, exist_ok=True)

    logger.baslik("SES TONU ORNEKLERI")
    logger.bilgi(f'Ornek cumle: "{metin}"')
    print()

    for ad, ayar in config.SES_TONLARI.items():
        hedef = klasor / f"{ad}.mp3"
        try:
            _calistir(_seslendir_ozel(
                metin, hedef, ayar["ses"], ayar["hiz"], ayar["perde"]
            ))
            sure = _sure_olc(hedef)
            hiz = len(metin.split()) / sure if sure else 0
            print(f"    {ad:14} {ayar['hiz']:>5} {ayar['perde']:>7}   "
                  f"{sure:4.1f} sn  ({hiz:.2f} kelime/sn)   {ayar['aciklama']}")
        except Exception as e:                          # noqa: BLE001
            logger.hata(f"    {ad}: uretilemedi ({e})")

    print()
    logger.ok(f"Ornekler burada: {klasor}")
    logger.bilgi("Begendigini .env dosyasina yaz:\n    SES_TONU=cok_canli")


# ------------------------------------------------------------------ ses listesi
def turkce_sesleri_listele() -> None:
    import edge_tts

    async def _al():
        return await edge_tts.list_voices()

    sesler = _calistir(_al())
    turkce = [s for s in sesler if s.get("Locale", "").startswith("tr")]

    logger.baslik("KULLANILABILIR TURKCE SESLER")
    for s in turkce:
        cinsiyet = "Kadin" if s.get("Gender") == "Female" else "Erkek"
        print(f"  {s['ShortName']:<28} {cinsiyet}")
    print(f"\nSecili ses: {config.SES_ADI}  (ton: {config.SES_TONU})")


# ------------------------------------------------------------------ ana fonksiyon
def seslendir(proje_dir: Path, senaryo: Dict[str, Any]) -> List[Path]:
    ses_dir = proje_dir / "ses"
    ses_dir.mkdir(exist_ok=True)

    sahneler = senaryo["sahneler"]
    if config.SES_MOTORU == "gemini":
        logger.bilgi(
            f"{len(sahneler)} sahne seslendirilecek "
            f"(motor: Gemini, ses: {config.GEMINI_SESI})"
        )
    else:
        logger.bilgi(
            f"{len(sahneler)} sahne seslendirilecek "
            f"(motor: edge-tts, ton: {config.SES_TONU}, hiz: {config.SES_HIZI})"
        )

    yollar, basarisiz = [], []

    for sahne in sahneler:
        no = sahne["no"]
        hedef = ses_dir / f"sahne_{no:02d}.mp3"

        # Zaten uretilmis VE kelime zamanlari kayitliysa dokunma
        if hedef.exists() and hedef.stat().st_size > 1024 and sahne.get("kelimeler"):
            sure = _sure_olc(hedef)
            sahne["ses"] = hedef.name
            sahne["ses_suresi"] = round(sure, 2)
            yollar.append(hedef)
            logger.bilgi(f"  Sahne {no:2d}: zaten var ({sure:.1f} sn)")
            continue

        for deneme in range(1, 4):
            try:
                kelimeler = _uret(sahne["anlatim"], hedef)
                _sessizligi_kirp(hedef, kelimeler)

                sure = _sure_olc(hedef)
                sahne["ses"] = hedef.name
                sahne["ses_suresi"] = round(sure, 2)
                sahne["kelimeler"] = kelimeler
                yollar.append(hedef)
                logger.ok(
                    f"  Sahne {no:2d}: hazir ({sure:.1f} sn, "
                    f"{len(kelimeler)} kelime)"
                )
                break
            except Exception as e:                     # noqa: BLE001
                if deneme < 3:
                    logger.uyari(f"  Sahne {no:2d}: deneme {deneme} basarisiz ({e})")
                    time.sleep(2 * deneme)
                else:
                    logger.hata(f"  Sahne {no:2d}: SESLENDIRILEMEDI - {e}")
                    basarisiz.append(no)

    if basarisiz:
        logger.uyari(f"{len(basarisiz)} sahne seslendirilemedi: {basarisiz}")
        return yollar

    toplam_ses = sum(s.get("ses_suresi", 0) for s in sahneler)
    toplam_kelime = sum(len(s["anlatim"].split()) for s in sahneler)
    hedef_sure = config.VIDEO_TIPLERI[senaryo["video_tipi"]]["hedef_saniye"]
    senaryo["toplam_ses_suresi"] = round(toplam_ses, 1)

    logger.ok(f"Tum sesler hazir. Toplam: {toplam_ses:.1f} sn")

    if toplam_ses > 0:
        gercek = toplam_kelime / toplam_ses
        logger.bilgi(
            f"Olculen konusma hizi: {gercek:.2f} kelime/sn "
            f"(ayarlardaki tahmin {config.KELIME_HIZI})"
        )
        sapma = abs(toplam_ses - hedef_sure) / hedef_sure
        if sapma > 0.25:
            yon = "kisa" if toplam_ses < hedef_sure else "uzun"
            logger.uyari(
                f"Video hedeften %{sapma*100:.0f} {yon}: "
                f"{toplam_ses:.0f} sn / hedef {hedef_sure} sn"
            )

    return yollar
