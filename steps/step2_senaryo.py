# -*- coding: utf-8 -*-
"""
ADIM 2 - SENARYO URETIMI
Fikri alir; baslik, aciklama, etiketler ve sahne sahne senaryo uretir.
Her sahnenin hem Turkce seslendirme metni hem Ingilizce gorsel promptu olur.
"""
import random
import re
from typing import Any, Dict, List

import config
from utils import ai, logger

# Cocuk icerigine girmemesi gereken kelime kokleri.
# Kelime siniri (\b) ile aranir, boylece "kan" kelimesi "kanat" icinde eslesmez
# ve "oldu" gibi masum kelimeler "oldu"/"olum" ile karistirilmaz.
# Tarih icerigi olum, savas gibi kavramlari dogal olarak icerir; bunlar
# yasak degil. Asil riskimiz YouTube politikalarina takilmak ve uydurma bilgi.

# Politika riski: siddet detayi, cinsellik, nefret soylemi
RISKLI_KALIPLAR = [
    r"iskence", r"tecavuz", r"soykirim", r"katliam",
    r"idam sahnesi", r"kan revan", r"parcalanmi",
    r"cinsel", r"ciplak",
]

# Uydurma riski: kesin sayi ve tarih iddialari kontrol edilmeli
KESINLIK_KALIPLARI = [
    r"\btam \d",              # "tam 3472 kisi"
    r"\b\d{1,2} (ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)\b",
    r"\bilk kez\b", r"\btarihte ilk\b", r"\bdunyanin ilk\b",
    r"\bkesinlikle\b", r"\bhic suphesiz\b", r"\bkanitlanmis\b",
]

_SAPKA = str.maketrans("cgiosuai", "cgiosuai")
_SAPKA = str.maketrans("çğıöşüâî", "cgiosuai")

HAREKETLER = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]

