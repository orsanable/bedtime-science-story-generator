# Bilim Günü Demo — Sahne Akışı

## Demo öncesi (5 dk)

1. Terminali ve tarayıcıyı yan yana aç (Win+sol/sağ ok)
2. Terminalde proje klasörüne gir, çalıştır: `python serve.py`
3. Tarayıcıda aç: `http://localhost:8000`
4. Claude Code'u terminalde başlat: `claude`
5. Yazı puntolarını büyüt — terminalde Ctrl++ , tarayıcıda Ctrl++
6. **Anthropic API anahtarını** hazır tut (story step için lazım olacak)

## Çocuklara açılış (1 dk)

> "Bugün size bilgisayara nasıl konuştuğumu göstereceğim. Bu siyah ekran terminal — burada bilgisayarla yazışıyorum. Bu beyaz ekran ise bizim hikaye sayfamız. Şimdi siz bana ne istediğinizi söyleyin, ben Claude'a yazayım, beraber yapalım!"

## Önerilen prompt sırası (her biri 30-60 saniye)

Çocuklar bağırdıkça bu komutları yazarsın. Sıra önemli değil — onların heyecanına uy.

### 1. Renk değişikliği (en hızlı "vay!" anı)
```
Arka planı pembe yap, başlığı mor yap.
```
> Sayfa anında değişir → kahkahalar.

### 2. İlk karakter butonu
```
"Prenses" yazılı büyük bir buton ekle. Tıklayınca alttaki kutuya
"Bir varmış bir yokmuş, cesur bir prenses varmış..." yazsın.
```

### 3. Daha çok karakter — çocuklar sırayla bağırsın
```
Süper Kahraman, Ejderha, Astronot, Korsan, Robot ve Tek Boynuzlu At
butonlarını da ekle. Her butonun farklı renk olsun.
```
> Her karakter butonu için ayrı bir başlangıç cümlesi yazdır.

### 4. Çocuğun adını ekle
> Bir çocuğun ismini sor — "Elif" diyelim.
```
"Elif" adında yeni bir buton ekle, rengi sarı olsun. Tıklayınca
"Elif bugün bilim insanı olmuş..." yazsın.
```

### 5. Emoji yağmuru (çıldırırlar)
```
Her butona uygun bir emoji ekle. Prenses'e taç, Ejderha'ya alev,
Astronot'a roket gibi.
```

### 6. Ses efekti
```
Butonlara tıklayınca kısa bir "ding" sesi çıksın.
```

### 7. Hikaye motoru — ASIL OLAY
```
Üstte "Bilim Konusu" seçimi olsun (Uzay, Hayvanlar, Vücut, Hava).
Bir karakter ve bir konu seçilince "Hikayeyi Yaz!" butonu ortaya çıksın.
Tıklayınca POST /api/story endpoint'ine fetch atsın, body'de
{character, topic, name} olsun. Yanıt SSE (text/event-stream)
formatında gelir — Anthropic'in streaming yanıtı. content_block_delta
event'lerindeki text parçalarını ekrana harf harf yazdır.
```
> API anahtarı `serve.py` üzerinden gidiyor, çocuklar göremiyor.

### 8. Resim ekle — BÜYÜK FİNAL
```
"Hikayeyi Yaz!" butonuna basınca aynı anda iki istek gitsin:
biri /api/story (zaten var), diğeri POST /api/image, body'de aynı
{character, topic, name}. Hikaye sol tarafta yazılırken sağda
büyük bir kare alan olsun, içinde "Çiziliyor..." yazısı ve
zıplayan emojiler. /api/image yanıtı gelince ({url: "..."})
o kareye <img> olarak yerleştir.
```
> İki istek paralel — hikaye hemen akmaya başlar, resim 3-8 sn sonra patlar.

**Eğer resim çok yavaşsa veya hata verirse:** Çocuklara "Bilgisayar düşünüyor, biz hikayeyi okuyalım" de ve devam et. Resim hiç gelmese bile demo akar.

### 9. Final süslemeler (vakit kalırsa)
```
- Hikaye yazılırken üstte konfeti efekti olsun
- Hikaye bitince "Tekrar yaz" ve "Yeni karakter seç" butonları çıksın
- Yazı tipi daha çocuksu olsun (Comic Sans veya benzeri)
- Sayfanın altında dönen küçük yıldızlar olsun
```

## Demo sonrası

- Auto-reload script'ini sil (`index.html` içindeki `<script>` bloğu)
- Çocuklarla beraber yazılan son halini ekran görüntüsü al
- API anahtarını sıfırla / sil

## Notlar / kurtarma

- **Auto-reload çalışmazsa:** F5'e bas, devam et. Drama yapma.
- **Claude yanlış bir şey yazarsa:** "Bunu geri al" de, çocuklara "Claude bazen yanılır, biz düzeltiriz" de — öğretici an.
- **API hata verirse:** Önceden hazırladığın 2-3 hikayeyi yedekte tut, kopyala-yapıştır oku.
- **Çocuk uygunsuz bir şey isterse:** "Bunu yapamayız ama ____ yapabiliriz" diye yönlendir.

## Yedek karakter listesi (ilham için)
Prenses, Süper Kahraman, Ejderha, Astronot, Korsan, Robot, Tek Boynuzlu At,
Cadı, Şövalye, Peri, Sihirbaz, Bilim İnsanı, Dedektif, Dinozor, Uzaylı, Köpek
