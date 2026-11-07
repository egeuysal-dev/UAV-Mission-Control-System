"""
Aşama 3: GoF Adapter Kalıbı (Heterojen Sensör Entegrasyonu) Birim Testleri.
"""

from __future__ import annotations

import math
import pytest

from src.models.sensor_models import SensorIntegrationError, TargetData
from src.patterns.adapter import (
    LegacyStanagRadarSDK,
    MissionComputer,
    StanagRadarAdapter,
    TargetSensor,
    ThermalCameraAdapter,
    VendorThermalDevice,
)


def test_adaptees_have_incompatible_interfaces_and_formats() -> None:
    """İki sanal sensörün farklı metot imzalarına ve ham veri yapılarına sahip olduğunu doğrular."""
    radar_sdk = LegacyStanagRadarSDK()
    thermal_dev = VendorThermalDevice()

    raw_radar = radar_sdk.fetch_polar_blip_buffer()
    raw_thermal = thermal_dev.capture_heat_signature_json()

    assert isinstance(raw_radar, str)
    assert raw_radar.startswith("STANAG4607|")
    assert isinstance(raw_thermal, dict)
    assert "device_header" in raw_thermal and "hotspot" in raw_thermal


def test_stanag_radar_adapter_normalizes_units_accurately() -> None:
    """
    StanagRadarAdapter sınıfının miliradyan, yard, feet ve dB birimlerini
    derece, km, metre ve [0, 1] güven skoruna doğru dönüştürdüğünü doğrular.
    """
    # 90 derece = pi * 1000 / 2 ~= 1570.7963 mrad
    # 10 km = 10 / 0.0009144 ~= 10936.133 yard
    # 1000 m = 1000 / 0.3048 ~= 3280.84 feet
    custom_blip = (
        "STANAG4607|TRK:999|AZ_MRAD:1570.7963|RNG_YD:10936.133|ALT_FT:3280.84|SNR_DB:20.0|CLS:3"
    )
    sdk = LegacyStanagRadarSDK(custom_blip_buffer=custom_blip)
    adapter = StanagRadarAdapter(sdk)

    target = adapter.read_target_data()

    assert isinstance(target, TargetData)
    assert target.target_id == "TGT-RAD-999"
    assert math.isclose(target.bearing_deg, 90.0, abs_tol=0.05)
    assert math.isclose(target.distance_km, 10.0, abs_tol=0.01)
    assert math.isclose(target.altitude_m, 1000.0, abs_tol=0.5)
    assert target.confidence_score == 0.80
    assert target.classification == "RADAR_EMITTER"
    # 90 derece (Doğu) yönünde 10 km -> X = +10.0 km, Y = 0.0 km
    assert math.isclose(target.cartesian_x_km, 10.0, abs_tol=0.02)
    assert math.isclose(target.cartesian_y_km, 0.0, abs_tol=0.02)
    assert target.raw_payload == custom_blip
    assert len(target.transformation_notes) == 5


def test_thermal_camera_adapter_normalizes_units_accurately() -> None:
    """
    ThermalCameraAdapter sınıfının radyan, deniz mili (NM) ve Kelvin birimlerini
    standart TargetData modeline doğru dönüştürdüğünü doğrular.
    """
    custom_thermal = {
        "device_header": {
            "vendor": "OptoTherm-X",
            "fw_ver": "4.2.1",
            "sensor_health": "NOMINAL",
        },
        "hotspot": {
            "blob_uid": "501",
            "angle_rad": 0.0,         # 0.0 derece (Kuzey)
            "slant_range_nm": 10.0,   # 18.52 km
            "elevation_m": 600.0,
            "peak_temp_kelvin": 373.15,  # 100 °C -> temp_factor = 1.0
            "pixel_cluster_pct": 90.0,   # cluster_factor = 0.90 -> conf = 0.4*1.0 + 0.6*0.9 = 0.94
            "signature_tag": "ENGINE_PLUME",
        },
    }
    device = VendorThermalDevice(custom_payload=custom_thermal)
    adapter = ThermalCameraAdapter(device)

    target = adapter.read_target_data()

    assert isinstance(target, TargetData)
    assert target.target_id == "TGT-THM-501"
    assert target.bearing_deg == 0.0
    assert math.isclose(target.distance_km, 18.52, abs_tol=0.001)
    assert target.altitude_m == 600.0
    assert target.confidence_score == 0.94
    assert target.classification == "SURFACE_VEHICLE"
    # 0 derece (Kuzey) yönünde 18.52 km -> X = 0.0 km, Y = +18.52 km
    assert math.isclose(target.cartesian_x_km, 0.0, abs_tol=0.01)
    assert math.isclose(target.cartesian_y_km, 18.52, abs_tol=0.01)
    assert target.raw_payload == custom_thermal


