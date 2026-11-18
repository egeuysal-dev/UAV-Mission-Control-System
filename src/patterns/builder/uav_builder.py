"""
GoF Builder Tasarım Kalıbı (Yaratımsal) — İHA Görev Yapılandırması ve Doğrulama.

Katılımcı Sınıflar:
- Product: UAVPlatform
- Builder (ABC): UAVConfigurationBuilder
- ConcreteBuilder: StrikeUAVBuilder, ReconUAVBuilder
- Director: MissionPrepDirector
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.models.uav_models import (
    COMMS_CATALOG,
    PAYLOAD_CATALOG,
    SENSOR_CATALOG,
    CommsModuleSpec,
    PayloadSpec,
    SensorSpec,
    UAVConfigurationError,
)
from src.utils.logger import system_logger


@dataclass
class UAVPlatform:
    """
    GoF Builder Kalıbı — Product (Ürün) Sınıfı.

    Adım adım yapılandırılan İHA platformunu, alt bileşenlerini, ağırlık dağılımını
    ve teknik/operasyonel doğrulama kurallarını temsil eder.
    """

    model_name: str = ""
    mission_type: str = ""  # "STRIKE" veya "RECON"
    airframe_type: str = ""
    empty_weight_kg: float = 0.0
    max_takeoff_weight_kg: float = 0.0
    max_fuel_capacity_kg: float = 0.0
    min_fuel_required_kg: float = 50.0
    max_hardpoints: int = 0
    max_sensor_slots: int = 3
    fuel_weight_kg: float = 0.0
    sensors: List[SensorSpec] = field(default_factory=list)
    payloads: List[PayloadSpec] = field(default_factory=list)
    comms_module: Optional[CommsModuleSpec] = None

    @property
    def sensors_weight_kg(self) -> float:
        """Takılı tüm sensörlerin toplam ağırlığını (kg) hesaplar."""
        return sum(sensor.weight_kg for sensor in self.sensors)

    @property
    def payloads_weight_kg(self) -> float:
        """Takılı tüm faydalı yüklerin toplam ağırlığını (kg) hesaplar."""
        return sum(payload.weight_kg for payload in self.payloads)

    @property
    def comms_weight_kg(self) -> float:
        """Haberleşme modülünün ağırlığını (kg) döndürür."""
        return self.comms_module.weight_kg if self.comms_module is not None else 0.0

    @property
    def total_weight_kg(self) -> float:
        """
        İHA'nın toplam kalkış ağırlığını (Boş Ağırlık + Yakıt + Sensörler + Yükler + Haberleşme) hesaplar.
        """
        return (
            self.empty_weight_kg
            + self.fuel_weight_kg
            + self.sensors_weight_kg
            + self.payloads_weight_kg
            + self.comms_weight_kg
        )

    @property
    def remaining_weight_capacity_kg(self) -> float:
        """Maksimum kalkış ağırlığına (MTOW) kalan kullanılabilir ağırlık marjını döndürür."""
        return self.max_takeoff_weight_kg - self.total_weight_kg

    @property
    def estimated_endurance_hours(self) -> float:
        """
        Yakıt miktarı (varsa harici yakıt tankı dahil) ve toplam ağırlığa göre
        sentetik tahmini havada kalış süresini (saat) hesaplar.
        """
        if self.fuel_weight_kg <= 0 or self.total_weight_kg <= 0:
            return 0.0
        aux_fuel_bonus = sum(
            120.0 for p in self.payloads if p.category == "AUX_FUEL"
        )
        effective_fuel = self.fuel_weight_kg + aux_fuel_bonus
        burn_rate_kg_per_hr = max(18.0, self.total_weight_kg * 0.025)
        return round(effective_fuel / burn_rate_kg_per_hr, 1)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Öneri D — İHA Mühendislik ve Aerodinamik Performans Analizi:
        Yapılandırılan platformun ağırlık, yakıt, sensör güç tüketimi, veri bağı
        menzili ve harici yük sürüklemesine göre uçuş zarfı metriklerini ve
        5 eksenli yetenek puanlarını (0-100) hesaplar.
        """
        is_strike = self.mission_type == "STRIKE"
        burn_rate_kg_hr = round(max(18.0, self.total_weight_kg * 0.025), 1)
        endurance_hr = self.estimated_endurance_hours

        # Harici yük sayısı arttıkça parazitik sürükleme nedeniyle seyir hızı hafif düşer
        base_cruise_kts = 160.0 if is_strike else 118.0
        drag_penalty_kts = len(self.payloads) * 3.5
        cruise_speed_kts = round(max(85.0, base_cruise_kts - drag_penalty_kts), 1)
        cruise_speed_kmh = cruise_speed_kts * 1.852

        max_ferry_range_km = round(endurance_hr * cruise_speed_kmh, 0)
        comms_range_km = self.comms_module.range_km if self.comms_module else 0.0
        fuel_combat_radius_km = round(max_ferry_range_km * 0.42, 0)
        effective_combat_radius_km = (
            round(min(comms_range_km, fuel_combat_radius_km), 0)
            if comms_range_km > 0
            else 0.0
        )

        sensor_power_watts = round(sum(s.power_watts for s in self.sensors), 0)
        mtow_ratio = (
            self.total_weight_kg / self.max_takeoff_weight_kg
            if self.max_takeoff_weight_kg > 0
            else 1.0
        )
        base_takeoff_m = 620.0 if is_strike else 450.0
        takeoff_roll_m = round(base_takeoff_m * (0.65 + 0.65 * mtow_ratio), 0)

        base_ceiling_m = 11500.0 if is_strike else 9200.0
        service_ceiling_m = round(max(4500.0, base_ceiling_m * (1.18 - 0.30 * mtow_ratio)), 0)

        # 5 Eksenli Yetenek Radar Puanları (0 - 100)
        endurance_score = round(min(100.0, (endurance_hr / 24.0) * 100.0), 1)
        range_score = round(min(100.0, (effective_combat_radius_km / 1200.0) * 100.0), 1)
        isr_score = round(
            min(
                100.0,
                len(self.sensors) * 28.0
                + (16.0 if any("RADAR" in s.sensor_type for s in self.sensors) else 0.0),
            ),
            1,
        )
        max_payload_ref = 900.0 if is_strike else 250.0
        payload_score = round(
            min(100.0, (self.payloads_weight_kg / max_payload_ref) * 100.0), 1
        )
        agility_score = round(
            min(100.0, max(10.0, (1.0 - (mtow_ratio - 0.55)) * 90.0)), 1
        )

        return {
            "burn_rate_kg_hr": burn_rate_kg_hr,
            "endurance_hours": endurance_hr,
            "cruise_speed_kts": cruise_speed_kts,
            "max_ferry_range_km": max_ferry_range_km,
            "comms_range_km": comms_range_km,
            "combat_radius_km": effective_combat_radius_km,
            "sensor_power_watts": sensor_power_watts,
            "takeoff_roll_m": takeoff_roll_m,
            "service_ceiling_m": service_ceiling_m,
            "mtow_usage_pct": round(mtow_ratio * 100.0, 1),
            "radar_scores": {
                "Havada Kalış (Endurance)": endurance_score,
                "Harekât Yarıçapı (Range)": range_score,
                "Keşif & Sensör (ISR)": isr_score,
                "Faydalı Yük (Payload)": payload_score,
                "Çeviklik & Marj (Agility)": agility_score,
            },
        }

    def validate(self) -> Tuple[bool, List[str]]:
        """
        İHA yapılandırmasının tüm mühendislik ve görev kısıtlarına uygunluğunu denetler.

        Returns:
            (is_valid, errors): Geçerlilik durumu ve tespit edilen hata mesajları listesi.
        """
        errors: List[str] = []

        # 1. Gövde (Airframe) kontrolü
        if not self.model_name or not self.airframe_type or not self.mission_type:
            errors.append("Gövde (Airframe) ve görev profili tanımlanmamış.")

        # 2. Yakıt kapasitesi ve minimum yakıt kontrolü
        if self.fuel_weight_kg <= 0:
            errors.append("Yakıt miktarı 0 kg'dan büyük olmalıdır.")
        elif self.fuel_weight_kg < self.min_fuel_required_kg:
            errors.append(
                f"{self.mission_type} profili için minimum {self.min_fuel_required_kg:.0f} kg "
                f"yakıt gereklidir (girilen: {self.fuel_weight_kg:.0f} kg)."
            )
        elif self.fuel_weight_kg > self.max_fuel_capacity_kg:
            errors.append(
                f"Yakıt miktarı ({self.fuel_weight_kg:.0f} kg), gövde maksimum yakıt "
                f"kapasitesini ({self.max_fuel_capacity_kg:.0f} kg) aşıyor."
            )

        # 3. Haberleşme modülü kontrolü
        if self.comms_module is None:
            errors.append("Haberleşme modülü (Comms Module) seçilmemiş.")

        # 4. Sensör sayısı ve uyumluluk kontrolü
        if len(self.sensors) == 0:
            errors.append("Görev güvenliği için en az 1 sensör seçilmelidir.")
        elif len(self.sensors) > self.max_sensor_slots:
            errors.append(
                f"Sensör sayısı ({len(self.sensors)}), maksimum sensör yuvası "
                f"kapasitesini ({self.max_sensor_slots}) aşıyor."
            )

        for sensor in self.sensors:
            if self.mission_type and self.mission_type not in sensor.compatible_missions:
                errors.append(
                    f"Uyumsuz Sensör: '{sensor.name}' yalnızca {sensor.compatible_missions} "
                    f"görev profiliyle uyumludur ({self.mission_type} gövdesine takılamaz)."
                )

        # 5. Faydalı yük istasyon (hardpoint) sayısı ve uyumluluk kontrolü
        if len(self.payloads) > self.max_hardpoints:
            errors.append(
                f"Takılan faydalı yük sayısı ({len(self.payloads)}), gövde istasyon "
                f"(hardpoint) kapasitesini ({self.max_hardpoints}) aşıyor."
            )

        for payload in self.payloads:
            if self.mission_type and self.mission_type not in payload.compatible_missions:
                errors.append(
                    f"Uyumsuz Faydalı Yük: '{payload.name}' yalnızca {payload.compatible_missions} "
                    f"görev profiliyle uyumludur ({self.mission_type} gövdesine takılamaz)."
                )

        # 6. Maksimum Kalkış Ağırlığı (MTOW) kontrolü
        if self.max_takeoff_weight_kg > 0 and self.total_weight_kg > self.max_takeoff_weight_kg:
            excess = self.total_weight_kg - self.max_takeoff_weight_kg
            errors.append(
                f"Maksimum Kalkış Ağırlığı (MTOW) Aşıldı: Toplam ağırlık "
                f"{self.total_weight_kg:.1f} kg, izin verilen MTOW "
                f"{self.max_takeoff_weight_kg:.1f} kg (Aşım: +{excess:.1f} kg)."
            )

        return (len(errors) == 0, errors)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Kullanıcı arayüzü ve raporlama için yapılandırma özetini sözlük olarak döndürür."""
        is_valid, errors = self.validate()
        return {
            "model_name": self.model_name,
            "mission_type": self.mission_type,
            "airframe_type": self.airframe_type,
            "empty_weight_kg": self.empty_weight_kg,
            "fuel_weight_kg": self.fuel_weight_kg,
            "sensors_weight_kg": self.sensors_weight_kg,
            "payloads_weight_kg": self.payloads_weight_kg,
            "comms_weight_kg": self.comms_weight_kg,
            "total_weight_kg": self.total_weight_kg,
            "max_takeoff_weight_kg": self.max_takeoff_weight_kg,
            "remaining_weight_capacity_kg": self.remaining_weight_capacity_kg,
            "estimated_endurance_hours": self.estimated_endurance_hours,
            "sensors": [s.name for s in self.sensors],
            "payloads": [p.name for p in self.payloads],
            "comms_module": self.comms_module.name if self.comms_module else None,
            "hardpoints_used": f"{len(self.payloads)}/{self.max_hardpoints}",
            "sensor_slots_used": f"{len(self.sensors)}/{self.max_sensor_slots}",
            "is_valid": is_valid,
            "validation_errors": errors,
        }


class UAVConfigurationBuilder(ABC):
    """
    GoF Builder Kalıbı — Builder (Soyut Arayüz) Sınıfı.

    Farklı görev profillerine sahip İHA nesnelerinin adım adım oluşturulması
    için gereken standart inşa metotlarını tanımlar.
    """

    @abstractmethod
    def reset(self) -> None:
        """Üzerinde çalışılan taslak UAVPlatform nesnesini sıfırlar."""

    @abstractmethod
    def set_airframe(self, model_name: Optional[str] = None) -> UAVConfigurationBuilder:
        """Görev profiline uygun gövde, boş ağırlık ve MTOW limitlerini ayarlar."""

    @abstractmethod
    def set_fuel_capacity(self, fuel_kg: float) -> UAVConfigurationBuilder:
        """İHA'ya yüklenecek yakıt miktarını (kg) belirler."""

    @abstractmethod
    def add_sensor(self, sensor_name: str) -> UAVConfigurationBuilder:
        """Katalogdan seçilen bir sensörü İHA üzerine ekler."""

    @abstractmethod
    def add_payload(self, payload_name: str) -> UAVConfigurationBuilder:
        """Katalogdan seçilen bir faydalı yükü istasyona (hardpoint) ekler."""

    @abstractmethod
    def set_comms_module(self, comms_name: str) -> UAVConfigurationBuilder:
        """Katalogdan seçilen haberleşme modülünü İHA'ya entegre eder."""

    @abstractmethod
    def get_draft_platform(self) -> UAVPlatform:
        """Doğrulama öncesi mevcut taslak platformun bir kopyasını döndürür (UI önizlemesi için)."""

    @abstractmethod
    def build(self) -> UAVPlatform:
        """
        Tüm yapılandırma ve uyumluluk doğrulamalarını çalıştırır.
        Geçerliyse UAVPlatform nesnesini döndürür, geçersizse UAVConfigurationError fırlatır.
        """


