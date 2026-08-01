# YouTube Video Otomasyonu — Kurulum Rehberi

> Bu rehber kodlama bilmeyen biri için yazıldı. Sırayla takip et, atlama.
> Şu an **Adım 1 (fikir)** ve **Adım 2 (senaryo)** hazır. Diğerleri sırada.

---

## 1. Python kurulumu (5 dakika)

1. https://www.python.org/downloads/ adresine git
2. Sarı **"Download Python"** butonuna bas
3. İndirilen dosyayı çalıştır
4. ⚠️ **ÇOK ÖNEMLİ:** İlk ekranda en altta **"Add Python to PATH"** kutucuğunu işaretle. Bunu unutursan hiçbir şey çalışmaz.
5. "Install Now" > bitince "Close"

**Kontrol:** Başlat menüsüne `cmd` yazıp Komut İstemi'ni aç, şunu yaz:

```
python --version
```

`Python 3.12.x` gibi bir yazı görmelisin. Görmüyorsan Python'u kaldırıp 4. adıma dikkat ederek tekrar kur.

---

## 2. Projeyi bilgisayarına koy

1. `youtube_otomasyon` klasörünü indir
2. Kolay ulaşacağın bir yere koy. Örneğin: `C:\youtube_otomasyon`

---

## 3. Gerekli paketleri kur (2 dakika)

Komut İstemi'ni aç ve şunları **tek tek** yaz (her satırdan sonra Enter):

```
cd C:\youtube_otomasyon
pip install -r requirements.txt
```

Alt alta yazılar akar, sonunda `Successfully installed...` görürsen tamam.

---

## 4. Ücretsiz Gemini API anahtarı al (3 dakika)

1. https://aistudio.google.com/apikey adresine git
2. Google hesabınla giriş yap
3. **"Create API key"** butonuna bas
4. **"Create API key in new project"** seç
5. Çıkan uzun yazıyı (`AIza...` ile başlar) **kopyala**

> Bu tamamen ücretsiz. Kredi kartı istemiyor. Günlük limiti bizim 4 videomuz için fazlasıyla yeterli.

---

## 5. Anahtarı projeye tanıt

1. `youtube_otomasyon` klasöründeki **`.env.example`** dosyasını bul
2. Üzerine sağ tıkla > **Kopyala**, sonra aynı klasöre **Yapıştır**
3. Kopyanın adını **`.env`** olarak değiştir (başındaki nokta dahil, uzantı yok)
4. Not Defteri ile aç, şu satırı bul:

```
GEMINI_API_KEY=buraya_anahtarini_yapistir
```

5. `buraya_anahtarini_yapistir` yazan yeri sil, kopyaladığın anahtarı yapıştır. Şöyle olmalı:

```
GEMINI_API_KEY=AIzaSyD...uzunbirşeyler
```

6. Kaydet ve kapat.

> **Windows dosya adını `.env.txt` yapıyorsa:** Dosya Gezgini > Görünüm > "Dosya adı uzantıları" kutucuğunu işaretle, sonra `.txt` kısmını sil.

---

## 6. İlk testi yap

### A) Önce internetsiz test (anahtar doğru mu diye uğraşmadan)

```
cd C:\youtube_otomasyon
python main.py --tip shorts --mock
```

Renkli yazılar akmalı ve sonunda `Basarili: 1` yazmalı. Bu, kurulumun sağlam olduğunu gösterir.

### B) Şimdi gerçek test

```
python main.py --tip shorts
```

Yapay zeka gerçekten bir fikir ve senaryo üretecek.

### C) Uzun video testi

```
python main.py --tip uzun
```

### D) Günlük plan (2 shorts + 2 uzun)

```
python main.py --gunluk
```

---

## 7. Sonuçlara nereden bakacaksın

`output` klasörüne gir. Her video için bir klasör oluşur:

```
output/
└── 20260726_143022_shorts_gokkusaginin_kayip_renkleri/
    ├── senaryo.json               ← programın kullandığı dosya (sen açma)
    ├── senaryo_okunabilir.txt     ← ✅ SEN BUNU OKU
    ├── gorseller/                 (adım 3'te dolacak)
    └── ses/                       (adım 4'te dolacak)
```

**`senaryo_okunabilir.txt`** dosyasını Not Defteri ile aç. İçinde başlık, açıklama, etiketler ve sahne sahne senaryo var.

---

## Bana ne şekilde geri bildirim vermelisin

Test ederken şunlara bak ve bana yaz:

1. **Hata aldın mı?** Kırmızı yazının tamamını kopyalayıp bana yapıştır.
2. **Senaryo kalitesi nasıl?** Çocuk için uygun mu, sıkıcı mı, doğal mı?
3. **Sahne sayısı ve süre mantıklı mı?** (Shorts ~45 sn, uzun ~4 dk hedefliyoruz)
4. **Görsel promptları** sence o sahneyi anlatıyor mu?
5. **Sarı uyarı** çıktı mı? ("riskli kelimeler var" diye)

En faydalısı: 2-3 tane çalıştırıp `senaryo_okunabilir.txt` dosyalarından birini bana olduğu gibi yapıştırman.

---

## Sık karşılaşılan hatalar

| Hata | Anlamı | Çözüm |
|---|---|---|
| `'python' is not recognized` | Python PATH'e eklenmemiş | Python'u kaldır, "Add to PATH" işaretleyerek tekrar kur |
| `GEMINI_API_KEY bulunamadi` | `.env` yok veya adı yanlış | Adım 5'i tekrar yap, dosya adı tam olarak `.env` olmalı |
| `HTTP 400` | Anahtar hatalı kopyalanmış | Anahtarı tekrar kopyala, başında/sonunda boşluk olmasın |
| `HTTP 429` | Günlük ücretsiz kota doldu | Birkaç saat bekle |
| `ModuleNotFoundError: requests` | Paketler kurulmamış | Adım 3'ü tekrar yap |

---

## Sırada ne var

- [x] **Adım 1** — İçerik fikri
- [x] **Adım 2** — Senaryo + başlık + açıklama + görsel promptları
- [ ] **Adım 3** — Görsel üretimi (Pollinations)
- [ ] **Adım 4** — Türkçe seslendirme (edge-tts)
- [ ] **Adım 5** — Montaj, hareket efekti, altyazı, müzik (FFmpeg)
- [ ] **Adım 6** — YouTube'a yükleme

Sen 1-2'yi test edip onaylayınca 3-4'e geçiyoruz.