def test_mission_computer_collects_targets_polymorphically() -> None:
    """
    MissionComputer sınıfının sensör tipinden bağımsız olarak tüm adaptörlerden
    ortak TargetData listesi topladığını doğrular.
    """
    radar_adapter: TargetSensor = StanagRadarAdapter()
    thermal_adapter: TargetSensor = ThermalCameraAdapter()

    computer = MissionComputer([radar_adapter, thermal_adapter])
    registered = computer.get_registered_sensors()
    assert len(registered) == 2

    targets = computer.collect_all_targets()
    assert len(targets) == 2
    assert all(isinstance(t, TargetData) for t in targets)
    assert targets[0].target_id.startswith("TGT-RAD-")
    assert targets[1].target_id.startswith("TGT-THM-")

    # İkinci okuma döngüsünde TGT-RAD-109 (güven=0.78) ve TGT-THM-214 (güven=0.74) üretilir;
    # 0.75 eşiği yalnızca yüksek güvenli radar hedefini bırakmalıdır.
    high_conf = computer.filter_high_confidence_targets(min_confidence=0.75)
    assert len(high_conf) == 1
    assert high_conf[0].target_id == "TGT-RAD-109"


def test_mission_computer_rejects_unadapted_raw_sensors() -> None:
    """MissionComputer'a doğrudan Adaptee verilmeye çalışıldığında TypeError fırlatıldığını doğrular."""
    computer = MissionComputer()
    raw_radar = LegacyStanagRadarSDK()

    with pytest.raises(TypeError):
        computer.register_sensor(raw_radar)  # type: ignore[arg-type]


def test_stanag_radar_adapter_raises_on_hardware_fault_or_bad_packet() -> None:
    """Radar durum kodu hatalı veya paket bozuk olduğunda SensorIntegrationError fırlatıldığını doğrular."""
    faulty_sdk = LegacyStanagRadarSDK(status_code=0x04)
    adapter = StanagRadarAdapter(faulty_sdk)

    with pytest.raises(SensorIntegrationError, match="donanım arıza kodu"):
        adapter.read_target_data()

    corrupted_sdk = LegacyStanagRadarSDK(custom_blip_buffer="CORRUPTED_DATA_FRAME")
    adapter2 = StanagRadarAdapter(corrupted_sdk)
    with pytest.raises(SensorIntegrationError, match="Geçersiz STANAG"):
        adapter2.read_target_data()


def test_thermal_adapter_raises_on_unhealthy_sensor_or_missing_keys() -> None:
    """Termal kamera sensör sağlığı bozuk veya JSON eksik olduğunda hata fırlatıldığını doğrular."""
    unhealthy_payload = {
        "device_header": {"sensor_health": "COOLER_FAULT"},
        "hotspot": {},
    }
    adapter = ThermalCameraAdapter(VendorThermalDevice(custom_payload=unhealthy_payload))

    with pytest.raises(SensorIntegrationError, match="COOLER_FAULT"):
        adapter.read_target_data()

    incomplete_payload = {
        "device_header": {"sensor_health": "NOMINAL"},
        "hotspot": {"blob_uid": "101"},  # angle_rad vb. eksik
    }
    adapter2 = ThermalCameraAdapter(VendorThermalDevice(custom_payload=incomplete_payload))
    with pytest.raises(SensorIntegrationError, match="eksik veya hatalı"):
        adapter2.read_target_data()