class _BaseUAVBuilder(UAVConfigurationBuilder):
    """
    StrikeUAVBuilder ve ReconUAVBuilder arasındaki ortak katalog arama,
    adım adım bileşen ekleme ve son doğrulama akışını yöneten taban sınıf.
    """

    def __init__(self) -> None:
        self._platform: UAVPlatform = UAVPlatform()
        self.reset()

    def reset(self) -> None:
        """Taslak platformu sıfırlar ve varsayılan gövde değerlerini yükler."""
        self._platform = UAVPlatform()
        self.set_airframe()

    def set_fuel_capacity(self, fuel_kg: float) -> UAVConfigurationBuilder:
        """Yakıt miktarını (kg) ayarlar."""
        self._platform.fuel_weight_kg = float(fuel_kg)
        return self

    def add_sensor(self, sensor_name: str) -> UAVConfigurationBuilder:
        """Katalogdan sensör bularak platforma ekler."""
        if sensor_name not in SENSOR_CATALOG:
            raise UAVConfigurationError(
                f"Bilinmeyen sensör: '{sensor_name}'. Geçerli sensörler: {list(SENSOR_CATALOG.keys())}"
            )
        self._platform.sensors.append(SENSOR_CATALOG[sensor_name])
        return self

    def add_payload(self, payload_name: str) -> UAVConfigurationBuilder:
        """Katalogdan faydalı yük bularak platforma ekler."""
        if payload_name not in PAYLOAD_CATALOG:
            raise UAVConfigurationError(
                f"Bilinmeyen faydalı yük: '{payload_name}'. Geçerli yükler: {list(PAYLOAD_CATALOG.keys())}"
            )
        self._platform.payloads.append(PAYLOAD_CATALOG[payload_name])
        return self

    def set_comms_module(self, comms_name: str) -> UAVConfigurationBuilder:
        """Katalogdan haberleşme modülü bularak platforma atar."""
        if comms_name not in COMMS_CATALOG:
            raise UAVConfigurationError(
                f"Bilinmeyen haberleşme modülü: '{comms_name}'. Geçerli modüller: {list(COMMS_CATALOG.keys())}"
            )
        self._platform.comms_module = COMMS_CATALOG[comms_name]
        return self

    def get_draft_platform(self) -> UAVPlatform:
        """Mevcut taslağın derin kopyasını döndürür."""
        return deepcopy(self._platform)

    def build(self) -> UAVPlatform:
        """
        Yapılandırılan UAVPlatform nesnesini doğrular; kurallar sağlanıyorsa
        ürünü teslim eder ve builder durumunu yeni inşa için sıfırlar.
        """
        is_valid, errors = self._platform.validate()
        if not is_valid:
            joined_errors = " | ".join(errors)
            system_logger.error(
                "Builder",
                f"[{self._platform.model_name or self._platform.mission_type}] "
                f"Yapılandırma reddedildi: {joined_errors}",
            )
            raise UAVConfigurationError(
                f"İHA yapılandırması geçersiz ({len(errors)} hata): {joined_errors}",
                errors=errors,
            )

        completed_platform = deepcopy(self._platform)
        system_logger.info(
            "Builder",
            f"'{completed_platform.model_name}' ({completed_platform.mission_type}) başarıyla inşa edildi. "
            f"Toplam Ağırlık: {completed_platform.total_weight_kg:.1f}/"
            f"{completed_platform.max_takeoff_weight_kg:.1f} kg.",
        )
        self.reset()
        return completed_platform