SISTEM = """Sen yetiskinler icin tarih videosu senaryosu yazan bir uzmansin.

KANAL: {kanal_adi}
TANIM: {kanal_tanimi}

GOREVIN: Verilen fikri, sahne sahne bir video senaryosuna cevirmek.

DOGRULUK KURALLARI (en onemlisi):
- SADECE emin oldugun, genel kabul gormus bilgileri anlat.
- Uydurma tarih, uydurma isim, uydurma sayi KESINLIKLE YASAK.
- KESIN GUN/AY TARIHI YASAK. "12 Mart 1453'te" YAZMA.
  Bunun yerine: "15. yuzyilin ortalarinda", "1450'lerde", "Fatih doneminde".
  Sadece yuzyil veya on yil belirt.
- KESIN SAYI YASAK. "tam 3.472 kisi" YAZMA. "binlerce kisi" yaz.
- "ILK / EN / TEK" IDDIASI YASAK. Su ifadeleri KULLANMA:
    "dunyanin ilk", "tarihte ilk", "ilk kez", "en eski", "en buyuk",
    "tek ornek", "kesinlikle", "hic suphesiz", "kanitlanmistir"
  Bunlar tartismali iddialardir ve yanlis cikma ihtimali yuksektir.
  Bunun yerine soyle yaz:
    YANLIS: "Catali ilk kez Bizanslilar kullandi."
    DOGRU : "Catal, Bizans saraylarinda kullanilan bir aracti."
    YANLIS: "Dunyanin en eski tarifi buydu."
    DOGRU : "Bilinen eski tariflerden biri buydu."
- Bir seyin "yaygınlasmasi", "bilinen ornekleri", "kullanildigi donem"
  gibi ifadeler guvenlidir; "ilk" iddiasi degildir.
- Tartismali konularda "bazi kaynaklara gore", "arastirmacilarin cogu"
  gibi ifadeler kullan.
- Bir sey bilinmiyorsa bilinmedigini soyle; bosluk doldurmak icin uydurma.

ANLATIM METNI KURALLARI (Turkce):
- Yetiskin izleyici icin, akici ve anlasilir Turkce.
- Ders verir gibi degil; ilginc bir sey anlatan bir arkadas gibi.
- Kisa ve orta uzunlukta cumleler karisik kullan; monoton olmasin.
- Agir akademik dil kullanma, ama basitlestirip yanlis da anlatma.
- Cinsel icerik, siddet detayi, iskence tasviri YASAK.
- Guncel siyaset, dini tartisma, etnik catisma konularina GIRME.

ILK SAHNE -- EN KRITIK KISIM:
Izleyicilerin cogu ilk 3 saniyede kaydirip geciyor. Ilk sahne bunu engellemeli.
- Ilk cumle EN FAZLA 10 KELIME olsun. Kisa, vurucu, net.
- Selamlama YAPMA. "Merhaba", "hos geldiniz", "bugun sizlerle" YASAK.
- Aciklama ile baslama. Once carpici iddiayi at, aciklamayi sonra yap.
- Su uc kalıptan birini kullan:
    (a) Sasirtici iddia:  "Ortacagda kimse sabaha kadar uyumazdi."
    (b) Izleyiciyi icine alan soru:  "Gece uyanip bir daha uyuyamiyor musun?"
    (c) Beklentiyi bozma:  "Sekiz saatlik uyku sandigindan cok daha yeni."
- MERAK BOSLUGU BIRAK: cevabin varligini duyur ama cevabi verme.
    YANLIS: "Ortacagda insanlar iki kez uyurdu cunku elektrik yoktu."
    DOGRU : "Ortacagda gece ikiye bolunurdu. Sebebi cok mantikli."
- Ikinci sahnede de cevabi tam verme; once konunun ilginc yanini derinlestir.

SABIT FORMAT KIMLIGI:
Izleyicinin kanali tanimasi icin her video benzer bir tonda olmali.
- Anlatimda bir yerde "gecmiste", "o donemde", "eskiden" gibi zaman capasi
  gecsin; izleyici hangi kanalda oldugunu hissetsin.
- Kapanista kanalin ne yaptigini bir kez hatirlat (tarihin bilinmeyen tarafi).

SON SAHNE -- ABONE CAGRISI:
- Once konuyu tek cumleyle topla.
- Sonra abone olmak icin SOMUT bir sebep sun. Sadece "abone ol" deme.
    DOGRU : "Her gun tarihten boyle bir detay paylasiyoruz. Abone ol."
    DOGRU : "Gecmisin bilinmeyen tarafi icin takipte kal."
    YANLIS: "Abone olmayi ve begenmeyi unutmayin."   (herkes bunu diyor, etkisiz)
- Kisa tut. Kapanis 12 kelimeyi gecmesin.

GORSEL KURALLARI (Ingilizce yaz):
- Gorseller STOK FOTOGRAF arsivinden secilecek, yapay zeka uretmeyecek.
  Bu yuzden prompt bir TARIF degil, bir ARAMA TERIMI gibi olmali.
- Somut, fotograflanabilir bir sahne yaz. Soyut kavram yazma.
    DOGRU : "airplane parked at airport terminal"
    YANLIS: "the concept of aerodynamic efficiency"
- Kisa tut: 3-6 kelime yeterli. Uzun cumle arama sonucunu bozar.
- Ilk kelimeler en onemlisi; asil konuyu basa yaz.
- Stok arsivde BULUNABILECEK seyler iste: insanlar, hayvanlar, doga,
  sehirler, nesneler, mekanlar, is ortamlari.
- Arsivde BULUNMAYACAK seyleri isteme: belirli tarihi olaylar, hayali
  yaratiklar, cok ozel anlar. Bunlarin yerine temsili bir sahne yaz.
    Ornek: "Ortacagda uyku" konusu icin -> "candle in dark room"
- Stil, isik, cekim acisi YAZMA. Arama motoru bunlari anlamaz.
- Ardisik sahnelerde FARKLI nesneler/mekanlar iste; ayni terimi tekrarlama.

BASLIK KURALLARI (cok onemli -- tiklanmayi bu belirliyor):
- Merak boslugu yarat: konuyu belli et ama cevabi verme.
    YANLIS: "Ucaklar Beyazdir Cunku Isigi Yansitir"   (cevap baslikta, tiklama gerekmez)
    DOGRU : "Ucaklarin Beyaz Olmasinin Gercek Sebebi"
- Su kaliplar iyi calisir:
    "... Olmasinin Gercek Sebebi"
    "Kimse ...  Fark Etmiyor"
    "... Sandigin Gibi Degil"
    "Neden ...? Cevap Sasirtici"
- 45-60 karakter arasi tut. Telefonda uzun basliklar kesiliyor.
- BUYUK HARFLE BAGIRMA, asiri emoji kullanma. En fazla bir emoji.
- Clickbait yapma: baslikta soyledigin sey videoda gercekten olmali.

Cevabini SADECE su JSON formatinda ver, baska hicbir sey yazma:
{{
  "baslik": "YouTube basligi, 70 karakteri gecmesin, merak uyandirsin",
  "aciklama": "YouTube aciklamasi. 3-4 cumle tanitim, sonra bos satir, sonra 5 hashtag.",
  "etiketler": ["10", "adet", "turkce", "youtube", "etiketi"],
  "karakter_sayfasi": "",
  "sahneler": [
    {{
      "no": 1,
      "anlatim": "Bu sahnede seslendirilecek Turkce metin",
      "karakter_sahnede": false,
      "gorsel_prompt": "English search term, 3-6 words, concrete photographable subject"
    }}
  ]
}}"""

