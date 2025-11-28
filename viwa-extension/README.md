# Viwa - WhatsApp Web Assistant

Viwa, WhatsApp Web deneyiminizi geliştiren güçlü bir Chrome uzantısıdır.

## Özellikler

- **📊 İstatistikler**: Mesaj ve resim sayılarını takip edin
- **🖼️ Resim Önizleme**: WhatsApp Web'deki resimleri otomatik algıla ve işaretle
- **💾 Otomatik Kaydet**: Resimleri otomatik kaydetme seçeneği
- **⚡ Hafif ve Hızlı**: Minimal performans etkisi
- **🔒 Gizlilik**: Tüm veriler yerel olarak saklanır

## Kurulum

### Chrome Web Store'dan (Yakında)
Uzantı henüz Chrome Web Store'da yayınlanmadı.

### Manuel Kurulum (Geliştirici Modu)

1. Bu repoyu klonlayın veya ZIP olarak indirin
2. Chrome tarayıcınızı açın
3. Adres çubuğuna `chrome://extensions/` yazın
4. Sağ üst köşeden "Geliştirici modu"nu aktif edin
5. "Paketlenmemiş öğe yükle" butonuna tıklayın
6. `viwa-extension` klasörünü seçin
7. Uzantı yüklendi! WhatsApp Web'e gidin ve kullanmaya başlayın

## Kullanım

1. Chrome'da uzantı ikonuna tıklayın
2. İstediğiniz özellikleri aktif edin
3. WhatsApp Web'e gidin (web.whatsapp.com)
4. Uzantı otomatik olarak çalışmaya başlayacak

## İstatistikler

Viwa, WhatsApp Web'deki mesajlarınızı ve resimlerinizi sayar ve size anlık istatistikler sunar. Tüm veriler tarayıcınızda yerel olarak saklanır, hiçbir veri dışarı gönderilmez.

## Resim Algılama

HTML kodlarınızı paylaştığınızda, Viwa otomatik olarak WhatsApp Web'deki resim seçicilerini (selectors) çıkaracak ve optimize edecektir.

### Resim Seçicilerini Güncelleme

`scripts/content.js` dosyasındaki `imageSelectors` dizisini güncelleyebilirsiniz:

\`\`\`javascript
const imageSelectors = [
  'img[src*="blob:"]',
  'img[src*="web.whatsapp.com"]',
  'div[data-testid="image-thumb"]',
  // Buraya yeni seçiciler ekleyin
];
\`\`\`

## Geliştirme

### Proje Yapısı

\`\`\`
viwa-extension/
├── manifest.json           # Uzantı yapılandırması (Manifest V3)
├── popup.html             # Popup arayüzü
├── scripts/
│   ├── popup.js          # Popup mantığı
│   ├── content.js        # WhatsApp Web'e inject edilen script
│   └── background.js     # Arka plan service worker
├── styles/
│   ├── popup.css         # Popup stilleri
│   └── content.css       # WhatsApp Web için stiller
├── icons/
│   ├── icon16.png
│   ├── icon32.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
\`\`\`

### Teknolojiler

- Chrome Extension Manifest V3
- Vanilla JavaScript (ES6+)
- CSS3
- Chrome Storage API
- Chrome Runtime API

## Katkıda Bulunma

1. Bu repoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## İletişim

Sorularınız veya önerileriniz için issue açabilirsiniz.

## Yasal Uyarı

Bu uzantı resmi bir WhatsApp ürünü değildir. WhatsApp'ın kullanım koşullarına uygun şekilde kullanılmalıdır.

---

**Viwa ile WhatsApp Web deneyiminizi geliştirin! 🚀**