class StrikeUAVBuilder(_BaseUAVBuilder):
    """
    GoF Builder Kalıbı — ConcreteBuilder 1 (Taarruz / Ağır Görev İHA İnşacısı).

    Yüksek kalkış ağırlığı kapasitesine (MTOW: 5500 kg) ve 4 faydalı yük istasyonuna
    sahip çift turboprop taarruz/taktik İHA yapılandırmasını yönetir.
    """

    def set_airframe(self, model_name: Optional[str] = None) -> StrikeUAVBuilder:
        """Ağır sınıf taarruz İHA gövde parametrelerini tanımlar."""
        self._platform.model_name = model_name or "AKINCI-S Taktik İHA (Sim)"
        self._platform.mission_type = "STRIKE"
        self._platform.airframe_type = "Çift Turboprop Ağır Taarruz Gövdesi"
        self._platform.empty_weight_kg = 3300.0
        self._platform.max_takeoff_weight_kg = 5500.0
        self._platform.max_fuel_capacity_kg = 1500.0
        self._platform.min_fuel_required_kg = 200.0
        self._platform.max_hardpoints = 4
        self._platform.max_sensor_slots = 3
        return self


class ReconUAVBuilder(_BaseUAVBuilder):
    """
    GoF Builder Kalıbı — ConcreteBuilder 2 (Keşif ve Gözetleme İHA İnşacısı).

    Yüksek irtifa - uzun havada kalış (HALE/MALE) odaklı, hafif kompozit gövdeli
    (MTOW: 1750 kg, 2 istasyonlu) keşif İHA yapılandırmasını yönetir.
    """

    def set_airframe(self, model_name: Optional[str] = None) -> ReconUAVBuilder:
        """Keşif sınıfı İHA gövde parametrelerini tanımlar."""
        self._platform.model_name = model_name or "ANKA-R Keşif İHA (Sim)"
        self._platform.mission_type = "RECON"
        self._platform.airframe_type = "Yüksek Açıklıklı Kompozit Keşif Gövdesi"
        self._platform.empty_weight_kg = 980.0
        self._platform.max_takeoff_weight_kg = 1750.0
        self._platform.max_fuel_capacity_kg = 600.0
        self._platform.min_fuel_required_kg = 120.0
        self._platform.max_hardpoints = 2
        self._platform.max_sensor_slots = 3
        return self


