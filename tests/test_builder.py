"""
Aşama 2: GoF Builder Kalıbı (İHA Yapılandırması ve Doğrulama) Birim Testleri.
"""

from __future__ import annotations

import pytest

from src.models.uav_models import UAVConfigurationError
from src.patterns.builder import (
    MissionPrepDirector,
    ReconUAVBuilder,
    StrikeUAVBuilder,
    UAVPlatform,
)


def test_director_constructs_valid_standard_recon_uav() -> None:
    """MissionPrepDirector ile standart keşif İHA'sının hatasız oluşturulduğunu doğrular."""
    builder = ReconUAVBuilder()
    director = MissionPrepDirector(builder)

    platform = director.construct_standard_recon_uav()

    assert isinstance(platform, UAVPlatform)
    assert platform.mission_type == "RECON"
    assert platform.model_name == "ANKA-R Standart Keşif"
    assert len(platform.sensors) == 2
    assert len(platform.payloads) == 1
    assert platform.comms_module is not None
    assert platform.total_weight_kg <= platform.max_takeoff_weight_kg
    is_valid, errors = platform.validate()
    assert is_valid is True
    assert errors == []


def test_director_constructs_valid_strike_uavs() -> None:
    """MissionPrepDirector ile standart ve ağır görev taarruz İHA'larının oluşturulduğunu doğrular."""
    builder = StrikeUAVBuilder()
    director = MissionPrepDirector(builder)

    std_strike = director.construct_standard_strike_uav()
    assert std_strike.mission_type == "STRIKE"
    assert std_strike.total_weight_kg <= std_strike.max_takeoff_weight_kg
    assert std_strike.estimated_endurance_hours > 0

    heavy_strike = director.construct_heavy_strike_uav()
    assert heavy_strike.mission_type == "STRIKE"
    assert heavy_strike.total_weight_kg <= heavy_strike.max_takeoff_weight_kg
    assert len(heavy_strike.sensors) == 3
    assert len(heavy_strike.payloads) == 3


def test_builder_resets_cleanly_after_build() -> None:
    """build() çağrısı sonrasında builder iç durumunun sıfırlandığını ve sızıntı yapmadığını doğrular."""
    builder = ReconUAVBuilder()
    director = MissionPrepDirector(builder)

    first = director.construct_long_range_recon_uav()
    assert len(first.sensors) == 3

    draft_after_build = builder.get_draft_platform()
    assert len(draft_after_build.sensors) == 0
    assert len(draft_after_build.payloads) == 0
    assert draft_after_build.comms_module is None


def test_mtow_exceeded_is_rejected() -> None:
    """Maksimum kalkış ağırlığını (MTOW) aşan yapılandırmanın reddedildiğini doğrular."""
    builder = StrikeUAVBuilder()
    # Boş ağırlık: 3300 kg + Yakıt: 1450 kg + 4x Ağır Yük (4*480=1920 kg) + Sensör + Comms > 5500 kg MTOW
    builder.set_airframe("Aşırı Yüklü Test İHA").set_fuel_capacity(1450.0).add_sensor(
        "EO/IR Termal Kamera Podu"
    ).add_payload("Ağır Görev Test Yükü (Sim-500)").add_payload(
        "Ağır Görev Test Yükü (Sim-500)"
    ).add_payload(
        "Ağır Görev Test Yükü (Sim-500)"
    ).set_comms_module(
        "SATCOM Uydu Haberleşme Terminali (Ku-Band)"
    )

    with pytest.raises(UAVConfigurationError) as exc_info:
        builder.build()

    assert any("Maksimum Kalkış Ağırlığı (MTOW) Aşıldı" in err for err in exc_info.value.errors)


