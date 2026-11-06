# İHA Görev ve Uçuş Kontrol Yazılımı — Mimari Analiz ve UML Sınıf Diyagramları

> **Proje Kapsamı Notu:** Bu yazılım tamamen eğitim, yazılım mimarisi ve nesne yönelimli tasarım kalıpları (GoF) simülasyonu amaçlıdır. Gerçek uçuş kontrol donanımı, gerçek sensör bağlantısı, elektronik harp veya fiziksel silah sistemi içermez; tüm veriler sentetiktir.

---

## 1. Gereksinim Belgesi (`project_requirements.pdf`) Analizi

Proje gereksinim belgesinde savunma ve havacılık simülasyonu bağlamında beş temel yazılım tasarım problemi tanımlanmış ve her biri için bir **Gang of Four (GoF)** tasarım kalıbı eşleştirilmiştir:

| # | Problem Tanımı | GoF Grubu & Kalıp | Katılımcı Roller ve Zorunlu Sınıflar | Çözülen Mimari Sorun |
|---|---|---|---|---|
| **1** | **Karmaşık Nesne İnşası ve Doğrulama:** Görev profiline göre faydalı yük, temsili mühimmat/ekipman, yakıt ve haberleşme modüllerinin maksimum kalkış ağırlığı (MTOW) ve istasyon uyumluluk kısıtlarıyla doğrulanarak oluşturulması. | **Yaratımsal (Creational)**<br>**Builder** | - **Builder (ABC):** `UAVConfigurationBuilder`<br>- **ConcreteBuilder:** `StrikeUAVBuilder`, `ReconUAVBuilder`<br>- **Director:** `MissionPrepDirector`<br>- **Product:** `UAVPlatform` | Telescoping constructor (çok parametreli kurucu) karmaşasını önler; adım adım inşa ve son aşamada tutarlılık/ağırlık doğrulaması sağlar. |
| **2** | **Heterojen Sensör Entegrasyonu:** Farklı üreticilere ve protokollere ait (eski nesil STANAG radar SDK'sı ve harici termal kamera cihazı) sensörlerin farklı metot imzaları ve veri çıktılarının tek bir standart hedef verisi formatına dönüştürülmesi. | **Yapısal (Structural)**<br>**Adapter** | - **Target (ABC):** `TargetSensor`<br>- **Adapter:** `StanagRadarAdapter`, `ThermalCameraAdapter`<br>- **Adaptee:** `LegacyStanagRadarSDK`, `VendorThermalDevice`<br>- **Client:** `MissionComputer` | `MissionComputer` kodunu değiştirmeden (Open/Closed) ve `isinstance` kontrollerine başvurmadan yeni/uyumsuz sensörleri sisteme entegre eder. |
| **3** | **Dinamik Haberleşme Güvenliği:** YKİ ile İHA arasındaki telemetri paketlerine çalışma zamanında şifreleme (AES), sıkıştırma ve hata düzeltme/parazit koruma (CRC/FEC simülasyonu) katmanlarının istenilen sıra ve kombinasyonla eklenip çıkarılması. | **Yapısal (Structural)**<br>**Decorator** | - **Component (ABC):** `TelemetryChannel`<br>- **ConcreteComponent:** `BaseRadioChannel`<br>- **Decorator (ABC):** `TelemetryChannelDecorator`<br>- **ConcreteDecorator:** `AesEncryptionDecorator`, `CompressionDecorator`, `AntiJammingDecorator` | Kalıtım ile $2^3 = 8$ farklı alt sınıf oluşmasını (sınıf patlaması) engeller; çalışma zamanında nesne sarmalama (wrapping) zinciri kurar. |
| **4** | **Uçuş Fazına Bağlı Davranış Değişimi:** Yerde Bekleme, Kalkış, Seyir, Görev/Angajman ve Acil Eve Dönüş (Failsafe) fazlarında irtifa kontrolü, motor tepkisi ve geçerli komutların tamamen değişmesi. | **Davranışsal (Behavioral)**<br>**State** | - **Context:** `FlightController`<br>- **State (ABC):** `FlightPhaseState`<br>- **ConcreteState:** `PreflightIdleState`, `TakeOffState`, `CruiseState`, `CombatState`, `EmergencyReturnState` | `FlightController` içindeki devasa `if-elif-else` bloklarını ortadan kaldırır; her uçuş fazının kurallarını kendi sınıfında kapsüller. |
| **5** | **Değişken Güdüm ve Rota Algoritmaları:** Uçuş sırasında kısıtlı bölge tehdidi veya yakıt durumuna göre En Kısa Rota, Kısıtlı Bölgeden Kaçınma ve Bölge Tarama (Loitering) algoritmaları arasında çalışma zamanında geçiş yapılması. | **Davranışsal (Behavioral)**<br>**Strategy** | - **Context:** `NavigationSystem`<br>- **Strategy (ABC):** `RoutePlanningStrategy`<br>- **ConcreteStrategy:** `ShortestPathStrategy`, `RadarEvasionStrategy`, `LoiteringSearchStrategy` | Rota hesaplama algoritmalarını `NavigationSystem`'den soyutlar; çalışma zamanında dinamik algoritma değişimi ve yeni strateji ekleme kolaylığı sağlar. |

---

## 2. Yazılım Mimarisi Değerlendirmesi ve SOLID Prensipleri

Uygulama, **İş Mantığı (Core Domain & Patterns)** ile **Sunum Katmanı (Streamlit UI)** birbirinden tamamen bağımsız olacak şekilde katmanlı mimariyle tasarlanmıştır:

1. **`src/models/`**: Kalıplar arasında taşınan değiştirilemez veya tip güvenli veri yapıları (`dataclass` tabanlı telemetri paketleri, koordinatlar, sensör okumaları, bileşen modelleri).
2. **`src/patterns/`**: Beş GoF tasarım kalıbının birbirinden izole alt paketleri (`builder`, `adapter`, `decorator`, `state`, `strategy`). Hiçbir kalıp sınıfı `streamlit` veya `plotly` kütüphanesine bağımlı değildir.
3. **`src/simulation/` & `src/services/`**: Beş kalıbı uçtan uca bir görev senaryosunda birleştiren orkestrasyon katmanı.
4. **`src/utils/`**: Merkezi olay günlüğü (`MissionEventLogger`) ve yardımcı doğrulama araçları.
5. **`ui/`**: Yalnızca `src/` altındaki servis ve kalıp arayüzlerini çağıran, Plotly grafiklerini ve kullanıcı etkileşimlerini çizen Streamlit bileşenleri.

### Mimari Prensiplerin Karşılanması
- **Single Responsibility Principle (SRP):** Her uçuş fazı, her rota stratejisi, her telemetri katmanı ve her sensör adaptörü yalnızca tek bir sorumluluğa sahiptir.
- **Open/Closed Principle (OCP):** Yeni bir sensör (`TargetSensor`), yeni bir rota algoritması (`RoutePlanningStrategy`), yeni bir telemetri katmanı (`TelemetryChannelDecorator`) veya yeni bir İHA tipi (`UAVConfigurationBuilder`) eklendiğinde mevcut istemci sınıflar (`MissionComputer`, `NavigationSystem`, `FlightController`) değiştirilmez.
- **Dependency Inversion Principle (DIP):** Üst seviye modüller (`MissionComputer`, `NavigationSystem`, `FlightController`, `MissionPrepDirector`) somut sınıflara değil, `ABC` ile tanımlanmış soyut arayüzlere bağımlıdır.
- **Composition over Inheritance:** Kalıtım patlaması yerine nesne kompozisyonu (`Decorator` sarmalama zinciri, `Strategy` enjeksiyonu, `State` referansı, `Adapter` sarmalaması) kullanılır.

---

## 3. Beş Tasarım Kalıbı Arasındaki İlişkiler ve Görev Akışı

Beş tasarım kalıbı tek başına çalışabildiği gibi, bir İHA görev yaşam döngüsünde birbirini tamamlayan bir boru hattı (pipeline) oluşturur:

```mermaid
flowchart TD
    subgraph P1["1. Görev Hazırlık (BUILDER)"]
        Director["MissionPrepDirector"] --> Builder["UAVConfigurationBuilder"]
        Builder --> Platform["UAVPlatform (Doğrulanmış İHA)"]
    end

    subgraph P2["2. Uçuş Fazı Yönetimi (STATE)"]
        Platform --> FC["FlightController"]
        FC <--> State["FlightPhaseState (Idle -> TakeOff -> Cruise -> Combat / EmergencyReturn)"]
    end

    subgraph P3["3. Sensör Okuma (ADAPTER)"]
        RawSensors["LegacyStanagRadarSDK / VendorThermalDevice"] --> Adapters["StanagRadarAdapter / ThermalCameraAdapter"]
        Adapters --> MC["MissionComputer (Normalize Hedef Verisi)"]
    end

    subgraph P4["4. Rota ve Güdüm (STRATEGY)"]
        MC --> Nav["NavigationSystem"]
        FC --> Nav
        Nav <--> Strat["RoutePlanningStrategy (Shortest / RadarEvasion / Loitering)"]
    end

    subgraph P5["5. Haberleşme ve Telemetri (DECORATOR)"]
        FC --> Tel["BaseRadioChannel"]
        Nav --> Tel
        MC --> Tel
        Tel --> Dec["TelemetryChannelDecorator (Compression -> AES -> AntiJamming)"]
        Dec --> GCS["Yer Kontrol İstasyonu (YKİ Paneli)"]
    end
```

1. **Builder -> State & Strategy:** `UAVConfigurationBuilder` ile inşa edilen `UAVPlatform`, sahip olduğu sensör/yük kapasitesi ve maksimum yakıt/ağırlık değerleriyle `FlightController` ve `NavigationSystem` için başlangıç platform parametrelerini sağlar.
2. **Adapter -> Strategy & State:** `MissionComputer`, `TargetSensor` adaptörleri üzerinden normalize edilmiş çevresel hedef/tehdid verilerini okur. Bir kısıtlı bölge veya anomali algılandığında `NavigationSystem` çalışma zamanında `RadarEvasionStrategy`'ye geçebilir veya kritik durumda `FlightController` `EmergencyReturnState` fazını tetikleyebilir.
3. **State & Strategy -> Decorator:** `FlightController`'ın aktif uçuş fazı (`FlightPhaseState`) ve `NavigationSystem`'in ürettiği aktif rota/konum bilgileri bir telemetri mesajına dönüştürülür ve `TelemetryChannel` dekoratör zincirinden (`CompressionDecorator` -> `AesEncryptionDecorator` -> `AntiJammingDecorator`) geçirilerek Yer Kontrol İstasyonu'na iletilir.

---

## 4. UML Sınıf Diyagramı Taslakları

### 4.1. Builder Kalıbı (Yaratımsal)

```mermaid
classDiagram
    class UAVPlatform {
        +str model_name
        +str mission_type
        +str airframe_type
        +float max_takeoff_weight_kg
        +float empty_weight_kg
        +float fuel_weight_kg
        +list~str~ sensors
        +list~str~ payloads
        +str comms_module
        +total_weight_kg() float
        +validate() tuple~bool, list~str~~
    }

    class UAVConfigurationBuilder {
        <<abstract>>
        +reset()* None
        +set_airframe()* UAVConfigurationBuilder
        +set_fuel_capacity(fuel_kg: float)* UAVConfigurationBuilder
        +add_sensor(sensor_name: str)* UAVConfigurationBuilder
        +add_payload(payload_name: str)* UAVConfigurationBuilder
        +set_comms_module(comms_name: str)* UAVConfigurationBuilder
        +build()* UAVPlatform
    }

    class StrikeUAVBuilder {
        -UAVPlatform _platform
        +reset() None
        +set_airframe() StrikeUAVBuilder
        +set_fuel_capacity(fuel_kg: float) StrikeUAVBuilder
        +add_sensor(sensor_name: str) StrikeUAVBuilder
        +add_payload(payload_name: str) StrikeUAVBuilder
        +set_comms_module(comms_name: str) StrikeUAVBuilder
        +build() UAVPlatform
    }

    class ReconUAVBuilder {
        -UAVPlatform _platform
        +reset() None
        +set_airframe() ReconUAVBuilder
        +set_fuel_capacity(fuel_kg: float) ReconUAVBuilder
        +add_sensor(sensor_name: str) ReconUAVBuilder
        +add_payload(payload_name: str) ReconUAVBuilder
        +set_comms_module(comms_name: str) ReconUAVBuilder
        +build() UAVPlatform
    }

    class MissionPrepDirector {
        -UAVConfigurationBuilder _builder
        +set_builder(builder: UAVConfigurationBuilder) None
        +construct_standard_recon_uav() UAVPlatform
        +construct_long_range_strike_uav() UAVPlatform
    }

    MissionPrepDirector o-- UAVConfigurationBuilder : directs
    UAVConfigurationBuilder <|-- StrikeUAVBuilder
    UAVConfigurationBuilder <|-- ReconUAVBuilder
    StrikeUAVBuilder ..> UAVPlatform : builds & validates
    ReconUAVBuilder ..> UAVPlatform : builds & validates
```

---

### 4.2. Adapter Kalıbı (Yapısal)

```mermaid
classDiagram
    class TargetSensor {
        <<abstract>>
        +read_target_data()* TargetData
        +get_sensor_info()* dict
    }

    class LegacyStanagRadarSDK {
        +fetch_polar_blip_buffer() str
        +get_radar_status_code() int
    }

    class VendorThermalDevice {
        +capture_heat_signature_json() dict
    }

    class StanagRadarAdapter {
        -LegacyStanagRadarSDK _adaptee
        +read_target_data() TargetData
        +get_sensor_info() dict
    }

    class ThermalCameraAdapter {
        -VendorThermalDevice _adaptee
        +read_target_data() TargetData
        +get_sensor_info() dict
    }

    class MissionComputer {
        -list~TargetSensor~ _sensors
        +register_sensor(sensor: TargetSensor) None
        +collect_all_targets() list~TargetData~
    }

    MissionComputer --> TargetSensor : uses
    TargetSensor <|-- StanagRadarAdapter
    TargetSensor <|-- ThermalCameraAdapter
    StanagRadarAdapter --> LegacyStanagRadarSDK : adapts
    ThermalCameraAdapter --> VendorThermalDevice : adapts
```

---

### 4.3. Decorator Kalıbı (Yapısal)

```mermaid
classDiagram
    class TelemetryChannel {
        <<abstract>>
        +transmit(payload: str)* TelemetryPacketResult
        +get_pipeline_layers()* list~str~
    }

    class BaseRadioChannel {
        -str _frequency_band
        +transmit(payload: str) TelemetryPacketResult
        +get_pipeline_layers() list~str~
    }

    class TelemetryChannelDecorator {
        <<abstract>>
        #TelemetryChannel _wrapped_channel
        +transmit(payload: str) TelemetryPacketResult
        +get_pipeline_layers() list~str~
    }

    class AesEncryptionDecorator {
        -bytes _key
        +transmit(payload: str) TelemetryPacketResult
    }

    class CompressionDecorator {
        +transmit(payload: str) TelemetryPacketResult
    }

    class AntiJammingDecorator {
        +transmit(payload: str) TelemetryPacketResult
    }

    TelemetryChannel <|-- BaseRadioChannel
    TelemetryChannel <|-- TelemetryChannelDecorator
    TelemetryChannelDecorator o-- TelemetryChannel : wraps
    TelemetryChannelDecorator <|-- AesEncryptionDecorator
    TelemetryChannelDecorator <|-- CompressionDecorator
    TelemetryChannelDecorator <|-- AntiJammingDecorator
```

---

### 4.4. State Kalıbı (Davranışsal)

```mermaid
classDiagram
    class FlightController {
        -FlightPhaseState _state
        -float _altitude_m
        -float _speed_knots
        +transition_to(new_state: FlightPhaseState) None
        +execute_command(command: str) StateActionResult
        +trigger_emergency(reason: str) StateActionResult
        +get_allowed_commands() list~str~
    }

    class FlightPhaseState {
        <<abstract>>
        +phase_name()* str
        +allowed_commands()* list~str~
        +handle_command(controller: FlightController, command: str)* StateActionResult
        +on_emergency(controller: FlightController, reason: str)* StateActionResult
    }

    class PreflightIdleState {
        +handle_command(controller: FlightController, command: str) StateActionResult
    }

    class TakeOffState {
        +handle_command(controller: FlightController, command: str) StateActionResult
    }

    class CruiseState {
        +handle_command(controller: FlightController, command: str) StateActionResult
    }

    class CombatState {
        +handle_command(controller: FlightController, command: str) StateActionResult
    }

    class EmergencyReturnState {
        +handle_command(controller: FlightController, command: str) StateActionResult
    }

    FlightController o-- FlightPhaseState : current state
    FlightPhaseState <|-- PreflightIdleState
    FlightPhaseState <|-- TakeOffState
    FlightPhaseState <|-- CruiseState
    FlightPhaseState <|-- CombatState
    FlightPhaseState <|-- EmergencyReturnState
```

---

### 4.5. Strategy Kalıbı (Davranışsal)

```mermaid
classDiagram
    class NavigationSystem {
        -RoutePlanningStrategy _strategy
        +set_strategy(strategy: RoutePlanningStrategy) None
        +calculate_route(start: Point2D, destination: Point2D, restricted_zones: list~RestrictedZone~) RoutePlan
    }

    class RoutePlanningStrategy {
        <<abstract>>
        +strategy_name()* str
        +plan_route(start: Point2D, destination: Point2D, restricted_zones: list~RestrictedZone~)* RoutePlan
    }

    class ShortestPathStrategy {
        +plan_route(start: Point2D, destination: Point2D, restricted_zones: list~RestrictedZone~) RoutePlan
    }

    class RadarEvasionStrategy {
        +plan_route(start: Point2D, destination: Point2D, restricted_zones: list~RestrictedZone~) RoutePlan
    }

    class LoiteringSearchStrategy {
        +plan_route(start: Point2D, destination: Point2D, restricted_zones: list~RestrictedZone~) RoutePlan
    }

    NavigationSystem o-- RoutePlanningStrategy : active strategy
    RoutePlanningStrategy <|-- ShortestPathStrategy
    RoutePlanningStrategy <|-- RadarEvasionStrategy
    RoutePlanningStrategy <|-- LoiteringSearchStrategy
```

---

## 5. Mantıklı Geliştirme Sırası (Yol Haritası)

1. **Aşama 1 — Proje Analizi ve Mimari (Tamamlandı):** Gereksinim analizi, klasör yapısı, UML diyagramları, merkezi log altyapısı, minimal uygulama iskeleti ve duman testleri.
2. **Aşama 2 — Builder Kalıbı:** İHA platformu (`UAVPlatform`) veri modeli, `UAVConfigurationBuilder`, `StrikeUAVBuilder`, `ReconUAVBuilder`, `MissionPrepDirector`, ağırlık/uyumluluk doğrulamaları ve birim testleri. (Diğer modüllerin ihtiyaç duyduğu İHA nesnesini ürettiği için ilk sırada geliştirilir.)
3. **Aşama 3 — Adapter Kalıbı:** Sentetik sensörler (`LegacyStanagRadarSDK`, `VendorThermalDevice`), adaptörler (`StanagRadarAdapter`, `ThermalCameraAdapter`), `TargetSensor` arayüzü ve `MissionComputer` entegrasyonu + birim testleri.
4. **Aşama 4 — Decorator Kalıbı:** `TelemetryChannel`, `BaseRadioChannel`, `TelemetryChannelDecorator` ve `AesEncryptionDecorator` (Fernet/AES kütüphanesi ile dinamik anahtarlı), `CompressionDecorator` (zlib + base64), `AntiJammingDecorator` (temsili CRC/FEC paket koruma simülasyonu) + birim testleri.
5. **Aşama 5 — State Kalıbı:** `FlightController`, `FlightPhaseState` ve 5 uçuş fazı (`PreflightIdleState`, `TakeOffState`, `CruiseState`, `CombatState`, `EmergencyReturnState`) geçiş kuralları, geçersiz komut reddi ve acil durum (Failsafe) davranışları + birim testleri.
6. **Aşama 6 — Strategy Kalıbı:** 2B sentetik koordinat/kısıtlı bölge modelleri, `NavigationSystem`, `RoutePlanningStrategy` ve 3 algoritma (`ShortestPathStrategy`, `RadarEvasionStrategy`, `LoiteringSearchStrategy`) + rota karşılaştırma metrikleri ve birim testleri.
7. **Aşama 7 — Görsel Arayüz (Streamlit + Plotly):** Modern koyu temalı simülasyon kontrol paneli (7 ekran: Dashboard, UAV Configuration, Sensor Integration, Telemetry System, Flight Controller, Navigation, Design Patterns).
8. **Aşama 8 — Test ve Dokümantasyon:** Uçtan uca entegrasyon testleri, son dokümantasyon güncellemeleri ve sistem doğrulaması.
