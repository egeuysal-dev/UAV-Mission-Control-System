"""
GoF Adapter Tasarım Kalıbı (Yapısal) — Heterojen Sensör Entegrasyonu.

Katılımcı Sınıflar:
- Target (ABC): TargetSensor
- Adaptee 1: LegacyStanagRadarSDK
- Adaptee 2: VendorThermalDevice
- Adapter 1: StanagRadarAdapter
- Adapter 2: ThermalCameraAdapter
- Client: MissionComputer
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, List, Optional

from src.models.sensor_models import SensorIntegrationError, TargetData
from src.utils.logger import system_logger


class TargetSensor(ABC):
    """
    GoF Adapter Kalıbı — Target (Hedef Arayüz) Sınıfı.

    MissionComputer (Görev Bilgisayarı) sınıfının tüm sensörlerle iletişim kurarken
    kullandığı standart ve sensör üreticisinden bağımsız soyut arayüz.
    """

    @abstractmethod
    def read_target_data(self) -> TargetData:
        """Sensörden veri okur ve standart TargetData formatında döndürür."""

    @abstractmethod
    def get_sensor_info(self) -> Dict[str, Any]:
        """Sensörün kimlik, protokol ve adaptör bilgilerini döndürür."""


class LegacyStanagRadarSDK:
    """
    GoF Adapter Kalıbı — Adaptee 1 (Uyumsuz Eski Nesil STANAG Radar SDK'sı).

    Farklı bir metot imzasına (`fetch_polar_blip_buffer`) ve İngiliz/Askeri birimler
    (Miliradyan, Yard, Feet, dB) içeren pipe (`|`) ayracıyla biçimlendirilmiş
    ham ASCII veri yapısına sahiptir. MissionComputer ile doğrudan kullanılamaz.
    """

    _PRESET_BLIPS: List[str] = [
        "STANAG4607|TRK:104|AZ_MRAD:1047.20|RNG_YD:15310.6|ALT_FT:3937.0|SNR_DB:22.0|CLS:2",
        "STANAG4607|TRK:109|AZ_MRAD:2356.19|RNG_YD:24059.5|ALT_FT:8202.1|SNR_DB:19.5|CLS:3",
        "STANAG4607|TRK:115|AZ_MRAD:4712.39|RNG_YD:9842.5|ALT_FT:1640.4|SNR_DB:24.0|CLS:2",
    ]

    def __init__(
        self,
        custom_blip_buffer: Optional[str] = None,
        status_code: int = 0x00,
    ) -> None:
        self._custom_blip_buffer = custom_blip_buffer
        self._status_code = status_code
        self._cursor = 0

    def get_radar_status_code(self) -> int:
        """
        Eski nesil radar donanım durum kodunu döndürür.
        0x00: Normal Çalışma, != 0x00: Donanım/Senkronizasyon Hatası.
        """
        return self._status_code

    def set_radar_status_code(self, status_code: int) -> None:
        """Simülasyon testi için radar durum kodunu günceller."""
        self._status_code = status_code

    def set_custom_blip_buffer(self, blip_buffer: Optional[str]) -> None:
        """Belirli bir ham telemetri dizesini test veya simülasyon için enjekte eder."""
        self._custom_blip_buffer = blip_buffer

    def fetch_polar_blip_buffer(self) -> str:
        """
        Kutupsal koordinatlarda ham STANAG radar izini ASCII dize olarak döndürür.

        Format:
            STANAG4607|TRK:<id>|AZ_MRAD:<miliradyan>|RNG_YD:<yard>|ALT_FT:<feet>|SNR_DB:<db>|CLS:<kod>
        """
        if self._custom_blip_buffer is not None:
            return self._custom_blip_buffer

        blip = self._PRESET_BLIPS[self._cursor % len(self._PRESET_BLIPS)]
        self._cursor += 1
        return blip


class VendorThermalDevice:
    """
    GoF Adapter Kalıbı — Adaptee 2 (Uyumsuz Üçüncü Parti Termal Kamera Cihazı).

    `capture_heat_signature_json()` metodu üzerinden iç içe geçmiş (nested) bir
    sözlük yapısında Radyan, Deniz Mili (NM) ve Kelvin (K) cinsinden ham ısı izi
    verisi üretir. MissionComputer tarafından doğrudan anlaşılamaz.
    """

    _PRESET_SIGNATURES: List[Dict[str, Any]] = [
        {
            "device_header": {
                "vendor": "OptoTherm-X",
                "fw_ver": "4.2.1",
                "sensor_health": "NOMINAL",
            },
            "hotspot": {
                "blob_uid": "208",
                "angle_rad": round(math.pi / 4, 6),  # 45.0 derece
                "slant_range_nm": 6.0,               # 11.112 km
                "elevation_m": 850.0,
                "peak_temp_kelvin": 353.15,          # 80 °C
                "pixel_cluster_pct": 91.0,
                "signature_tag": "ENGINE_PLUME",
            },
        },
        {
            "device_header": {
                "vendor": "OptoTherm-X",
                "fw_ver": "4.2.1",
                "sensor_health": "NOMINAL",
            },
            "hotspot": {
                "blob_uid": "214",
                "angle_rad": round(math.pi, 6),      # 180.0 derece
                "slant_range_nm": 4.5,               # 8.334 km
                "elevation_m": 420.0,
                "peak_temp_kelvin": 335.15,          # 62 °C
                "pixel_cluster_pct": 82.0,
                "signature_tag": "GENERATOR_HEAT",
            },
        },
        {
            "device_header": {
                "vendor": "OptoTherm-X",
                "fw_ver": "4.2.1",
                "sensor_health": "NOMINAL",
            },
            "hotspot": {
                "blob_uid": "221",
                "angle_rad": round(5 * math.pi / 3, 6),  # 300.0 derece
                "slant_range_nm": 8.0,                   # 14.816 km
                "elevation_m": 1150.0,
                "peak_temp_kelvin": 318.15,              # 45 °C
                "pixel_cluster_pct": 74.0,
                "signature_tag": "THERMAL_ANOMALY",
            },
        },
    ]

    def __init__(self, custom_payload: Optional[Dict[str, Any]] = None) -> None:
        self._custom_payload = custom_payload
        self._cursor = 0

    def set_custom_payload(self, payload: Optional[Dict[str, Any]]) -> None:
        """Test veya simülasyon senaryoları için özel ham sözlük verisi ayarlar."""
        self._custom_payload = payload

    def capture_heat_signature_json(self) -> Dict[str, Any]:
        """Üreticiye özgü formatta ham termal kamera verisini döndürür."""
        if self._custom_payload is not None:
            return deepcopy(self._custom_payload)

        frame = deepcopy(self._PRESET_SIGNATURES[self._cursor % len(self._PRESET_SIGNATURES)])
        self._cursor += 1
        return frame


class StanagRadarAdapter(TargetSensor):
    """
    GoF Adapter Kalıbı — Adapter 1 (STANAG Radar Adaptörü).

    `LegacyStanagRadarSDK` nesnesini sarmalar (composition) ve ürettiği ham
    ASCII kutupsal radar verisini `TargetData` standardına dönüştürür.
    """

    _CLASSIFICATION_MAP: Dict[int, str] = {
        1: "AIR_TRACK",
        2: "SURFACE_VEHICLE",
        3: "RADAR_EMITTER",
    }

    # Birim dönüşüm sabitleri
    _YARDS_TO_KM: float = 0.0009144
    _FEET_TO_M: float = 0.3048
    _MRAD_PER_CIRCLE: float = 2.0 * math.pi * 1000.0  # ~6283.185 mrad = 360°

    def __init__(self, radar_sdk: Optional[LegacyStanagRadarSDK] = None) -> None:
        self._adaptee: LegacyStanagRadarSDK = radar_sdk or LegacyStanagRadarSDK()

    @property
    def adaptee(self) -> LegacyStanagRadarSDK:
        """Sarmalanan LegacyStanagRadarSDK nesnesini döndürür."""
        return self._adaptee

    def get_sensor_info(self) -> Dict[str, Any]:
        """Adaptör ve sarmalanan radar sensörü hakkında meta veri döndürür."""
        return {
            "sensor_name": "STANAG-4607 Taktik Radar",
            "adapter_class": self.__class__.__name__,
            "adaptee_class": self._adaptee.__class__.__name__,
            "protocol": "STANAG_4607_POLAR_LEGACY",
            "raw_units": "Azimut: mrad | Menzil: yard | İrtifa: feet | Güven: SNR (dB)",
        }

    def read_target_data(self) -> TargetData:
        """
        LegacyStanagRadarSDK'dan ham veri tamponunu okur, birim dönüşümlerini
        uygular ve standart TargetData nesnesi üretir.
        """
        status_code = self._adaptee.get_radar_status_code()
        if status_code != 0x00:
            msg = f"LegacyStanagRadarSDK donanım arıza kodu bildirdi: 0x{status_code:02X}"
            system_logger.error("Adapter", msg)
            raise SensorIntegrationError(msg)

        raw_buffer = self._adaptee.fetch_polar_blip_buffer()
        if not raw_buffer or not raw_buffer.startswith("STANAG4607|"):
            msg = f"Geçersiz STANAG radar veri paketi başlığı: '{raw_buffer}'"
            system_logger.error("Adapter", msg)
            raise SensorIntegrationError(msg)

        fields: Dict[str, str] = {}
        try:
            for token in raw_buffer.split("|")[1:]:
                key, val = token.split(":", 1)
                fields[key.strip()] = val.strip()

            track_num = fields["TRK"]
            az_mrad = float(fields["AZ_MRAD"])
            rng_yd = float(fields["RNG_YD"])
            alt_ft = float(fields["ALT_FT"])
            snr_db = float(fields["SNR_DB"])
            cls_code = int(fields["CLS"])
        except (KeyError, ValueError) as exc:
            msg = f"STANAG radar paketi ayrıştırılamadı ('{raw_buffer}'): {exc}"
            system_logger.error("Adapter", msg)
            raise SensorIntegrationError(msg) from exc

        # 1. Miliradyan -> Derece [0, 360)
        bearing_deg = round((az_mrad * 360.0 / self._MRAD_PER_CIRCLE) % 360.0, 2)
        # 2. Yard -> Kilometre (km)
        distance_km = round(rng_yd * self._YARDS_TO_KM, 3)
        # 3. Feet -> Metre (m)
        altitude_m = round(alt_ft * self._FEET_TO_M, 1)
        # 4. SNR (dB) -> Normalize Güven Skoru [0.0, 1.0]
        confidence = round(min(1.0, max(0.0, snr_db / 25.0)), 2)
        # 5. Sınıf kodu eşlemesi
        classification = self._CLASSIFICATION_MAP.get(cls_code, "UNKNOWN_CONTACT")
        # 6. Kutupsal -> 2B Kartezyen (X: Doğu, Y: Kuzey)
        rad = math.radians(bearing_deg)
        cart_x = round(distance_km * math.sin(rad), 3)
        cart_y = round(distance_km * math.cos(rad), 3)

        notes = (
            f"Azimut: {az_mrad:.2f} mrad -> {bearing_deg:.2f}°",
            f"Menzil: {rng_yd:.1f} yard -> {distance_km:.3f} km",
            f"İrtifa: {alt_ft:.1f} ft -> {altitude_m:.1f} m",
            f"Güven: SNR {snr_db:.1f} dB -> {confidence:.2f}",
            f"Sınıf Kodu: CLS={cls_code} -> '{classification}'",
        )

        target = TargetData(
            target_id=f"TGT-RAD-{track_num}",
            source_sensor_name="STANAG-4607 Taktik Radar",
            sensor_protocol="STANAG_4607_POLAR_LEGACY",
            bearing_deg=bearing_deg,
            distance_km=distance_km,
            altitude_m=altitude_m,
            confidence_score=confidence,
            classification=classification,
            cartesian_x_km=cart_x,
            cartesian_y_km=cart_y,
            raw_payload=raw_buffer,
            transformation_notes=notes,
        )
        system_logger.info(
            "Adapter",
            f"[StanagRadarAdapter] {target.target_id} normalize edildi "
            f"({target.bearing_deg}°, {target.distance_km} km, güven={target.confidence_score}).",
        )
        return target


class ThermalCameraAdapter(TargetSensor):
    """
    GoF Adapter Kalıbı — Adapter 2 (Termal Kamera Adaptörü).

    `VendorThermalDevice` nesnesini sarmalar (composition) ve iç içe geçmiş
    üretici JSON/sözlük verisini (Radyan, Deniz Mili, Kelvin) `TargetData`
    standardına dönüştürür.
    """

    _NM_TO_KM: float = 1.852

    _TAG_TO_CLASSIFICATION: Dict[str, str] = {
        "ENGINE_PLUME": "SURFACE_VEHICLE",
        "GENERATOR_HEAT": "RADAR_EMITTER",
        "THERMAL_ANOMALY": "THERMAL_ANOMALY",
    }

    def __init__(self, thermal_device: Optional[VendorThermalDevice] = None) -> None:
        self._adaptee: VendorThermalDevice = thermal_device or VendorThermalDevice()

    @property
    def adaptee(self) -> VendorThermalDevice:
        """Sarmalanan VendorThermalDevice nesnesini döndürür."""
        return self._adaptee

    def get_sensor_info(self) -> Dict[str, Any]:
        """Adaptör ve sarmalanan termal kamera sensörü hakkında meta veri döndürür."""
        return {
            "sensor_name": "OptoTherm EO/IR Termal Kamera",
            "adapter_class": self.__class__.__name__,
            "adaptee_class": self._adaptee.__class__.__name__,
            "protocol": "VENDOR_EOIR_JSON_V2",
            "raw_units": "Açı: radyan | Menzil: deniz mili (NM) | Sıcaklık: Kelvin (K)",
        }

    def read_target_data(self) -> TargetData:
        """
        VendorThermalDevice'dan ham ısı izi sözlüğünü okur, sağlık kontrolü ve
        birim dönüşümlerini uygulayarak standart TargetData döndürür.
        """
        raw_json = self._adaptee.capture_heat_signature_json()
        if not isinstance(raw_json, dict):
            msg = "VendorThermalDevice geçersiz veri yapısı döndürdü (dict bekleniyordu)."
            system_logger.error("Adapter", msg)
            raise SensorIntegrationError(msg)

        header = raw_json.get("device_header", {})
        health = header.get("sensor_health", "UNKNOWN")
        if health != "NOMINAL":
            msg = f"VendorThermalDevice sensör sağlık hatası bildirdi: '{health}'"
            system_logger.error("Adapter", msg)
            raise SensorIntegrationError(msg)

        try:
            hotspot = raw_json["hotspot"]
            blob_uid = str(hotspot["blob_uid"])
            angle_rad = float(hotspot["angle_rad"])
            slant_range_nm = float(hotspot["slant_range_nm"])
            elevation_m = float(hotspot["elevation_m"])
            peak_temp_k = float(hotspot["peak_temp_kelvin"])
            cluster_pct = float(hotspot["pixel_cluster_pct"])
            sig_tag = str(hotspot["signature_tag"])
        except (KeyError, TypeError, ValueError) as exc:
            msg = f"VendorThermalDevice paketi eksik veya hatalı alan içeriyor: {exc}"
            system_logger.error("Adapter", msg)
            raise SensorIntegrationError(msg) from exc

        # 1. Radyan -> Derece [0, 360)
        bearing_deg = round(math.degrees(angle_rad) % 360.0, 2)
        # 2. Deniz Mili (NM) -> Kilometre (km)
        distance_km = round(slant_range_nm * self._NM_TO_KM, 3)
        # 3. İrtifa (metre)
        altitude_m = round(elevation_m, 1)
        # 4. Kelvin sıcaklık + küme yoğunluğu -> Normalize güven skoru [0.0, 1.0]
        temp_c = round(peak_temp_k - 273.15, 1)
        temp_factor = min(1.0, max(0.0, (peak_temp_k - 273.15) / 100.0))
        cluster_factor = min(1.0, max(0.0, cluster_pct / 100.0))
        confidence = round((0.4 * temp_factor) + (0.6 * cluster_factor), 2)
        # 5. Etiket -> Standart sınıflandırma
        classification = self._TAG_TO_CLASSIFICATION.get(sig_tag, "UNKNOWN_CONTACT")
        # 6. Kutupsal -> 2B Kartezyen (X: Doğu, Y: Kuzey)
        rad = math.radians(bearing_deg)
        cart_x = round(distance_km * math.sin(rad), 3)
        cart_y = round(distance_km * math.cos(rad), 3)

        notes = (
            f"Açı: {angle_rad:.4f} rad -> {bearing_deg:.2f}°",
            f"Menzil: {slant_range_nm:.2f} NM -> {distance_km:.3f} km",
            f"Sıcaklık: {peak_temp_k:.2f} K ({temp_c:.1f} °C) & Küme %{cluster_pct:.0f} -> Güven {confidence:.2f}",
            f"İmza Etiketi: '{sig_tag}' -> '{classification}'",
        )

        target = TargetData(
            target_id=f"TGT-THM-{blob_uid}",
            source_sensor_name="OptoTherm EO/IR Termal Kamera",
            sensor_protocol="VENDOR_EOIR_JSON_V2",
            bearing_deg=bearing_deg,
            distance_km=distance_km,
            altitude_m=altitude_m,
            confidence_score=confidence,
            classification=classification,
            cartesian_x_km=cart_x,
            cartesian_y_km=cart_y,
            raw_payload=raw_json,
            transformation_notes=notes,
        )
        system_logger.info(
            "Adapter",
            f"[ThermalCameraAdapter] {target.target_id} normalize edildi "
            f"({target.bearing_deg}°, {target.distance_km} km, güven={target.confidence_score}).",
        )
        return target


class MissionComputer:
    """
    GoF Adapter Kalıbı — Client (İstemci / Görev Bilgisayarı) Sınıfı.

    Somut sensör sınıflarından (`LegacyStanagRadarSDK`, `VendorThermalDevice`)
    tamamen habersizdir; yalnızca `TargetSensor` soyut arayüzü üzerinden
    hedef verilerini toplar ve işler (Open/Closed & Dependency Inversion).
    """

    def __init__(self, sensors: Optional[List[TargetSensor]] = None) -> None:
        self._sensors: List[TargetSensor] = []
        if sensors:
            for sensor in sensors:
                self.register_sensor(sensor)

    def register_sensor(self, sensor: TargetSensor) -> None:
        """Görev bilgisayarına TargetSensor arayüzünü sağlayan bir sensör bağlar."""
        if not isinstance(sensor, TargetSensor):
            raise TypeError(
                f"MissionComputer yalnızca TargetSensor arayüzünü kabul eder; "
                f"verilen tip: {type(sensor).__name__}"
            )
        self._sensors.append(sensor)
        info = sensor.get_sensor_info()
        system_logger.info(
            "MissionComputer",
            f"Sensör kaydedildi: {info.get('sensor_name')} ({info.get('adapter_class')}).",
        )

    def clear_sensors(self) -> None:
        """Kayıtlı tüm sensörleri temizler."""
        self._sensors.clear()

    def get_registered_sensors(self) -> List[Dict[str, Any]]:
        """Kayıtlı tüm sensörlerin meta veri listesini döndürür."""
        return [sensor.get_sensor_info() for sensor in self._sensors]

    def collect_all_targets(self) -> List[TargetData]:
        """
        Kayıtlı tüm sensörlerden polimorfik olarak `read_target_data()` çağrısı
        ile standartlaştırılmış hedef verilerini toplar.
        """
        targets: List[TargetData] = []
        for sensor in self._sensors:
            target = sensor.read_target_data()
            targets.append(target)
        return targets

    def filter_high_confidence_targets(self, min_confidence: float = 0.75) -> List[TargetData]:
        """Belirtilen güven eşiğinin üzerindeki normalize hedefleri filtreler."""
        all_targets = self.collect_all_targets()
        return [t for t in all_targets if t.confidence_score >= min_confidence]
