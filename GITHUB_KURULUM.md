# Bilgisayarsız Otomasyon — GitHub Actions Kurulumu

> Bundan sonra videolar GitHub'ın sunucusunda üretilecek. Bilgisayarın kapalı olsa da
> her sabah çalışacak. Tek seferlik kurulum, yaklaşık 20 dakika.

---

## Önce bir karar: depo açık mı kapalı mı?

| | Özel (private) | Herkese açık (public) |
|---|---|---|
| Ücretsiz süre | 2000 dakika/ay | **Sınırsız** |
| Günde 4 video | ~2250 dk/ay — **yetmez** | Sorun yok |
| Kodu kimler görür | Sadece sen | Herkes |
| API anahtarların | Şifreli, güvenli | Şifreli, güvenli |

**Öneri: herkese açık yap.** Kodda gizli bir şey yok; anahtarlar koda değil GitHub'ın
şifreli "Secrets" bölümüne konuyor ve orada kalıyor.

Özel kalsın istersen `config.py` içindeki `GUNLUK_PLAN` değerini düşür:
```python
GUNLUK_PLAN = {"shorts": 1, "uzun": 1}
```

---

## 1. Projeyi GitHub'a yükle

Proje klasöründe (PowerShell):

```
git init
git add .
git commit -m "YouTube otomasyonu"
```

⚠️ **Yüklemeden önce kontrol et:**

```
git status
```

Listede `.env`, `client_secret.json` veya `youtube_token.json` **görünmemeli**.
Görünüyorsa dur ve bana yaz — `.gitignore` çalışmıyor demektir.

Sonra GitHub'da yeni bir depo oluştur (github.com > New repository), adını
`youtube-otomasyon` koy ve ekranda çıkan iki satırı çalıştır:

```
git remote add origin https://github.com/KULLANICI_ADIN/youtube-otomasyon.git
git push -u origin main
```

---

## 2. Gizli bilgileri GitHub'a tanıt

GitHub'da deponun sayfasına git:
**Settings** > sol menüde **Secrets and variables** > **Actions**

**"New repository secret"** ile üç tane ekle:

### `GEMINI_API_KEY`
`.env` dosyandaki anahtarın (AQ. ile başlayan uzun yazı).

### `YOUTUBE_TOKEN_JSON`
`data/youtube_token.json` dosyasını Not Defteri ile aç, **içeriğinin tamamını**
kopyala yapıştır. `{` ile başlayıp `}` ile biten tek satırlık bir metin.

### `YOUTUBE_CLIENT_SECRET_JSON`
`data/client_secret.json` dosyasının içeriğinin tamamı.

> Bu üçü GitHub'da şifreli saklanır, sen dahil kimse bir daha göremez, kayıtlarda
> görünmez. Depon herkese açık olsa bile güvendedir.

---

## 3. Ayarları tanıt (isteğe bağlı)

Aynı sayfada **Variables** sekmesine geç, **"New repository variable"**:

| İsim | Örnek değer | Ne işe yarar |
|---|---|---|
| `SES_TONU` | `canli` | Seslendirme tonu |
| `SFX_TIPI` | `marimba` | Geçiş sesi |
| `YOUTUBE_GIZLILIK` | `public` | Yayın durumu |

Eklemezsen `config.py`'deki varsayılanlar kullanılır.

---

## 4. Müziği depoya ekle

`assets/music` klasöründeki mp3'ler GitHub'a yüklenmeli, yoksa videolar müziksiz çıkar.
`.gitignore` bunu zaten izin verecek şekilde ayarlandı.

**Sadece telifsiz müzik koy** — depo herkese açıksa müzik dosyaları da görünür olur.

---

## 5. İlk denemeyi elle yap

1. GitHub'da deponun **Actions** sekmesine git
2. Sol menüden **"Günlük Video Üretimi"**
3. Sağda **"Run workflow"** butonu
4. Açılan kutuda:
   - **Ne üretilsin?** → `shorts` (ilk denemede tek video yeter)
   - **YouTube'a yüklensin mi?** → önce `false` yap, sadece üretsin
5. Yeşil **"Run workflow"**

Birkaç saniye sonra çalışma listede belirir. Üzerine tıklayıp adımları canlı izleyebilirsin.

Bitince sayfanın altındaki **Artifacts** bölümünden `videolar-1` dosyasını indirip izle.

Her şey yolundaysa aynı işlemi `yukle: true` ile tekrarla.

---

## 6. Otomatiğe bırak

İlk deneme başarılıysa başka bir şey yapmana gerek yok. Her gün Türkiye saatiyle
**08:00** civarında kendiliğinden çalışacak.

Saati değiştirmek istersen `.github/workflows/gunluk_video.yml` dosyasında:

```yaml
    - cron: "0 5 * * *"     # UTC saati. TR = UTC + 3
```

Örnekler: `"0 3 * * *"` → TR 06:00, `"0 18 * * *"` → TR 21:00

---

## Bilmen gereken şeyler

**Zamanlama tam dakikasında çalışmaz.** GitHub yoğunluğa göre 5-30 dakika gecikebilir.
Bu normaldir.

**60 gün hiç işlem olmazsa zamanlama durur.** GitHub, kullanılmayan depolarda otomatik
görevleri kapatıyor. E-posta ile haber veriyor; Actions sekmesinden tek tıkla yeniden
açabilirsin.

**Hata olursa e-posta gelir.** Actions sekmesinden hangi adımda takıldığını görebilirsin.
Kırmızı adımın üzerine tıklayıp kayıtları bana gönderirsen çözeriz.

**Fikir geçmişi korunur.** Üretilen konular `data/fikir_gecmisi.json` dosyasına yazılıp
depoya geri gönderiliyor, böylece aynı konu tekrar üretilmiyor.

**Kendi bilgisayarında da çalışmaya devam edebilirsin.** Bu kurulum eskisini bozmuyor;
`python main.py --tip shorts` komutu hâlâ çalışır.

---

## Sık karşılaşılan hatalar

| Hata | Sebep | Çözüm |
|---|---|---|
| `GEMINI_API_KEY bulunamadi` | Secret eklenmemiş veya adı yanlış | Adım 2'yi kontrol et, isim birebir aynı olmalı |
| `Gecerli YouTube izni yok` | `YOUTUBE_TOKEN_JSON` eksik/bozuk | Dosya içeriğinin tamamını kopyaladığından emin ol |
| `invalid_grant` | İzin süresi dolmuş | Bilgisayarında `python main.py --youtube-giris` çalıştır, yeni token'ı secret olarak güncelle |
| Video müziksiz çıkıyor | `assets/music` boş veya yüklenmemiş | mp3'leri ekleyip `git push` yap |
| Altyazı görünmüyor/bozuk | Yazı tipi bulunamadı | İş akışı DejaVu Sans kuruyor, olmazsa bana yaz |
| `You have exceeded your quota` | Aylık Actions süresi bitti | Depoyu herkese açık yap veya günlük video sayısını düşür |
