# -*- coding: utf-8 -*-
"""
ADIM 5 - MONTAJ
Gorselleri ve sesleri birlestirip videoyu olusturur.

- Her sahneye Ken Burns hareketi verir (yavas zoom / kaydirma)
- Sahne suresi o sahnenin ses suresine gore ayarlanir
- Varsa arka plan muzigi ekler (assets/music klasoru)
- YouTube'a yuklenebilecek bir .srt altyazi dosyasi uretir

FFmpeg'i dogrudan kullanir; boylece MoviePy surum uyumsuzluklari yasanmaz.
"""
import json
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from utils import logger


class MontajHatasi(Exception):
    pass


# ------------------------------------------------------------------ ffmpeg bul
def ffmpeg_yolu() -> str:
    """Once sistemdeki ffmpeg'e, yoksa pip ile gelen surume bakar."""
    sistem = shutil.which("ffmpeg")
    if sistem:
        return sistem
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise MontajHatasi(
        "FFmpeg bulunamadi.\n"
        "Coz: python -m pip install imageio-ffmpeg\n"
        "(Bu, ffmpeg'i otomatik indirir; ayrica kurulum gerekmez.)"
    )


def _calistir(komut: List[str], aciklama: str, klasor: Optional[Path] = None) -> None:
    sonuc = subprocess.run(
        komut, capture_output=True, text=True,
        cwd=str(klasor) if klasor else None,
    )
    if sonuc.returncode != 0:
        son = "\n".join(sonuc.stderr.strip().splitlines()[-12:])
        raise MontajHatasi(f"{aciklama} basarisiz:\n{son}")


# ------------------------------------------------------------------ Ken Burns
def _altyazi_filtresi(altyazi: Optional[Path]) -> str:
    """Altyaziyi videoya gomen filtre parcasi.

    Dosya adi tek basina kullaniliyor (ffmpeg o klasorde calistiriliyor);
    boylece Windows yollarindaki ':' ve '\\' kacis sorunlari yasanmiyor.
    """
    if not altyazi or not altyazi.exists():
        return ""
    return f",subtitles={altyazi.name}"


def _zoom_ifadesi(hareket: str, kare_sayisi: int) -> Dict[str, str]:
    """Ken Burns hareketi icin zoom/x/y ifadelerini uretir."""
    z = config.ZOOM_MIKTARI
    d = max(kare_sayisi, 2)
    ilerleme = f"on/{d - 1}"
    orta_x, orta_y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"

    if hareket == "zoom_in":
        return {"z": f"1+{z}*{ilerleme}", "x": orta_x, "y": orta_y}
    if hareket == "zoom_out":
        return {"z": f"1+{z}-{z}*{ilerleme}", "x": orta_x, "y": orta_y}
    if hareket == "pan_right":
        return {"z": f"1+{z}", "x": f"(iw-iw/zoom)*{ilerleme}", "y": orta_y}
    if hareket == "pan_left":
        return {"z": f"1+{z}", "x": f"(iw-iw/zoom)*(1-{ilerleme})", "y": orta_y}
    if hareket == "pan_down":
        return {"z": f"1+{z}", "x": orta_x, "y": f"(ih-ih/zoom)*{ilerleme}"}
    if hareket == "pan_up":
        return {"z": f"1+{z}", "x": orta_x, "y": f"(ih-ih/zoom)*(1-{ilerleme})"}
    return {"z": f"1+{z}*{ilerleme}", "x": orta_x, "y": orta_y}


def _ass_zaman(sn: float) -> str:
    """Saniyeyi ASS formatina cevirir: 0:00:01.23"""
    sn = max(sn, 0)
    saat, kalan = divmod(sn, 3600)
    dakika, saniye = divmod(kalan, 60)
    return f"{int(saat)}:{int(dakika):02d}:{saniye:05.2f}"


