# 🛸 İHA Görev ve Uçuş Kontrol Yazılımı (UAV Mission & Flight Control)

Nesne yönelimli programlama (OOP) prensiplerine, **SOLID** ilkelerine ve beş temel **Gang of Four (GoF)** tasarım kalıbına dayanan, modüler ve etkileşimli **İHA Görev ve Uçuş Kontrol Simülasyon Yazılımı**.

> **Not:** Bu proje tamamen eğitim ve yazılım mimarisi simülasyonu amaçlıdır. Gerçek uçuş kontrolü, gerçek sensör bağlantıları veya fiziksel silah sistemleri kullanılmaz; tüm veriler sentetik olarak üretilir.

---

## 🎯 Uygulanan GoF Tasarım Kalıpları

| Kalıp | Kategori | Çözülen Problem | Temel Sınıflar |
|---|---|---|---|
| **Builder** | Yaratımsal (Creational) | Farklı görev profilleri için İHA yapılandırması, MTOW (Maksimum Kalkış Ağırlığı) ve bileşen uyumluluğu doğrulaması | `UAVConfigurationBuilder`, `StrikeUAVBuilder`, `ReconUAVBuilder`, `MissionPrepDirector`, `UAVPlatform` |
| **Adapter** | Yapısal (Structural) | Farklı metot imzalarına ve veri yapılarına sahip harici sensörlerin ortak bir arayüzle görev bilgisayarına bağlanması | `TargetSensor`, `StanagRadarAdapter`, `ThermalCameraAdapter`, `LegacyStanagRadarSDK`, `VendorThermalDevice`, `MissionComputer` |
| **Decorator** | Yapısal (Structural) | Telemetri kanalına çalışma zamanında dinamik olarak şifreleme, sıkıştırma ve hata düzeltme katmanlarının eklenip çıkarılması | `TelemetryChannel`, `BaseRadioChannel`, `TelemetryChannelDecorator`, `AesEncryptionDecorator`, `CompressionDecorator`, `AntiJammingDecorator` |
| **State** | Davranışsal (Behavioral) | İHA'nın uçuş fazlarına göre kabul ettiği komutların, motor/irtifa tepkisinin ve acil durum (Failsafe) geçişlerinin yönetimi | `FlightController`, `FlightPhaseState`, `PreflightIdleState`, `TakeOffState`, `CruiseState`, `CombatState`, `EmergencyReturnState` |
| **Strategy** | Davranışsal (Behavioral) | 2B sentetik harita üzerinde en kısa yol, kısıtlı bölgelerden kaçınma ve bölge tarama (loitering) algoritmaları arasında dinamik geçiş | `NavigationSystem`, `RoutePlanningStrategy`, `ShortestPathStrategy`, `RadarEvasionStrategy`, `LoiteringSearchStrategy` |

---

## 📂 Proje Klasör Yapısı

```text
uav-mission-control/
├── app.py                      # Streamlit ana uygulama giriş noktası
├── requirements.txt            # Python bağımlılıkları
├── README.md                   # Proje genel dokümantasyonu
├── .gitignore                  # Git hariç tutma kuralları
├── project_requirements.pdf    # Proje gereksinim belgesi
├── src/
│   ├── models/                 # Veri modelleri (dataclasses)
│   ├── patterns/
│   │   ├── builder/            # Aşama 2: Builder kalıbı
│   │   ├── adapter/            # Aşama 3: Adapter kalıbı
│   │   ├── decorator/          # Aşama 4: Decorator kalıbı
│   │   ├── state/              # Aşama 5: State kalıbı
│   │   └── strategy/           # Aşama 6: Strategy kalıbı
│   ├── simulation/             # Simülasyon orkestrasyon bileşenleri
│   ├── services/               # Uygulama servis katmanı
│   └── utils/                  # Merkezi olay günlüğü (logger) ve yardımcılar
├── ui/
│   ├── pages/                  # Streamlit simülasyon ekranları
│   └── components/             # Yeniden kullanılabilir grafik ve UI bileşenleri
├── tests/                      # Pytest birim ve entegrasyon testleri
├── docs/
│   └── architecture_and_uml.md # Mimari analiz ve Mermaid UML diyagramları
└── assets/                     # Statik medya ve görsel kaynaklar
```

---

## ⚙️ Kurulum ve Çalıştırma

### 1. Sanal Ortamın Oluşturulması ve Bağımlılıkların Yüklenmesi

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Uygulamanın Çalıştırılması

```powershell
streamlit run app.py
```

### 3. Testlerin Çalıştırılması

```powershell
pytest -v
```

---

## 🗺️ Geliştirme Aşamaları Durumu

- [x] **Aşama 1 — Proje analizi ve mimari**
- [x] **Aşama 2 — Builder Kalıbı (İHA Yapılandırması)**
- [ ] **Aşama 3 — Adapter Kalıbı (Sensör Entegrasyonu)**
- [ ] **Aşama 4 — Decorator Kalıbı (Telemetri Katmanları)**
- [ ] **Aşama 5 — State Kalıbı (Uçuş Fazları)**
- [ ] **Aşama 6 — Strategy Kalıbı (Navigasyon Algoritmaları)**
- [ ] **Aşama 7 — Görsel Arayüz (Streamlit + Plotly)**
- [ ] **Aşama 8 — Test ve Dokümantasyon**