def test_incompatible_sensor_and_payload_rejected_for_recon() -> None:
    """Keşif (RECON) İHA'sına taarruz (STRIKE) sensörü veya yükü takıldığında reddedildiğini doğrular."""
    builder = ReconUAVBuilder()
    builder.set_fuel_capacity(300.0).add_sensor(
        "STANAG Atış Kontrol Radarı"  # Sadece STRIKE uyumlu
    ).add_payload(
        "Lazer İşaretleme ve Eğitim Podu"  # Sadece STRIKE uyumlu
    ).set_comms_module(
        "LOS Görüş Hattı Radyo Bağı (UHF/VHF)"
    )

    with pytest.raises(UAVConfigurationError) as exc_info:
        builder.build()

    error_text = " ".join(exc_info.value.errors)
    assert "Uyumsuz Sensör" in error_text
    assert "Uyumsuz Faydalı Yük" in error_text


def test_incompatible_sensor_and_payload_rejected_for_strike() -> None:
    """Taarruz (STRIKE) İHA'sına yalnızca keşif (RECON) uyumlu bileşen takıldığında reddedildiğini doğrular."""
    builder = StrikeUAVBuilder()
    builder.set_fuel_capacity(800.0).add_sensor(
        "Hiperspektral Keşif Kamerası"  # Sadece RECON uyumlu
    ).add_payload(
        "Geniş Alan Haritalama Podu"  # Sadece RECON uyumlu
    ).set_comms_module(
        "LOS Görüş Hattı Radyo Bağı (UHF/VHF)"
    )

    with pytest.raises(UAVConfigurationError) as exc_info:
        builder.build()

    error_text = " ".join(exc_info.value.errors)
    assert "Uyumsuz Sensör" in error_text
    assert "Uyumsuz Faydalı Yük" in error_text


def test_hardpoint_and_sensor_slot_limits_enforced() -> None:
    """İstasyon (hardpoint) kapasitesi aşıldığında veya hiç sensör seçilmediğinde hata verildiğini doğrular."""
    builder = ReconUAVBuilder()  # max_hardpoints = 2
    builder.set_fuel_capacity(250.0).add_payload(
        "Geniş Alan Haritalama Podu"
    ).add_payload("Geniş Alan Haritalama Podu").add_payload(
        "Elektronik Destek (ESM) Karşı Tedbir Podu"
    ).set_comms_module(
        "LOS Görüş Hattı Radyo Bağı (UHF/VHF)"
    )
    # Sensör hiç eklenmedi (0 sensör) ve 3 faydalı yük eklendi (kapasite 2)

    with pytest.raises(UAVConfigurationError) as exc_info:
        builder.build()

    error_text = " ".join(exc_info.value.errors)
    assert "en az 1 sensör" in error_text
    assert "hardpoint" in error_text


def test_fuel_limits_and_missing_comms_enforced() -> None:
    """Minimum/maksimum yakıt sınırlarının ve eksik haberleşme modülünün denetlendiğini doğrular."""
    builder = ReconUAVBuilder()  # min_fuel=120, max_fuel=600
    builder.set_fuel_capacity(50.0).add_sensor("EO/IR Termal Kamera Podu")

    with pytest.raises(UAVConfigurationError) as exc_info:
        builder.build()

    error_text = " ".join(exc_info.value.errors)
    assert "minimum 120 kg yakıt" in error_text
    assert "Haberleşme modülü" in error_text


def test_unknown_catalog_items_raise_configuration_error() -> None:
    """Katalogda bulunmayan sensör, yük veya haberleşme modülü eklendiğinde hata fırlatıldığını doğrular."""
    builder = StrikeUAVBuilder()

    with pytest.raises(UAVConfigurationError):
        builder.add_sensor("Olmayan Radar")

    with pytest.raises(UAVConfigurationError):
        builder.add_payload("Olmayan Yük")

    with pytest.raises(UAVConfigurationError):
        builder.set_comms_module("Olmayan Radyo")


def test_platform_summary_dict() -> None:
    """UAVPlatform.to_summary_dict() çıktısının tüm beklenen anahtarları içerdiğini doğrular."""
    director = MissionPrepDirector(ReconUAVBuilder())
    uav = director.construct_standard_recon_uav()
    summary = uav.to_summary_dict()

    assert summary["is_valid"] is True
    assert summary["mission_type"] == "RECON"
    assert summary["total_weight_kg"] == uav.total_weight_kg
    assert summary["hardpoints_used"] == "1/2"
    assert summary["sensor_slots_used"] == "2/3"