ISTEK = """FIKIR
Konu: {konu}
Hedef yas: {hedef_yas}
Ozet: {ozet}
Ana mesaj: {mesaj}

FORMAT
Video tipi: {tip_ad} ({en_boy})
Hedef sure: yaklasik {sure} saniye
Sahne sayisi: TAM OLARAK {sahne_min} ile {sahne_max} arasinda olsun
Her sahnenin anlatim metni: {kelime_min}-{kelime_max} kelime

Simdi senaryoyu yaz."""

MOCK_SENARYO = {
    "baslik": "Sekiz Saatlik Uyku Sandığından Çok Daha Yeni",
    "aciklama": "Elektrikten önce gece ikiye bölünürdü. İnsanlar birinci uykudan "
                "sonra saatlerce uyanık kalır, sonra ikinci uykuya dalardı. "
                "Peki bu alışkanlık neden kayboldu?\n\n"
                "#tarih #ortaçağ #meraklıtarih #gündelikhayat #tarihibilgiler",
    "etiketler": ["tarih", "ortaçağ", "uyku", "günlük hayat tarihi",
                  "meraklı tarih", "tarihi bilgiler", "ilginç tarih",
                  "sanayi devrimi", "belgesel", "tarih kanalı"],
    "karakter_sayfasi": "",
    "sahneler": [
        {"no": 1, "karakter_sahnede": False,
         "anlatim": "Ortaçağda kimse sabaha kadar uyumazdı.",
         "gorsel_prompt": "a dark medieval bedroom lit only by moonlight through "
                          "a small window, empty wooden bed with rough blankets, "
                          "quiet atmosphere, wide shot"},
        {"no": 2, "karakter_sahnede": False,
         "anlatim": "Elektrik yokken geceler bugünkünden çok daha uzundu. "
                    "İnsanlar karanlık çökünce yatağa girerdi.",
         "gorsel_prompt": "a medieval village at dusk, small houses with faint "
                          "candlelight in windows, dirt path, deep blue evening "
                          "sky, wide establishing shot"},
        {"no": 3, "karakter_sahnede": False,
         "anlatim": "Birkaç saat sonra kendiliğinden uyanırlardı. Buna birinci "
                    "uyku denirdi.",
         "gorsel_prompt": "interior of a peasant cottage at night, a single "
                          "candle burning on a wooden table, warm dim light, "
                          "medium shot"},
        {"no": 4, "karakter_sahnede": False,
         "anlatim": "Bu ara sürede sohbet eder, dua eder, hatta komşuya "
                    "gidip iş konuşurlardı.",
         "gorsel_prompt": "two people sitting by a fireplace at night wrapped "
                          "in blankets, talking quietly, warm orange firelight, "
                          "close-up shot"},
        {"no": 5, "karakter_sahnede": False,
         "anlatim": "Sonra ikinci uykuya dalar, sabaha kadar uyurlardı.",
         "gorsel_prompt": "peaceful medieval bedroom before dawn, faint blue "
                          "light entering, blankets in soft folds, overhead shot"},
        {"no": 6, "karakter_sahnede": False,
         "anlatim": "Sanayi devrimiyle yapay ışık geldi ve bu alışkanlık unutuldu. "
                    "Geçmişin bilinmeyen tarafı için abone ol.",
         "gorsel_prompt": "a 19th century factory street at night lit by gas "
                          "lamps, people walking, industrial buildings, "
                          "atmospheric wide shot"},
    ],
}


