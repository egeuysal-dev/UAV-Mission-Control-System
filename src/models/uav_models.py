"""
İHA yapılandırması (Builder Kalıbı) için veri modelleri, bileşen katalogları ve özel hatalar.

Tüm bileşen verileri eğitim ve simülasyon amaçlı sentetik değerlerden oluşur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


class UAVConfigurationError(ValueError):
    """
    Geçersiz bir İHA konfigürasyonu tespit edildiğinde fırlatılan özel istisna sınıfı.
    Maksimum kalkış ağırlığı (MTOW) aşımı, eksik zorunlu bileşen veya görev profili
    uyumsuzluğu durumlarında detaylı hata listesini barındırır.
    """

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or [message]


@dataclass(frozen=True)
class SensorSpec:
    """İHA üzerine entegre edilebilen sentetik sensör teknik özellikleri."""

    name: str
    sensor_type: str
    weight_kg: float
    power_watts: float
    compatible_missions: Tuple[str, ...]
    description: str


@dataclass(frozen=True)
class PayloadSpec:
    """İHA istasyonlarına (hardpoint) takılabilen sentetik görev yükü özellikleri."""

    name: str
    category: str
    weight_kg: float
    hardpoint_type: str
    compatible_missions: Tuple[str, ...]
    description: str


@dataclass(frozen=True)
class CommsModuleSpec:
    """İHA haberleşme ve veri bağı (Data Link) modülü teknik özellikleri."""

    name: str
    bandwidth_mbps: float
    weight_kg: float
    encrypted_capable: bool
    range_km: float
    description: str


# Sentetik Sensör Kataloğu
SENSOR_CATALOG: Dict[str, SensorSpec] = {
    "EO/IR Termal Kamera Podu": SensorSpec(
        name="EO/IR Termal Kamera Podu",
        sensor_type="OPTICAL_THERMAL",
        weight_kg=48.0,
        power_watts=350.0,
        compatible_missions=("RECON", "STRIKE"),
        description="Gece/gündüz elektro-optik ve kızılötesi görüntüleme sensörü.",
    ),
    "SAR Sentetik Açıklıklı Radar": SensorSpec(
        name="SAR Sentetik Açıklıklı Radar",
        sensor_type="RADAR_SAR",
        weight_kg=85.0,
        power_watts=750.0,
        compatible_missions=("RECON", "STRIKE"),
        description="Bulut altı yüksek çözünürlüklü yüzey haritalama radarı.",
    ),
    "STANAG Atış Kontrol Radarı": SensorSpec(
        name="STANAG Atış Kontrol Radarı",
        sensor_type="RADAR_FCR",
        weight_kg=120.0,
        power_watts=1100.0,
        compatible_missions=("STRIKE",),
        description="Yalnızca taarruz (STRIKE) gövdeleriyle uyumlu hedef takip radarı.",
    ),
    "Hiperspektral Keşif Kamerası": SensorSpec(
        name="Hiperspektral Keşif Kamerası",
        sensor_type="OPTICAL_HYPERSPECTRAL",
        weight_kg=62.0,
        power_watts=420.0,
        compatible_missions=("RECON",),
        description="Yalnızca keşif (RECON) gövdeleriyle uyumlu geniş alan spektral tarayıcı.",
    ),
    "SIGINT Elektronik İstihbarat Sensörü": SensorSpec(
        name="SIGINT Elektronik İstihbarat Sensörü",
        sensor_type="SIGINT",
        weight_kg=55.0,
        power_watts=500.0,
        compatible_missions=("RECON", "STRIKE"),
        description="Pasif radyo frekans ve sinyal analiz sensörü.",
    ),
}

# Sentetik Faydalı Yük / Görev Ekipmanı Kataloğu (Temsili Simülasyon Yükleri)
PAYLOAD_CATALOG: Dict[str, PayloadSpec] = {
    "Lazer İşaretleme ve Eğitim Podu": PayloadSpec(
        name="Lazer İşaretleme ve Eğitim Podu",
        category="TACTICAL_SIM",
        weight_kg=110.0,
        hardpoint_type="MEDIUM_PYLON",
        compatible_missions=("STRIKE",),
        description="Temsili hedef işaretleme ve angajman simülasyon podu.",
    ),
    "Ağır Görev Test Yükü (Sim-500)": PayloadSpec(
        name="Ağır Görev Test Yükü (Sim-500)",
        category="HEAVY_TACTICAL_SIM",
        weight_kg=480.0,
        hardpoint_type="HEAVY_PYLON",
        compatible_missions=("STRIKE",),
        description="Yüksek ağırlıklı taarruz profili denge ve kapasite test yükü.",
    ),
    "Hafif Hassas Görev Yükü (Sim-100)": PayloadSpec(
        name="Hafif Hassas Görev Yükü (Sim-100)",
        category="LIGHT_TACTICAL_SIM",
        weight_kg=95.0,
        hardpoint_type="LIGHT_PYLON",
        compatible_missions=("STRIKE",),
        description="Düşük ağırlıklı taktik simülasyon görev yükü.",
    ),
    "Geniş Alan Haritalama Podu": PayloadSpec(
        name="Geniş Alan Haritalama Podu",
        category="RECON_MAPPING",
        weight_kg=70.0,
        hardpoint_type="LIGHT_PYLON",
        compatible_missions=("RECON",),
        description="Keşif görevleri için yüksek doğruluklu topografik tarama podu.",
    ),
    "Harici Ek Yakıt Tankı (Drop Tank)": PayloadSpec(
        name="Harici Ek Yakıt Tankı (Drop Tank)",
        category="AUX_FUEL",
        weight_kg=180.0,
        hardpoint_type="UNIVERSAL_PYLON",
        compatible_missions=("RECON", "STRIKE"),
        description="Menzil artırıcı harici kanat altı yakıt tankı.",
    ),
    "Elektronik Destek (ESM) Karşı Tedbir Podu": PayloadSpec(
        name="Elektronik Destek (ESM) Karşı Tedbir Podu",
        category="EW_SUPPORT",
        weight_kg=85.0,
        hardpoint_type="UNIVERSAL_PYLON",
        compatible_missions=("RECON", "STRIKE"),
        description="Simüle edilmiş pasif koruma ve sinyal analiz podu.",
    ),
}

# Sentetik Haberleşme Modülü Kataloğu
COMMS_CATALOG: Dict[str, CommsModuleSpec] = {
    "LOS Görüş Hattı Radyo Bağı (UHF/VHF)": CommsModuleSpec(
        name="LOS Görüş Hattı Radyo Bağı (UHF/VHF)",
        bandwidth_mbps=12.0,
        weight_kg=18.0,
        encrypted_capable=True,
        range_km=250.0,
        description="Kısa/orta menzil standart görüş hattı telemetri ve komut bağı.",
    ),
    "SATCOM Uydu Haberleşme Terminali (Ku-Band)": CommsModuleSpec(
        name="SATCOM Uydu Haberleşme Terminali (Ku-Band)",
        bandwidth_mbps=50.0,
        weight_kg=45.0,
        encrypted_capable=True,
        range_km=2500.0,
        description="Görüş hattı ötesi (BLOS) uzun menzil uydu haberleşme modülü.",
    ),
    "Çift Yedekli Taktik Veri Bağı (STANAG-Link)": CommsModuleSpec(
        name="Çift Yedekli Taktik Veri Bağı (STANAG-Link)",
        bandwidth_mbps=35.0,
        weight_kg=32.0,
        encrypted_capable=True,
        range_km=600.0,
        description="Frekans atlamalı, yüksek güvenlikli taktik veri bağı modülü.",
    ),
}
