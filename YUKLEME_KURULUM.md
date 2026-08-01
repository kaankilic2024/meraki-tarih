# YouTube'a Yükleme — Kurulum Rehberi

> Tek seferlik, yaklaşık 10 dakika. Bir kez yaptıktan sonra bir daha uğraşmayacaksın.
> Sabırlı ol, Google'ın arayüzü kalabalık ama adımlar basit.

---

## Önce paketleri kur

```
python -m pip install -r requirements.txt
```

---

## 1. Google Cloud projesi oluştur

1. https://console.cloud.google.com/ adresine git, Google hesabınla giriş yap
2. Sayfanın en üstünde, "Google Cloud" yazısının yanındaki **proje seçici**ye tıkla
3. Açılan pencerede sağ üstteki **"Yeni Proje"** butonuna bas
4. Proje adı: `youtube-otomasyon` yaz, **Oluştur**'a bas
5. Birkaç saniye sonra bildirim gelir. Proje seçiciden **yeni projeyi seç** (bu önemli, yanlış projede çalışırsan hiçbir şey olmaz)

---

## 2. YouTube API'sini aç

1. Sol üstteki ☰ menüden **"API'ler ve Hizmetler"** > **"Kitaplık"**
2. Arama kutusuna `YouTube Data API v3` yaz
3. Çıkan sonuca tıkla, mavi **"Etkinleştir"** butonuna bas

---

## 3. İzin ekranını ayarla

1. Sol menüden **"API'ler ve Hizmetler"** > **"OAuth izin ekranı"**
2. Kullanıcı türü: **"Harici" (External)** seç, **Oluştur**
3. Formu doldur:
   - Uygulama adı: `YouTube Otomasyon`
   - Kullanıcı destek e-postası: kendi e-postanı seç
   - Geliştirici iletişim bilgileri (en altta): kendi e-postanı yaz
4. **Kaydet ve Devam Et**
5. "Kapsamlar" ekranı: hiçbir şey yapma, **Kaydet ve Devam Et**
6. "Test kullanıcıları" ekranı: **"+ ADD USERS"** > kendi e-postanı ekle > **Kaydet ve Devam Et**
7. Özet ekranında **"Panoya Dön"**

### ⚠️ Önemli: Haftalık giriş sorununu şimdi çöz

Uygulama "Test" modunda kalırsa izin **7 günde bir sona erer** ve her hafta yeniden giriş yapman gerekir.

Bunu önlemek için OAuth izin ekranında **"UYGULAMAYI YAYINLA" (PUBLISH APP)** butonuna bas ve onayla.

"Doğrulanmamış uygulama" uyarısı görebilirsin — kendi kanalın için kendi uygulamanı kullandığından bu sorun değil. Giriş yaparken çıkan "Google bu uygulamayı doğrulamadı" ekranında **"Gelişmiş"** > **"...adlı uygulamaya git (güvenli değil)"** diyeceksin.

---

## 4. OAuth kimlik bilgisi oluştur

1. Sol menüden **"API'ler ve Hizmetler"** > **"Kimlik Bilgileri"**
2. Üstteki **"+ KİMLİK BİLGİSİ OLUŞTUR"** > **"OAuth istemci kimliği"**
3. Uygulama türü: **"Masaüstü uygulaması"** seç
4. Ad: `otomasyon` yaz, **Oluştur**
5. Açılan pencerede **"JSON'U İNDİR"** butonuna bas
6. İnen dosyanın adını **`client_secret.json`** olarak değiştir
7. Bu dosyayı proje klasöründeki **`data`** klasörüne koy:

```
youtube_otomasyon/
└── data/
    └── client_secret.json     ← buraya
```

> 🔒 Bu dosyayı kimseyle paylaşma, GitHub'a yükleme.

---

## 5. Yetkilendirmeyi yap

```
python main.py --youtube-giris
```

Ne olacak:
1. Tarayıcı otomatik açılır
2. Google hesabını seç (**videoların yükleneceği kanalın hesabı**)
3. "Doğrulanmadı" uyarısı çıkarsa: **Gelişmiş** > **...uygulamaya git**
4. İzin listesini onayla
5. Tarayıcıda "The authentication flow has completed" yazısını gör, sekmeyi kapat

Konsolda **"Bagli kanal: KANAL_ADIN"** yazısını görürsen tamamdır.

---

## 6. İlk yüklemeyi yap

Hazır bir projeyi yükle:

```
python main.py --yukle PROJE_KLASORU
```

Ya da baştan üretip yükle:

```
python main.py --tip shorts --yukle-otomatik
```

---

## Bilmen gereken 3 şey

### Videolar özel (private) yüklenir
Bu bilinçli. YouTube Studio'dan izleyip beğenirsen yayına alırsın. Varsayılanı değiştirmek istersen `config.py` içinde:
```python
YOUTUBE_GIZLILIK = "private"   # "public" veya "unlisted" yapabilirsin
```

### ⚠️ Denetim kısıtı
YouTube, denetimden geçmemiş API projelerinden yüklenen videoları **özel olarak kilitleyebilir**. Yani Studio'dan bile herkese açık yapamayabilirsin.

Böyle bir durumla karşılaşırsan YouTube'un API denetim başvurusunu doldurman gerekir:
https://support.google.com/youtube/contact/yt_api_form

Onaya kadar geçici çözüm: videoyu klasörden alıp YouTube Studio'ya elle yükle. Başlık, açıklama ve etiketler `senaryo_okunabilir.txt` dosyasında hazır bekliyor, kopyala yapıştır yeter.

### Günlük limit
API kotası günde 10.000 birim, bir yükleme 1.600 birim harcıyor. Yani **günde en fazla 6 video**. Senin planın 4 video olduğu için sorun yok.

---

## Sık karşılaşılan hatalar

| Hata | Çözüm |
|---|---|
| `OAuth dosyasi bulunamadi` | `client_secret.json` dosyası `data` klasöründe değil |
| `access_denied` | İzin ekranında kendini "Test kullanıcısı" olarak eklemedin |
| `quotaExceeded` | Günlük 6 yükleme hakkın doldu, yarın devam |
| `The request metadata is invalid` | Başlık veya açıklama çok uzun (kod bunu kırpıyor, olmamalı) |
| Her hafta tekrar giriş isteniyor | Adım 3'teki "Uygulamayı Yayınla" işlemini yapmadın |
| `invalid_grant` | İzin bozulmuş. `data/youtube_token.json` dosyasını sil, tekrar giriş yap |