# ------------------------------------------------------------------ kontroller
# Anlatimda gecerse gorselle celisme riski olan sayi kelimeleri
SAYI_KELIMELERI = [
    "iki", "üç", "uc", "dört", "dort", "beş", "bes", "altı", "alti",
    "yedi", "sekiz", "dokuz", "on tane", "ikisi", "üçü", "ucu", "dördü",
]


RENKLER = ["kırmızı", "sarı", "mavi", "yeşil", "turuncu", "mor", "pembe",
           "siyah", "beyaz", "kahverengi", "gri", "kirmizi", "sari", "yesil"]


def _benzerlik_kontrol(hamlar: List[tuple]) -> List[str]:
    """Ardisik UC sahnede de ayni nesne/mekan geciyorsa uyarir.

    Ayni goruntuyu farkli kelimelerle tarif edince kelime ortusme orani
    dusuk cikiyor; bu yuzden tekrar eden ikili kelime obeklerini ariyoruz.
    """
    def obekler(metin: str) -> set:
        kelimeler = re.findall(r"[a-z]{3,}", metin.lower())
        return {f"{a} {b}" for a, b in zip(kelimeler, kelimeler[1:])}

    GURULTU = {"soft", "warm", "bright", "gentle", "light", "lighting", "shot",
               "background", "sunlight", "atmosphere", "colorful", "view",
               "dark", "dim", "faint", "wide", "close"}

    uyarilar = []
    for i in range(len(hamlar) - 2):
        ucler = hamlar[i:i + 3]
        ortak = obekler(ucler[0][1]) & obekler(ucler[1][1]) & obekler(ucler[2][1])
        ortak = {o for o in ortak if not set(o.split()) & GURULTU}
        if ortak:
            nolar = "-".join(str(n) for n, _ in ucler)
            uyarilar.append(f"sahne {nolar} (hepsinde '{sorted(ortak)[0]}' var)")
    return uyarilar



# Ilk sahnede olmamasi gerekenler: izleyiciyi kaydirtan kaliplar
ZAYIF_ACILIS = [
    r"^merhaba", r"^selam", r"^hos ?geldin", r"^bugun sizlerle",
    r"^bu videoda", r"^herkese merhaba", r"^sevgili", r"^degerli",
    r"^kanalimiza", r"^videomuza",
]

# Kapanista etkisiz kalip
ZAYIF_KAPANIS = [
    r"abone olmayi ve begenmeyi unutmayin",
    r"begenmeyi ve abone olmayi unutmayin",
    r"kanalimiza abone olmayi unutmayin",
]


