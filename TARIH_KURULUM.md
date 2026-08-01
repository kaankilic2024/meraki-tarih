# Meraklı Tarih — Kurulum Notu

> Bu proje, çocuk kanalı otomasyonunun tarih içeriğine uyarlanmış hâli.
> Kod aynı, ayarlar ve senaryo kuralları farklı.

---

## Çocuk projesinden farklar

| | Çocuk kanalı | Meraklı Tarih |
|---|---|---|
| Ses tonu | `canli` (Emel, +10%, +18Hz) | `belgesel` (Ahmet, -3%, -2Hz) |
| Geçiş sesi | `chime` | `whoosh` |
| Görsel stili | Yumuşak 3D çizgi film | Tarihsel dijital resim |
| Altyazı | Büyük, 3 kelime | Küçük, 5 kelime |
| Çocuk işareti | Var (COPPA) | Yok |
| Çalışma saati | 08:00 | 11:00 |

Saatler bilerek farklı — ikisi aynı anda çalışırsa Gemini kotası çakışır.

---

## Kurulum sırası

### 1. Klasörü yerleştir
`tarih_otomasyon` klasörünü çocuk projesinin **yanına** koy, içine değil.

```
Projeler\
├── youtube_otomasyon\      (çocuk kanalı)
└── tarih_otomasyon\        (bu proje)
```

### 2. Müzik ekle
`assets/music` klasörü boş. Tarih içeriğine uygun müzik lazım — çocuk kanalının
neşeli parçaları burada yakışmaz.

YouTube Studio > Ses Kitaplığı'ndan şu türlerde ara: *ambient*, *cinematic*,
*documentary*, *calm*. 3-5 parça yeterli.

### 3. `.env` dosyası oluştur
Çocuk projesindeki `.env` dosyasını kopyalayıp buraya yapıştır. Aynı Gemini
anahtarı iki projede de çalışır.

> ⚠️ Günlük kota ikiye bölünür. İki kanal birden günde 8 video üretiyorsa
> sınıra yaklaşırsın. Sorun çıkarsa ikinci bir Google hesabından ayrı anahtar al.

### 4. YouTube yetkilendirmesi
Bu **yeni kanal için ayrı** yapılmalı:

```
python main.py --youtube-giris
```

Tarayıcı açılınca **Meraklı Tarih kanalını** seç. Yanlış kanalı seçersen
videolar çocuk kanalına gider.

> Google Cloud'da yeni proje açmana gerek yok, `cocuk-video` projesi ikisi
> için de çalışır. Sadece `data/client_secret.json` dosyasını çocuk
> projesinden buraya kopyala.

### 5. İlk deneme

```
python main.py --tip shorts
```

Üretilen `senaryo_okunabilir.txt` dosyasını **mutlaka oku**. Tarih içeriğinde
en büyük risk uydurma bilgi.

### 6. GitHub kurulumu
Çocuk projesindeki `GITHUB_KURULUM.md` adımlarının aynısı, tek farkla:
**ayrı bir depo** oluştur (`meraklı-tarih` gibi). Secrets'ı yeniden eklemen
gerekir, çünkü YouTube token'ı farklı.

---

## Tarih içeriğine özel kontroller

Kod, senaryo üretirken şunları uyarı olarak bildiriyor:

**Kesin iddialar** — "tam 3472 kişi", "12 Mart 1453", "tarihte ilk kez" gibi
ifadeler yakalanır. Bunlar yapay zekanın en çok uydurduğu şeyler.

**Yıllar** — Metinde geçen tüm yıllar listelenir, doğrulaman için.

**Politika riski** — İşkence, cinsellik gibi YouTube'un kısıtladığı ifadeler.
Savaş ve ölüm gibi tarih için normal kelimeler işaretlenmez.

---

## ⚠️ Bunu ciddiye al

Yapay zeka tarih konusunda **emin bir dille yanlış bilgi üretir.** Çocuk
masalında bu önemsizdi; tarih kanalında değil.

- İlk aylarda her videoyu yayınlamadan önce oku
- Uyarı verilen kesin iddiaları hızlıca aratıp doğrula
- Şüphelendiğin videoyu silmekten çekinme

Bir kanalın güveni yavaş kazanılır, tek bir yanlış videoyla sarsılır.
Yorumlarda düzeltilmek de kanala zarar verir.

Bu yüzden `config.py` içinde şu ayarı bir süre böyle bırakmanı öneriyorum:

```python
YOUTUBE_GIZLILIK = "private"
```

Kontrol ettikçe elle yayına alırsın. Kaliteden emin olunca `public` yaparsın.