def _kelime_gruplari(kelimeler: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Kelimeleri altyazi parcalarina boler.

    Cok kisa kelimeler tek basina ekranda titrer; bu yuzden asgari sureyi
    dolduracak kadar kelimeyi birlestiriyoruz.
    """
    asgari = config.ALTYAZI_ASGARI_SURE
    en_fazla = config.ALTYAZI_KELIME_SAYISI

    gruplar, birikim = [], []
    for k in kelimeler:
        birikim.append(k)
        basla = birikim[0]["basla"]
        bitis = k["basla"] + k["sure"]
        if (bitis - basla >= asgari and len(birikim) >= 1) or len(birikim) >= en_fazla:
            gruplar.append({
                "metin": " ".join(x["metin"] for x in birikim),
                "basla": basla,
                "bitis": bitis,
            })
            birikim = []

    if birikim:
        gruplar.append({
            "metin": " ".join(x["metin"] for x in birikim),
            "basla": birikim[0]["basla"],
            "bitis": birikim[-1]["basla"] + birikim[-1]["sure"],
        })

    # Parcalar arasinda bosluk kalmasin: her biri bir sonrakine kadar dursun
    for i in range(len(gruplar) - 1):
        gruplar[i]["bitis"] = max(gruplar[i]["bitis"], gruplar[i + 1]["basla"] - 0.02)

    return gruplar


def _ass_yaz(sahne: Dict[str, Any], hedef: Path, gen: int, yuk: int,
             sure: float) -> bool:
    """Bir sahne icin karaoke altyazi dosyasi uretir."""
    kelimeler = sahne.get("kelimeler") or []
    if not kelimeler:
        return False

    punto = int(yuk * config.ALTYAZI_BOYUT_ORANI)
    kenar = max(int(punto * 0.14), 3)
    alt_bosluk = int(yuk * (1 - config.ALTYAZI_KONUM))

    basliklar = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {gen}
PlayResY: {yuk}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{config.ALTYAZI_YAZI_TIPI},{punto},{config.ALTYAZI_RENK},{config.ALTYAZI_RENK},{config.ALTYAZI_KENAR_RENGI},&H90000000,-1,0,0,0,100,100,0,0,1,{kenar},2,2,80,80,{alt_bosluk},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    satirlar = []
    for grup in _kelime_gruplari(kelimeler):
        basla = max(grup["basla"], 0)
        bitis = min(grup["bitis"], sure)
        if bitis <= basla:
            continue
        # Kucukten buyuyerek beliren "pop" etkisi
        efekt = r"{\fscx82\fscy82\t(0,110,\fscx100\fscy100)}"
        metin = grup["metin"].replace("\n", " ").strip()
        if not metin:
            continue
        satirlar.append(
            f"Dialogue: 0,{_ass_zaman(basla)},{_ass_zaman(bitis)},K,,0,0,0,,"
            f"{efekt}{metin}"
        )

    if not satirlar:
        return False

    hedef.write_text(basliklar + "\n".join(satirlar) + "\n", encoding="utf-8")
    return True


# ------------------------------------------------------------------ sahne klibi
def _sahne_klibi(
    ffmpeg: str, gorsel: Path, ses: Path, hareket: str,
    sure: float, gen: int, yuk: int, hedef: Path, bosluk: float,
    gorsel_2: Optional[Path] = None, altyazi: Optional[Path] = None,
) -> None:
    """Bir sahnenin video klibini uretir.

    gorsel_2 verilirse iki poz arasinda yumusak gecis yapilir; karakter
    hareket ediyormus gibi gorunur. Ken Burns hareketi gecisin uzerine binir.
    """
    kare_sayisi = int(round(sure * config.FPS))
    buyuk_gen = int(gen * config.ZOOM_ON_OLCEK)
    buyuk_yuk = int(yuk * config.ZOOM_ON_OLCEK)
    zoom_f = _zoom_ifadesi(hareket, kare_sayisi)

    olcek = (
        f"scale={buyuk_gen}:{buyuk_yuk}:force_original_aspect_ratio=increase,"
        f"crop={buyuk_gen}:{buyuk_yuk},fps={config.FPS},format=yuv420p"
    )
    kenburns = (
        f"zoompan=z='{zoom_f['z']}':x='{zoom_f['x']}':y='{zoom_f['y']}':"
        f"d=1:s={gen}x{yuk}:fps={config.FPS},setsar=1,format=yuv420p"
    )

    if gorsel_2 and gorsel_2.exists():
        # Gecis sahnenin ortasinda olsun; oncesi ve sonrasi poz sabit kalsin
        gecis = min(config.POZ_GECIS_SURESI, sure * 0.4)
        baslangic = max((sure - gecis) * config.POZ_GECIS_KONUMU, 0.05)
        sure_a = baslangic + gecis
        sure_b = sure - baslangic

        girdiler = [
            "-loop", "1", "-t", f"{sure_a:.3f}", "-i", str(gorsel),
            "-loop", "1", "-t", f"{sure_b:.3f}", "-i", str(gorsel_2),
            "-i", str(ses),
        ]
        filtre = (
            f"[0:v]{olcek}[a];[1:v]{olcek}[b];"
            f"[a][b]xfade=transition=fade:duration={gecis:.3f}:"
            f"offset={baslangic:.3f}[x];"
            f"[x]{kenburns}{_altyazi_filtresi(altyazi)}[v];"
            f"[2:a]apad=pad_dur={bosluk},aresample=48000,"
            f"aformat=channel_layouts=stereo[a_out]"
        )
    else:
        girdiler = ["-loop", "1", "-i", str(gorsel), "-i", str(ses)]
        filtre = (
            f"[0:v]{olcek},{kenburns}{_altyazi_filtresi(altyazi)}[v];"
            f"[1:a]apad=pad_dur={bosluk},aresample=48000,"
            f"aformat=channel_layouts=stereo[a_out]"
        )

    komut = [ffmpeg, "-y", "-loglevel", "error"] + girdiler + [
        "-filter_complex", filtre,
        "-map", "[v]", "-map", "[a_out]",
        "-t", f"{sure:.3f}",
        "-c:v", "libx264", "-preset", config.X264_HIZI, "-crf", str(config.X264_KALITE),
        "-r", str(config.FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        str(hedef),
    ]
    _calistir(
        komut, f"Sahne klibi ({gorsel.name})",
        klasor=altyazi.parent if altyazi else None,
    )


# ------------------------------------------------------------------ altyazi
def _srt_yaz(sahneler: List[Dict[str, Any]], hedef: Path) -> None:
    def zaman(sn: float) -> str:
        saat, kalan = divmod(max(sn, 0), 3600)
        dakika, saniye = divmod(kalan, 60)
        return (f"{int(saat):02d}:{int(dakika):02d}:{int(saniye):02d},"
                f"{int((saniye % 1) * 1000):03d}")

    def bol(metin: str) -> List[str]:
        """Uzun metni altyaziya sigacak parcalara boler (kirpmaz)."""
        if len(metin) <= 84:
            return [metin]
        # Once cumlelerden bolmeyi dene
        cumleler = re.split(r"(?<=[.!?…])\s+", metin)
        parcalar, birikim = [], ""
        for c in cumleler:
            if len(birikim) + len(c) + 1 <= 84:
                birikim = f"{birikim} {c}".strip()
            else:
                if birikim:
                    parcalar.append(birikim)
                birikim = c
        if birikim:
            parcalar.append(birikim)
        # Tek cumle bile uzunsa kelimeden bol
        sonuc = []
        for p in parcalar:
            if len(p) <= 84:
                sonuc.append(p)
            else:
                kelimeler, satir = p.split(), ""
                for k in kelimeler:
                    if len(satir) + len(k) + 1 <= 84:
                        satir = f"{satir} {k}".strip()
                    else:
                        sonuc.append(satir)
                        satir = k
                if satir:
                    sonuc.append(satir)
        return sonuc

    satirlar, an, sira = [], 0.0, 1
    for sahne in sahneler:
        sure = sahne.get("_klip_suresi", 0)
        konusma = max(sure - config.SAHNE_ARASI_BOSLUK, 0.5)
        parcalar = bol(sahne["anlatim"])
        pay = konusma / len(parcalar)

        for i, parca in enumerate(parcalar):
            basla = an + i * pay
            bitis = basla + pay
            metin = "\n".join(textwrap.wrap(parca, width=42))
            satirlar += [str(sira), f"{zaman(basla)} --> {zaman(bitis)}", metin, ""]
            sira += 1
        an += sure

    hedef.write_text("\n".join(satirlar), encoding="utf-8")


def _gecis_sesi_uret(ffmpeg: str) -> Optional[Path]:
    """Sahne gecis sesini hazirlar.

    Sirasiyla:
      1) assets/sfx/gecis.wav varsa onu kullanir (kendi dosyani koyabilirsin)
      2) Yoksa config.SFX_TIPI'ne gore sentezler

    Efekt secenekleri: chime, pop, whoosh, arp, sparkle, marimba
    Dinlemek icin: python main.py --efektler
    """
    hedef = config.SFX_DIR / "gecis.wav"
    if hedef.exists():
        return hedef

    try:
        from utils import ses_efekti
        ses_efekti.uret(config.SFX_TIPI, hedef, tepe=config.SFX_TEPE_GENLIK)
        logger.bilgi(f"Gecis ses efekti olusturuldu: {config.SFX_TIPI}")
        return hedef
    except Exception as e:                              # noqa: BLE001
        logger.uyari(f"Gecis sesi uretilemedi ({e}). Efektsiz devam ediliyor.")
        return None


def _sfx_zamanlari(sahneler: List[Dict[str, Any]]) -> List[float]:
    """Ses efektinin calacagi anlar: her sahnenin baslangici (ilki haric)."""
    anlar, birikim = [], 0.0
    for sahne in sahneler[:-1]:
        birikim += sahne["_klip_suresi"]
        # Efekt, sahne degisiminden hemen once (sessizligin icinde) calsin
        anlar.append(max(birikim - config.SAHNE_ARASI_BOSLUK + 0.05, 0))
    return anlar


# ------------------------------------------------------------------ muzik
def _muzik_sec() -> Optional[Path]:
    if not config.MUZIK_KULLAN:
        return None
    parcalar = [
        p for p in config.MUSIC_DIR.iterdir()
        if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg")
    ] if config.MUSIC_DIR.exists() else []
    if not parcalar:
        return None
    return random.choice(parcalar)


def _ses_finali(
    ffmpeg: str, video: Path, muzik: Optional[Path],
    sfx: Optional[Path], sfx_anlari: List[float], hedef: Path,
) -> None:
    """Muzigi ve gecis efektlerini ekler, sesi YouTube seviyesine normalize eder.

    Goruntu yeniden kodlanmaz (-c:v copy), bu yuzden hizlidir.
    """
    norm = (
        f"loudnorm=I={config.HEDEF_SES_SEVIYESI}:TP=-1.5:LRA=11"
        if config.SES_NORMALIZE else "anull"
    )

    girdiler = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video)]
    parcalar, karisacaklar = [], ["[0:a]"]
    sonraki = 1

    if muzik:
        girdiler += ["-stream_loop", "-1", "-i", str(muzik)]
        parcalar.append(
            f"[{sonraki}:a]volume={config.MUZIK_SESI},"
            f"aformat=channel_layouts=stereo[muzik]"
        )
        karisacaklar.append("[muzik]")
        sonraki += 1

    if sfx and sfx_anlari:
        for i, an in enumerate(sfx_anlari):
            girdiler += ["-i", str(sfx)]
            ms = int(an * 1000)
            parcalar.append(
                f"[{sonraki}:a]adelay={ms}|{ms},volume={config.SFX_SESI}[sfx{i}]"
            )
            karisacaklar.append(f"[sfx{i}]")
            sonraki += 1

    if len(karisacaklar) == 1:
        filtre = f"[0:a]{norm}[a]"
    else:
        parcalar.append(
            "".join(karisacaklar)
            + f"amix=inputs={len(karisacaklar)}:duration=first:"
              f"dropout_transition=0:normalize=0[karisim]"
        )
        parcalar.append(f"[karisim]alimiter=limit=0.97,{norm}[a]")
        filtre = ";".join(parcalar)

    komut = girdiler + [
        "-filter_complex", filtre,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        str(hedef),
    ]
    _calistir(komut, "Ses finali (muzik + efekt + normalizasyon)")


# ------------------------------------------------------------------ ana fonksiyon
def videoyu_olustur(proje_dir: Path, senaryo: Dict[str, Any]) -> Path:
    ffmpeg = ffmpeg_yolu()
    gen, yuk = senaryo["genislik"], senaryo["yukseklik"]
    sahneler = senaryo["sahneler"]

    gecici_dir = proje_dir / "gecici"
    gecici_dir.mkdir(exist_ok=True)

    logger.bilgi(f"FFmpeg: {ffmpeg}")
    logger.bilgi(f"{len(sahneler)} sahne birlestirilecek ({gen}x{yuk}, {config.FPS} fps)")

    # --- 1) Her sahne icin ayri klip
    klipler = []
    for sahne in sahneler:
        no = sahne["no"]
        gorsel = (proje_dir / "gorseller" / f"sahne_{no:02d}.jpg").resolve()
        ses = (proje_dir / "ses" / f"sahne_{no:02d}.mp3").resolve()

        if not gorsel.exists():
            raise MontajHatasi(f"Sahne {no} gorseli eksik: {gorsel.name}")
        if not ses.exists():
            raise MontajHatasi(f"Sahne {no} sesi eksik: {ses.name}")

        # Sureyi senaryo.json'a guvenmek yerine ses dosyasindan olc.
        # Boylece ses yeniden uretilmis veya kayit eskimis olsa da dogru calisir.
        try:
            from steps.step4_ses import _sure_olc
            ses_suresi = _sure_olc(ses)
            kayitli = sahne.get("ses_suresi")
            if kayitli and abs(kayitli - ses_suresi) > 0.15:
                logger.uyari(
                    f"  Sahne {no}: kayitli sure {kayitli:.1f} sn, "
                    f"gercek {ses_suresi:.1f} sn. Gercek sure kullanilacak."
                )
            sahne["ses_suresi"] = round(ses_suresi, 2)
        except Exception:
            ses_suresi = float(sahne.get("ses_suresi", 3.0))

        # Son sahnede bosluk daha kisa: Shorts basa donunce olu hava duyulmasin
        son_mu = sahne is sahneler[-1]
        bosluk = config.SON_SAHNE_BOSLUK if son_mu else config.SAHNE_ARASI_BOSLUK
        sure = ses_suresi + bosluk
        sahne["_klip_suresi"] = round(sure, 3)

        gorsel_2 = (proje_dir / "gorseller" / f"sahne_{no:02d}b.jpg").resolve()
        iki_kare = config.IKI_KARE and gorsel_2.exists()

        altyazi = None
        if config.ALTYAZI_GOM:
            aday = gecici_dir / f"altyazi_{no:02d}.ass"
            if _ass_yaz(sahne, aday, gen, yuk, sure):
                altyazi = aday

        klip = (gecici_dir / f"klip_{no:02d}.mp4").resolve()
        _sahne_klibi(
            ffmpeg, gorsel, ses, sahne["hareket"], sure, gen, yuk, klip, bosluk,
            gorsel_2 if iki_kare else None, altyazi,
        )
        klipler.append(klip)
        etiketler = ["2 poz" if iki_kare else "tek kare"]
        if altyazi:
            etiketler.append("karaoke")
        logger.ok(
            f"  Sahne {no:2d}: {sure:.1f} sn "
            f"({sahne['hareket']}, {', '.join(etiketler)})"
        )

    # --- 2) Klipleri birlestir
    liste = gecici_dir / "liste.txt"
    liste.write_text(
        "\n".join(f"file '{k.resolve().as_posix()}'" for k in klipler),
        encoding="utf-8",
    )

    ham = gecici_dir / "ham_video.mp4"
    _calistir([
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(liste),
        "-c", "copy", str(ham),
    ], "Sahneleri birlestirme")
    logger.ok("Sahneler birlestirildi")

    # --- 3) Muzik
    final = proje_dir / "video.mp4"
    muzik = _muzik_sec()

    sfx, sfx_anlari = None, []
    if config.SFX_KULLAN and len(sahneler) > 1:
        sfx = _gecis_sesi_uret(ffmpeg)
        sfx_anlari = _sfx_zamanlari(sahneler)

    _ses_finali(ffmpeg, ham, muzik, sfx, sfx_anlari, final)

    if sfx and sfx_anlari:
        logger.ok(f"{len(sfx_anlari)} gecis ses efekti eklendi")
    if muzik:
        logger.ok(f"Arka plan muzigi eklendi: {muzik.name}")
    elif config.MUZIK_KULLAN:
        logger.uyari(
            "ARKA PLAN MUZIGI YOK -- video sessiz ve durgun duracak."
        )
        logger.bilgi(
            f"Coz: YouTube Studio > Ses Kitapligi'ndan telifsiz bir mp3 indirip "
            f"su klasore koy:\n         {config.MUSIC_DIR}"
        )
    if config.SES_NORMALIZE:
        logger.ok(f"Ses seviyesi normalize edildi ({config.HEDEF_SES_SEVIYESI} LUFS)")

    # --- 4) Altyazi
    srt = proje_dir / "altyazi.srt"
    _srt_yaz(sahneler, srt)

    # --- 5) Temizlik
    if config.GECICI_DOSYALARI_SIL:
        shutil.rmtree(gecici_dir, ignore_errors=True)

    toplam = sum(s["_klip_suresi"] for s in sahneler)
    boyut_mb = final.stat().st_size / (1024 * 1024)
    senaryo["video_suresi"] = round(toplam, 1)

    logger.ok(f"VIDEO HAZIR: {final.name}  ({toplam:.0f} sn, {boyut_mb:.1f} MB)")
    logger.bilgi(f"Altyazi dosyasi: {srt.name} (YouTube'a ayrica yuklenebilir)")

    return final