def _acilis_kontrol(sahneler: List[Dict[str, Any]]) -> List[str]:
    """Ilk sahnenin izleyiciyi tutacak guclukte olup olmadigini kontrol eder.

    Izleyicilerin cogu ilk 3 saniyede karar veriyor; zayif bir acilis
    videonun izlenme suresini dogrudan dusuruyor.
    """
    if not sahneler:
        return []

    uyarilar = []
    ilk = sahneler[0]["anlatim"].strip()
    sade = ilk.lower().translate(_SAPKA)

    for kalip in ZAYIF_ACILIS:
        if re.search(kalip, sade):
            uyarilar.append(f"zayif acilis: '{ilk[:35]}...'")
            break

    # Ilk cumle cok uzunsa vurucu degildir
    ilk_cumle = re.split(r"(?<=[.!?])\s", ilk)[0]
    kelime = len(ilk_cumle.split())
    if kelime > 13:
        uyarilar.append(f"ilk cumle cok uzun ({kelime} kelime, hedef 10)")

    return uyarilar


def _kapanis_kontrol(sahneler: List[Dict[str, Any]]) -> List[str]:
    """Kapanista somut bir abone sebebi var mi?"""
    if not sahneler:
        return []
    son = sahneler[-1]["anlatim"].lower().translate(_SAPKA)
    for kalip in ZAYIF_KAPANIS:
        if re.search(kalip, son):
            return ["kapanis etkisiz kalip kullaniyor"]
    return []


def _risk_kontrol(senaryo: Dict[str, Any]) -> List[str]:
    """YouTube politikalarina takilabilecek ifadeleri arar."""
    parcalar = [s.get("anlatim", "") for s in senaryo["sahneler"]]
    parcalar += [senaryo.get("baslik", ""), senaryo.get("aciklama", "")]
    metin = " ".join(parcalar).lower().translate(_SAPKA)

    bulunanlar = []
    for kalip in RISKLI_KALIPLAR:
        e = re.search(rf"\b{kalip}\w*", metin, flags=re.UNICODE)
        if e:
            bulunanlar.append(e.group(0))
    return sorted(set(bulunanlar))


def _kesinlik_kontrol(sahneler: List[Dict[str, Any]]) -> List[str]:
    """Dogrulanmasi gereken kesin iddialari isaretler.

    Yapay zeka tarih ve sayilari uydurmaya cok musait. Bu kontrol hatayi
    duzeltmez ama nereye bakman gerektigini soyler.
    """
    bulunanlar = []
    for sahne in sahneler:
        metin = sahne["anlatim"].lower().translate(_SAPKA)
        for kalip in KESINLIK_KALIPLARI:
            e = re.search(kalip, metin, flags=re.UNICODE)
            if e:
                bulunanlar.append(f"sahne {sahne['no']}: '{e.group(0).strip()}'")
                break
    return bulunanlar


def _yil_kontrol(sahneler: List[Dict[str, Any]]) -> List[str]:
    """Metinde gecen yillari listeler (dogrulaman icin)."""
    yillar = []
    for sahne in sahneler:
        for e in re.finditer(r"\b(1\d{3}|20[0-2]\d)\b", sahne["anlatim"]):
            yillar.append(f"sahne {sahne['no']}: {e.group(0)}")
    return yillar


def _temizle(metin: str) -> str:
    """Seslendirme icin metni duzeltir."""
    metin = re.sub(r"\s+", " ", metin).strip()
    metin = metin.replace("...", "…")
    # Cumle sonunda noktalama yoksa nokta ekle
    if metin and metin[-1] not in ".!?…":
        metin += "."
    return metin


# Model kurali unutup stil kelimesi yazarsa temizlemek icin
STIL_KALIPLARI = [
    r"\b3d\s+(render|animation|cartoon)(\s+style)?\b",
    r"\b(children'?s?\s+)?(book\s+)?illustration(\s+style)?\b",
    r"\bcartoon\s+style\b",
    r"\bdigital\s+art\b",
    r"\bstorybook(\s+style|\s+look)?\b",
    r"\bpixar\s+style\b",
    r"\banimation\s+style\b",
    r"\bvertical\s+composition\b",
    r"\bhigh\s+quality\b",
    r"\b4k\b", r"\b8k\b",
]


