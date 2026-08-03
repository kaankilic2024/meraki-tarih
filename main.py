# -*- coding: utf-8 -*-
"""
YOUTUBE VIDEO OTOMASYONU - ANA DOSYA

Kullanim ornekleri:
    python main.py --tip shorts              # 1 adet shorts senaryosu
    python main.py --tip uzun                # 1 adet uzun video senaryosu
    python main.py --gunluk                  # gunluk plan (2 shorts + 2 uzun)
    python main.py --tip shorts --mock       # API'siz test
"""
import argparse
import json
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

import config
from utils import logger
from steps import (step1_fikir, step2_senaryo, step3_gorsel,
                   step4_ses, step5_montaj, step6_yukle)


def _klasor_adi(baslik: str, video_tipi: str) -> str:
    """Baslikatan guvenli klasor ismi uretir."""
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    ad = baslik.translate(tr)
    ad = re.sub(r"[^a-zA-Z0-9]+", "_", ad).strip("_").lower()[:40]
    damga = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{damga}_{video_tipi}_{ad}"


def tek_video(video_tipi: str, atla_gorsel: bool = False,
              yukle: bool = False) -> Path:
    """Bir video projesi uretir. Simdilik adim 1-3."""
    logger.baslik(f"YENI PROJE  •  {config.VIDEO_TIPLERI[video_tipi]['ad']}")

    # --- ADIM 1
    logger.adim("ADIM 1/6  Icerik fikri uretiliyor")
    fikir = step1_fikir.fikir_uret(video_tipi)
    print(f"\n   Konu   : {fikir['konu']}")
    print(f"   Yas    : {fikir.get('hedef_yas', '-')}")
    print(f"   Ozet   : {fikir['ozet']}")
    print(f"   Mesaj  : {fikir['mesaj']}\n")

    # --- ADIM 2
    logger.adim("ADIM 2/6  Senaryo yaziliyor")
    senaryo = step2_senaryo.senaryo_uret(fikir)

    # --- Kaydet (ayni isim varsa sonuna numara ekle, uzerine yazma)
    temel = config.OUTPUT_DIR / _klasor_adi(senaryo["baslik"], video_tipi)
    proje_dir, sayac = temel, 2
    while proje_dir.exists():
        proje_dir = temel.with_name(f"{temel.name}_{sayac}")
        sayac += 1
    proje_dir.mkdir(parents=True, exist_ok=True)
    (proje_dir / "gorseller").mkdir(exist_ok=True)
    (proje_dir / "ses").mkdir(exist_ok=True)

    (proje_dir / "senaryo.json").write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Insan gozuyle okunacak ozet
    satirlar = [
        f"BASLIK : {senaryo['baslik']}",
        f"TIP    : {config.VIDEO_TIPLERI[video_tipi]['ad']}",
        f"SURE   : ~{senaryo['tahmini_sure_sn']} sn  ({senaryo['toplam_kelime']} kelime)",
        f"SAHNE  : {len(senaryo['sahneler'])}",
        "",
        "ACIKLAMA:",
        senaryo["aciklama"],
        "",
        "ETIKETLER: " + ", ".join(senaryo["etiketler"]),
        "",
        "KARAKTER: " + (senaryo.get("karakter_sayfasi") or "(yok)"),
        "",
        "=" * 70,
    ]
    for s in senaryo["sahneler"]:
        kar = "karakter VAR" if s.get("karakter_sahnede") else "karakter YOK"
        satirlar += [
            f"\n[SAHNE {s['no']}]  hareket: {s['hareket']}  |  {kar}",
            f"  ANLATIM : {s['anlatim']}",
            f"  GORSEL  : {s['gorsel_prompt']}",
        ]
    (proje_dir / "senaryo_okunabilir.txt").write_text(
        "\n".join(satirlar), encoding="utf-8"
    )

    logger.ok(f"Proje kaydedildi: {proje_dir}")

    if senaryo.get("_uyari"):
        logger.uyari(
            "Bu senaryoda kontrol etmen gereken kelimeler var: "
            + ", ".join(senaryo["_uyari"])
        )

    if atla_gorsel:
        logger.bilgi("Gorsel uretimi atlandi (--senaryo-only).")
        return proje_dir

    # --- ADIM 3
    logger.adim("ADIM 3/6  Gorseller uretiliyor")
    step3_gorsel.gorselleri_uret(proje_dir, senaryo)

    # senaryo.json'u guncelle (seed ve gorsel dosya adlari eklendi)
    (proje_dir / "senaryo.json").write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- ADIM 4
    logger.adim("ADIM 4/6  Seslendirme yapiliyor")
    step4_ses.seslendir(proje_dir, senaryo)

    (proje_dir / "senaryo.json").write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- ADIM 5
    logger.adim("ADIM 5/6  Video montajlaniyor")
    step5_montaj.videoyu_olustur(proje_dir, senaryo)

    (proje_dir / "senaryo.json").write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not yukle:
        logger.bilgi(
            "Video hazir. YouTube'a yuklemek icin: "
            f"python main.py --yukle {proje_dir.name}"
        )
        return proje_dir

    # --- ADIM 6
    logger.adim("ADIM 6/6  YouTube'a yukleniyor")
    try:
        step6_yukle.yukle(proje_dir, senaryo)
    except Exception as e:                            # noqa: BLE001
        logger.hata(f"Yukleme basarisiz: {e}")
        logger.bilgi("Video klasorde duruyor; sorunu cozup --yukle ile tekrar dene.")
    finally:
        (proje_dir / "senaryo.json").write_text(
            json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return proje_dir


def _proje_bul(klasor: str) -> Path:
    """Klasor adini cozer. 'son' yazilirsa en yeni projeyi secer.

    Bulamazsa mevcut projeleri listeleyerek anlasilir bir hata verir.
    """
    if klasor.lower() in ("son", "last", "sonuncu"):
        projeler = sorted(
            (d for d in config.OUTPUT_DIR.iterdir()
             if d.is_dir() and (d / "senaryo.json").exists()),
            key=lambda d: d.stat().st_mtime,
        )
        if not projeler:
            raise FileNotFoundError("Hic proje bulunamadi. Once bir video uret.")
        logger.bilgi(f"En son proje seciliyor: {projeler[-1].name}")
        return projeler[-1]

    proje_dir = Path(klasor)
    if not proje_dir.is_absolute():
        proje_dir = config.OUTPUT_DIR / klasor

    if (proje_dir / "senaryo.json").exists():
        return proje_dir

    # Bulunamadi: kullaniciya secenekleri goster
    mevcut = sorted(
        (d.name for d in config.OUTPUT_DIR.iterdir()
         if d.is_dir() and (d / "senaryo.json").exists()),
        reverse=True,
    )
    mesaj = f"'{klasor}' adinda bir proje yok."
    if mevcut:
        liste = "\n".join(f"    {ad}" for ad in mevcut[:10])
        mesaj += (
            f"\n\nMevcut projeler:\n{liste}"
            f"\n\nEn sonuncusunu kullanmak icin:  python main.py --devam son"
        )
    else:
        mesaj += " output klasoru bos."
    raise FileNotFoundError(mesaj)


def projeye_devam(klasor: str) -> Path:
    """Var olan bir projenin eksik gorsellerini tamamlar."""
    proje_dir = _proje_bul(klasor)
    senaryo_yolu = proje_dir / "senaryo.json"
    senaryo = json.loads(senaryo_yolu.read_text(encoding="utf-8"))
    logger.baslik(f"DEVAM  •  {senaryo['baslik']}")

    logger.adim("ADIM 3/6  Eksik gorseller tamamlaniyor")
    step3_gorsel.gorselleri_uret(proje_dir, senaryo)

    logger.adim("ADIM 4/6  Eksik sesler tamamlaniyor")
    step4_ses.seslendir(proje_dir, senaryo)

    logger.adim("ADIM 5/6  Video montajlaniyor")
    step5_montaj.videoyu_olustur(proje_dir, senaryo)

    senaryo_yolu.write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.ok(f"Proje guncellendi: {proje_dir}")
    return proje_dir


def gorsel_yenile(klasor: str, sahne_no: int) -> Path:
    """Begenilmeyen tek bir gorseli farkli bir seed ile yeniden uretir."""
    proje_dir = _proje_bul(klasor)
    senaryo_yolu = proje_dir / "senaryo.json"
    senaryo = json.loads(senaryo_yolu.read_text(encoding="utf-8"))
    logger.baslik(f"GORSEL YENILEME  •  sahne {sahne_no}")

    step3_gorsel.gorselleri_uret(
        proje_dir, senaryo, sadece_sahne=sahne_no, yeniden=True
    )

    senaryo_yolu.write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.bilgi("Begenmezsen ayni komutu tekrar calistir, baska bir seed denenir.")
    return proje_dir


def sadece_montaj(klasor: str) -> Path:
    """Gorsel ve sesler hazirsa videoyu (yeniden) olusturur."""
    proje_dir = _proje_bul(klasor)
    senaryo_yolu = proje_dir / "senaryo.json"
    senaryo = json.loads(senaryo_yolu.read_text(encoding="utf-8"))
    logger.baslik(f"MONTAJ  •  {senaryo['baslik']}")

    step5_montaj.videoyu_olustur(proje_dir, senaryo)
    senaryo_yolu.write_text(
        json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return proje_dir


def videoyu_yukle(klasor: str) -> None:
    """Hazir bir projeyi YouTube'a yukler."""
    proje_dir = _proje_bul(klasor)
    senaryo_yolu = proje_dir / "senaryo.json"
    senaryo = json.loads(senaryo_yolu.read_text(encoding="utf-8"))
    logger.baslik(f"YOUTUBE'A YUKLEME  •  {senaryo['baslik']}")

    try:
        step6_yukle.yukle(proje_dir, senaryo)
    finally:
        senaryo_yolu.write_text(
            json.dumps(senaryo, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def efektleri_dinlet() -> None:
    """Tum gecis seslerini ornek dosya olarak uretir."""
    from utils import ses_efekti

    klasor = config.SFX_DIR / "ornekler"
    klasor.mkdir(parents=True, exist_ok=True)

    logger.baslik("GECIS SESI ORNEKLERI")
    for ad in ses_efekti.EFEKTLER:
        yol = ses_efekti.uret(ad, klasor / f"{ad}.wav", tepe=0.6)
        print(f"    {ad:9} -> {yol.name}")

    print()
    logger.ok(f"Ornekler burada: {klasor}")
    logger.bilgi(
        "Dosyalari dinle, begendigini sec ve config.py icinde ayarla:\n"
        '    SFX_TIPI = "marimba"\n'
        "Sonra assets/sfx/gecis.wav dosyasini SIL (yenisi uretilsin) ve\n"
        "    python main.py --montaj son"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="YouTube cocuk videosu otomasyonu")
    p.add_argument("--tip", choices=["shorts", "uzun"], help="Uretilecek video tipi")
    p.add_argument("--adet", type=int, default=1, help="Kac adet uretilecek")
    p.add_argument("--gunluk", action="store_true",
                   help="Gunluk plani calistir (2 shorts + 2 uzun)")
    p.add_argument("--mock", action="store_true",
                   help="API kullanmadan sahte veriyle test et")
    p.add_argument("--senaryo-only", action="store_true",
                   help="Sadece fikir ve senaryo uret, gorsel uretme")
    p.add_argument("--devam", metavar="KLASOR",
                   help="Yarim kalan projeyi tamamla (klasor adi veya 'son')")
    p.add_argument("--yenile", metavar="KLASOR",
                   help="Tek bir gorseli yeniden uret (--sahne ile birlikte)")
    p.add_argument("--sahne", type=int, metavar="NO",
                   help="--yenile ile yeniden uretilecek sahne numarasi")
    p.add_argument("--sesler", action="store_true",
                   help="Kullanilabilir Turkce sesleri listele")
    p.add_argument("--efektler", action="store_true",
                   help="Gecis sesi orneklerini uret (dinleyip secmek icin)")
    p.add_argument("--ton-dene", action="store_true",
                   help="Ses tonu orneklerini uret (dinleyip secmek icin)")
    p.add_argument("--cumle", metavar="METIN", default="",
                   help="--ton-dene ile seslendirilecek ozel cumle")
    p.add_argument("--montaj", metavar="KLASOR",
                   help="Videoyu yeniden olustur (klasor adi veya 'son')")
    p.add_argument("--yukle", metavar="KLASOR",
                   help="Projeyi YouTube'a yukle (klasor adi veya 'son')")
    p.add_argument("--youtube-giris", action="store_true",
                   help="YouTube yetkilendirmesi yap (tek seferlik)")
    p.add_argument("--youtube-cikis", action="store_true",
                   help="Kayitli izni sil (baska hesaba gecmek icin)")
    p.add_argument("--yukle-otomatik", action="store_true",
                   help="Uretim bitince videoyu otomatik yukle")
    args = p.parse_args()

    if args.youtube_cikis:
        try:
            step6_yukle.cikis_yap()
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.youtube_giris:
        try:
            step6_yukle.giris_yap()
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.yukle:
        try:
            videoyu_yukle(args.yukle)
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.montaj:
        try:
            sadece_montaj(args.montaj)
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.ton_dene:
        try:
            step4_ses.tonlari_dene(args.cumle)
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.efektler:
        try:
            efektleri_dinlet()
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.sesler:
        try:
            if config.SES_MOTORU == "gemini":
                from utils import gemini_ses
                gemini_ses.sesleri_listele()
                return 0
            step4_ses.turkce_sesleri_listele()
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(f"Ses listesi alinamadi: {e}")
            return 1

    if args.yenile:
        if not args.sahne:
            logger.hata("--yenile ile birlikte --sahne NO vermelisin.")
            logger.bilgi("Ornek: python main.py --yenile PROJE_KLASORU --sahne 4")
            return 1
        try:
            gorsel_yenile(args.yenile, args.sahne)
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.devam:
        try:
            projeye_devam(args.devam)
            return 0
        except Exception as e:                        # noqa: BLE001
            logger.hata(str(e))
            return 1

    if args.mock:
        config.MOCK = True

    if not args.gunluk and not args.tip:
        p.print_help()
        return 1

    gorevler = []
    if args.gunluk:
        for tip, adet in config.GUNLUK_PLAN.items():
            gorevler += [tip] * adet
    else:
        gorevler = [args.tip] * args.adet

    logger.baslik(f"{len(gorevler)} video projesi uretilecek")

    basarili, basarisiz = [], []
    for i, tip in enumerate(gorevler, 1):
        print(f"\n\033[1m### {i}/{len(gorevler)} ###\033[0m")
        try:
            basarili.append(tek_video(
                tip,
                atla_gorsel=args.senaryo_only,
                yukle=args.yukle_otomatik,
            ))
        except Exception as e:                    # noqa: BLE001
            logger.hata(f"Proje basarisiz: {e}")
            traceback.print_exc()
            basarisiz.append((tip, str(e)))

    logger.baslik("OZET")
    logger.ok(f"Basarili: {len(basarili)}")
    for yol in basarili:
        print(f"   → {yol}")
    if basarisiz:
        logger.hata(f"Basarisiz: {len(basarisiz)}")
        for tip, hata in basarisiz:
            print(f"   → {tip}: {hata}")

    # Kismi basari hata sayilmaz: en az bir video uretildiyse islem basarilidir.
    if basarili:
        if basarisiz:
            logger.uyari(
                f"{len(basarisiz)} video uretilemedi ama {len(basarili)} tanesi "
                "hazir. Islem basarili sayiliyor."
            )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