class MissionPrepDirector:
    """
    GoF Builder Kalıbı — Director (Yönetici) Sınıfı.

    UAVConfigurationBuilder arayüzünü kullanarak önceden tanımlanmış standart
    veya parametrik görev konfigürasyonlarını belirli bir inşa sırasıyla üretir.
    """

    def __init__(self, builder: Optional[UAVConfigurationBuilder] = None) -> None:
        self._builder: Optional[UAVConfigurationBuilder] = builder

    @property
    def builder(self) -> UAVConfigurationBuilder:
        """Aktif builder nesnesini döndürür; atanmamışsa hata fırlatır."""
        if self._builder is None:
            raise UAVConfigurationError("MissionPrepDirector için aktif bir Builder atanmamış.")
        return self._builder

    def set_builder(self, builder: UAVConfigurationBuilder) -> None:
        """Çalışma zamanında aktif builder nesnesini değiştirir."""
        self._builder = builder

    def construct_standard_recon_uav(self) -> UAVPlatform:
        """
        Standart uzun süreli keşif/gözetleme İHA konfigürasyonu inşa eder.
        """
        b = self.builder
        b.reset()
        return (
            b.set_airframe("ANKA-R Standart Keşif")
            .set_fuel_capacity(420.0)
            .add_sensor("EO/IR Termal Kamera Podu")
            .add_sensor("Hiperspektral Keşif Kamerası")
            .add_payload("Geniş Alan Haritalama Podu")
            .set_comms_module("LOS Görüş Hattı Radyo Bağı (UHF/VHF)")
            .build()
        )

    def construct_long_range_recon_uav(self) -> UAVPlatform:
        """
        Uydu haberleşmeli (SATCOM) ve ek yakıt tanklı uzun menzil stratejik keşif İHA'sı inşa eder.
        """
        b = self.builder
        b.reset()
        return (
            b.set_airframe("AKSUNGUR-R Stratejik Keşif")
            .set_fuel_capacity(350.0)
            .add_sensor("EO/IR Termal Kamera Podu")
            .add_sensor("SAR Sentetik Açıklıklı Radar")
            .add_sensor("SIGINT Elektronik İstihbarat Sensörü")
            .add_payload("Harici Ek Yakıt Tankı (Drop Tank)")
            .set_comms_module("SATCOM Uydu Haberleşme Terminali (Ku-Band)")
            .build()
        )

    def construct_standard_strike_uav(self) -> UAVPlatform:
        """
        Standart taktik görev profili için dengeli yük ve sensör donanımlı İHA inşa eder.
        """
        b = self.builder
        b.reset()
        return (
            b.set_airframe("AKINCI-S Taktik Görev")
            .set_fuel_capacity(1100.0)
            .add_sensor("EO/IR Termal Kamera Podu")
            .add_sensor("STANAG Atış Kontrol Radarı")
            .add_payload("Lazer İşaretleme ve Eğitim Podu")
            .add_payload("Hafif Hassas Görev Yükü (Sim-100)")
            .add_payload("Elektronik Destek (ESM) Karşı Tedbir Podu")
            .set_comms_module("Çift Yedekli Taktik Veri Bağı (STANAG-Link)")
            .build()
        )

    def construct_heavy_strike_uav(self) -> UAVPlatform:
        """
        Uzun menzilli, ağır görev yükü ve SATCOM donanımlı İHA inşa eder.
        """
        b = self.builder
        b.reset()
        return (
            b.set_airframe("AKINCI-B Ağır Görev")
            .set_fuel_capacity(1200.0)
            .add_sensor("EO/IR Termal Kamera Podu")
            .add_sensor("STANAG Atış Kontrol Radarı")
            .add_sensor("SAR Sentetik Açıklıklı Radar")
            .add_payload("Ağır Görev Test Yükü (Sim-500)")
            .add_payload("Lazer İşaretleme ve Eğitim Podu")
            .add_payload("Elektronik Destek (ESM) Karşı Tedbir Podu")
            .set_comms_module("SATCOM Uydu Haberleşme Terminali (Ku-Band)")
            .build()
        )

    def construct_custom_uav(
        self,
        model_name: Optional[str],
        fuel_kg: float,
        sensors: List[str],
        payloads: List[str],
        comms_name: str,
    ) -> UAVPlatform:
        """
        Kullanıcı arayüzünden veya harici servislerden gelen özel parametrelerle
        adım adım İHA konfigürasyonu oluşturur ve doğrular.
        """
        b = self.builder
        b.reset()
        b.set_airframe(model_name)
        b.set_fuel_capacity(fuel_kg)
        for sensor_name in sensors:
            b.add_sensor(sensor_name)
        for payload_name in payloads:
            b.add_payload(payload_name)
        if comms_name:
            b.set_comms_module(comms_name)
        return b.build()