def _prompt_temizle(prompt: str) -> str:
    """Stil kelimelerini ve fazla noktalama isaretlerini ayiklar."""
    for kalip in STIL_KALIPLARI:
        prompt = re.sub(kalip, "", prompt, flags=re.IGNORECASE)
    prompt = re.sub(r"\s*[.,]\s*(?=[.,])", "", prompt)   # ",," -> ","
    prompt = re.sub(r"\s+", " ", prompt)
    prompt = re.sub(r"^[\s,.]+|[\s,.]+$", "", prompt)
    return prompt


# ------------------------------------------------------------------ ana fonksiyon
def senaryo_uret(fikir: Dict[str, Any]) -> Dict[str, Any]:
    video_tipi = fikir["video_tipi"]
    profil = config.VIDEO_TIPLERI[video_tipi]
    s_min, s_max = profil["sahne_sayisi"]
    k_min, k_max = profil["sahne_kelime"]

    logger.bilgi(f"Senaryo yaziliyor... ({s_min}-{s_max} sahne)")

    sistem = SISTEM.format(
        kanal_adi=config.KANAL_ADI, kanal_tanimi=config.KANAL_TANIMI
    )
    istek = ISTEK.format(
        konu=fikir["konu"],
        hedef_yas=fikir.get("hedef_yas", "3-8"),
        ozet=fikir["ozet"],
        mesaj=fikir["mesaj"],
        tip_ad=profil["ad"],
        en_boy=profil["en_boy"],
        sure=profil["hedef_saniye"],
        sahne_min=s_min, sahne_max=s_max,
        kelime_min=k_min, kelime_max=k_max,
    )

    senaryo = ai.sor(sistem, istek, sicaklik=0.85, mock_cevap=MOCK_SENARYO)

    # --- yapisal dogrulama
    if not senaryo.get("sahneler"):
        raise ai.AIHatasi("Senaryoda sahne yok.")
    if not senaryo.get("baslik"):
        raise ai.AIHatasi("Senaryoda baslik yok.")

    sahne_sayisi = len(senaryo["sahneler"])
    if not (s_min - 2 <= sahne_sayisi <= s_max + 4):
        logger.uyari(
            f"Sahne sayisi beklenenin disinda: {sahne_sayisi} "
            f"(beklenen {s_min}-{s_max}). Yine de devam ediliyor."
        )

    # --- politika riski kontrolu
    bulunanlar = _risk_kontrol(senaryo)
    if bulunanlar:
        logger.uyari(
            f"YouTube politikasi acisindan riskli ifadeler: {bulunanlar}. "
            "Yuklemeden once kontrol et."
        )
        senaryo["_uyari"] = bulunanlar

    # --- sahneleri normalize et
    stil = config.GORSEL_STIL
    kompozisyon = profil.get("kompozisyon", "")
    karakter = (senaryo.get("karakter_sayfasi") or "").strip().rstrip(".,")

    temiz_sahneler = []
    ham_promptlar = []          # benzerlik kontrolu icin (karakter/stil eki haric)
    onceki_hareket = None

    for i, sahne in enumerate(senaryo["sahneler"], start=1):
        anlatim = _temizle(str(sahne.get("anlatim", "")))
        prompt = _prompt_temizle(str(sahne.get("gorsel_prompt", "")))

        if not anlatim or not prompt:
            logger.uyari(f"Sahne {i} eksik, atlaniyor.")
            continue

        # Karakter tarifi SADECE o sahnede karakter varsa eklenir.
        # Alan hic yoksa guvenli varsayim: ilk sahne haric karakter vardir.
        ham_promptlar.append((i, prompt))   # enjeksiyondan ONCEKI hali

        karakter_var = bool(sahne.get("karakter_sahnede", i > 1))
        # Iki poz: ayni sahne, farkli durus. Aralarinda gecis yapilarak
        # karakter hareket ediyormus gibi gorunecek.
        poz_1 = str(sahne.get("poz_1", "")).strip().rstrip(".,")
        poz_2 = str(sahne.get("poz_2", "")).strip().rstrip(".,")

        def tam_prompt(poz: str) -> str:
            # Stok fotograf modunda stil/kompozisyon eki arama sonucunu bozar
            if config.GORSEL_KAYNAGI == "pexels":
                return prompt
            p = prompt
            if karakter and karakter_var:
                bas = f"{karakter}, consistent character design"
                p = f"{bas}, {poz}, {p}" if poz else f"{bas}, {p}"
            if kompozisyon:
                p = f"{p}, {kompozisyon}"
            return f"{p}, {stil}"

        prompt_1 = tam_prompt(poz_1)
        prompt_2 = tam_prompt(poz_2) if (karakter_var and poz_2 and poz_1 != poz_2) else ""

        # Ayni kamera hareketi arka arkaya gelmesin
        secenekler = [h for h in HAREKETLER if h != onceki_hareket]
        hareket = random.choice(secenekler)
        onceki_hareket = hareket

        kayit = {
            "no": i,
            "anlatim": anlatim,
            "karakter_sahnede": karakter_var,
            "gorsel_prompt": prompt_1,
            "hareket": hareket,
        }
        if config.IKI_KARE and prompt_2:
            kayit["gorsel_prompt_2"] = prompt_2
        temiz_sahneler.append(kayit)

    senaryo["sahneler"] = temiz_sahneler
    senaryo["baslik"] = senaryo["baslik"].strip()[:95]

    # Etiketler
    etiketler = senaryo.get("etiketler") or fikir.get("anahtar_kelimeler", [])
    senaryo["etiketler"] = [str(e).strip() for e in etiketler][:15]

    # Meta bilgiler
    senaryo["video_tipi"] = video_tipi
    senaryo["genislik"] = profil["genislik"]
    senaryo["yukseklik"] = profil["yukseklik"]
    senaryo["fikir"] = fikir

    toplam_kelime = sum(len(s["anlatim"].split()) for s in temiz_sahneler)
    tahmini_sure = round(toplam_kelime / config.KELIME_HIZI)

    # Riskli iddialari otomatik yumusat (elle kontrol yukunu azaltir)
    from utils import iddia
    iddia.yumusat(senaryo)

    # Acilis ve kapanis gucu -- izlenme suresini en cok bunlar etkiliyor
    zayif = _acilis_kontrol(temiz_sahneler) + _kapanis_kontrol(temiz_sahneler)
    if zayif:
        for z in zayif:
            logger.uyari(f"IZLENME RISKI -> {z}")
        senaryo["_acilis_uyarisi"] = zayif

    # Yumusatmadan SONRA kalan kesin iddialari bildir
    kesin = _kesinlik_kontrol(temiz_sahneler)
    if kesin:
        logger.uyari("Yumusatmaya ragmen kalan kesin iddialar:")
        for k in kesin:
            logger.uyari(f"    {k}")
        senaryo["_kesinlik_uyarisi"] = kesin

    # Metinde gecen yillar
    yillar = _yil_kontrol(temiz_sahneler)
    if yillar:
        logger.bilgi("Metinde gecen yillar (dogrulaman icin): " + ", ".join(yillar))
        senaryo["_yillar"] = yillar

    # Ardisik sahneler birbirine cok mu benziyor?
    benzer = _benzerlik_kontrol(ham_promptlar)
    if benzer:
        logger.uyari("Benzer gorunecek ardisik sahneler: " + ", ".join(benzer))
        senaryo["_benzerlik_uyarisi"] = benzer

    senaryo["tahmini_sure_sn"] = tahmini_sure
    senaryo["toplam_kelime"] = toplam_kelime

    logger.ok(
        f"Senaryo hazir: {len(temiz_sahneler)} sahne, "
        f"{toplam_kelime} kelime, ~{tahmini_sure} sn"
    )
    return senaryo
