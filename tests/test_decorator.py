"""
Aşama 4: GoF Decorator Kalıbı (Dinamik Telemetri Katmanları) Birim Testleri.
"""

from __future__ import annotations

import pytest

from src.models.telemetry_models import TelemetryMessage, TelemetryProcessingError
from src.patterns.decorator import (
    AesEncryptionDecorator,
    AntiJammingDecorator,
    BaseRadioChannel,
    CompressionDecorator,
    TelemetryChannel,
    build_telemetry_chain,
    remove_decorator_layer,
)


def _sample_telemetry_payload() -> str:
    msg = TelemetryMessage(
        uav_id="ANKA-R-01",
        flight_phase="CRUISE",
        altitude_m=6500.0,
        speed_knots=135.0,
        heading_deg=120.0,
        fuel_remaining_kg=310.5,
        status_note="NOMINAL_FLIGHT_TELEMETRY " * 4,
    )
    return msg.to_payload_string()


def test_base_radio_channel_transmit_and_receive() -> None:
    """BaseRadioChannel sınıfının tek başına mesaj iletip geri çözebildiğini doğrular."""
    channel = BaseRadioChannel(frequency_band="UHF-433MHz")
    payload = _sample_telemetry_payload()

    result = channel.transmit(payload)
    assert len(result.stages) == 1
    assert result.wrapping_chain == ("BaseRadioChannel",)
    assert result.final_payload.startswith("RAW_RADIO[UHF-433MHz]:")

    recovered = channel.receive(result.final_payload)
    assert recovered == payload


def test_empty_telemetry_payload_raises_error() -> None:
    """Boş telemetri mesajı gönderildiğinde TelemetryProcessingError fırlatıldığını doğrular."""
    channel = BaseRadioChannel()
    with pytest.raises(TelemetryProcessingError):
        channel.transmit("   ")


def test_full_decorator_chain_stage_by_stage_and_roundtrip() -> None:
    """
    Üç dekoratör katmanının (Compression -> AES -> AntiJamming) nesne sarmalama zincirini,
    her aşamadaki veri dönüşüm kaydını ve kayıpsız geri çözmeyi (receive) doğrular.
    """
    payload = _sample_telemetry_payload()

    channel: TelemetryChannel = BaseRadioChannel("SATCOM-Ku")
    channel = CompressionDecorator(channel)
    channel = AesEncryptionDecorator(channel)
    channel = AntiJammingDecorator(channel, simulate_interference=True)

    assert channel.get_pipeline_layers() == [
        "BaseRadioChannel",
        "CompressionDecorator",
        "AesEncryptionDecorator",
        "AntiJammingDecorator",
    ]
    assert channel.format_wrapping_chain() == (
        "AntiJammingDecorator(AesEncryptionDecorator("
        "CompressionDecorator(BaseRadioChannel(SATCOM-Ku))))"
    )

    result = channel.transmit(payload)
    assert len(result.stages) == 4

    # Her katmanın çıktısı bir sonraki katmanın girdisi olmalıdır
    for idx in range(len(result.stages) - 1):
        assert result.stages[idx].output_data == result.stages[idx + 1].input_data

    assert result.stages[1].layer_name == "CompressionDecorator"
    assert result.stages[2].layer_name == "AesEncryptionDecorator"
    assert result.stages[3].layer_name == "AntiJammingDecorator"
    assert result.stages[3].metadata["simulated_errors_fixed"] == 1

    # Dıştan içe çözme (AntiJamming -> AES -> Compression -> BaseRadioChannel)
    recovered = channel.receive(result.final_payload)
    assert recovered == payload


def test_decorator_layer_order_changes_output_and_packet_size() -> None:
    """
    Katman sırasının değiştirilmesinin (Önce Sıkıştırma vs Önce Şifreleme)
    nihai çıktıyı ve paket boyutunu etkilediğini doğrular.
    """
    payload = _sample_telemetry_payload()

    # Sıra 1: Önce Sıkıştırma, Sonra AES Şifreleme (Optimal sıra)
    chain_compress_first = build_telemetry_chain(
        ["CompressionDecorator", "AesEncryptionDecorator"]
    )
    res1 = chain_compress_first.transmit(payload)

    # Sıra 2: Önce AES Şifreleme, Sonra Sıkıştırma (Yüksek entropili şifreli veri sıkışmaz)
    chain_encrypt_first = build_telemetry_chain(
        ["AesEncryptionDecorator", "CompressionDecorator"]
    )
    res2 = chain_encrypt_first.transmit(payload)

    assert res1.wrapping_chain != res2.wrapping_chain
    assert res1.final_payload != res2.final_payload
    assert res1.final_size_bytes < res2.final_size_bytes
    assert chain_compress_first.receive(res1.final_payload) == payload
    assert chain_encrypt_first.receive(res2.final_payload) == payload


def test_remove_and_readd_decorator_layer_dynamically() -> None:
    """
    Çalışma zamanında sarmalama zincirinden bir katmanın çıkarılıp
    yeniden farklı bir konuma eklenebildiğini doğrular.
    """
    payload = _sample_telemetry_payload()
    channel = build_telemetry_chain(
        ["CompressionDecorator", "AesEncryptionDecorator", "AntiJammingDecorator"]
    )

    # Ortadaki AesEncryptionDecorator katmanını çıkar
    without_aes = remove_decorator_layer(channel, "AesEncryptionDecorator")
    assert without_aes.get_pipeline_layers() == [
        "BaseRadioChannel",
        "CompressionDecorator",
        "AntiJammingDecorator",
    ]
    res_no_aes = without_aes.transmit(payload)
    assert "AES256GCM:" not in res_no_aes.final_payload
    assert without_aes.receive(res_no_aes.final_payload) == payload

    # AES katmanını en dışa yeniden ekle
    re_added_aes = AesEncryptionDecorator(without_aes)
    assert re_added_aes.get_pipeline_layers() == [
        "BaseRadioChannel",
        "CompressionDecorator",
        "AntiJammingDecorator",
        "AesEncryptionDecorator",
    ]
    res_re_added = re_added_aes.transmit(payload)
    assert res_re_added.final_payload.startswith("AES256GCM:")
    assert re_added_aes.receive(res_re_added.final_payload) == payload


def test_aes_encryption_detects_tampering_and_uses_dynamic_keys() -> None:
    """
    AES-256-GCM katmanının her örnekte dinamik anahtar ürettiğini ve
    şifreli veri değiştirildiğinde bütünlük hatası fırlattığını doğrular.
    """
    base = BaseRadioChannel()
    enc1 = AesEncryptionDecorator(base)
    enc2 = AesEncryptionDecorator(base)

    assert len(enc1.session_key) == 32
    assert enc1.session_key != enc2.session_key

    packet = enc1.transmit("GIZLI_KOMUT_PAKETI")
    # Farklı anahtara sahip alıcı çözememelidir
    with pytest.raises(TelemetryProcessingError, match="AES-GCM"):
        enc2.receive(packet.final_payload)

    # Şifreli metnin son karakterini bozarak GCM etiket doğrulamasını test et
    tampered = packet.final_payload[:-4] + "AAAA"
    with pytest.raises(TelemetryProcessingError, match="AES-GCM"):
        enc1.receive(tampered)


def test_antijamming_fec_recovers_corrupted_payload_or_fails_if_unrecoverable() -> None:
    """
    AntiJammingDecorator'ün iletim sırasında bozulan gövdeyi FEC bloğu ile kurtardığını,
    hem gövde hem FEC bozulursa TelemetryProcessingError fırlattığını doğrular.
    """
    channel = AntiJammingDecorator(BaseRadioChannel())
    payload = "TELEMETRY_TEST_DATA"
    packet = channel.transmit(payload)

    # Paketin sonundaki gövde kısmını boz (FEC kısmı sağlam kalsın)
    corrupted_frame = packet.final_payload.replace("TELEMETRY_TEST_DATA", "CORRUPTED_XXXX_DATA")
    recovered = channel.receive(corrupted_frame)
    assert recovered == payload

    # Hem gövdeyi hem FEC bloğunu boz -> kurtarılamaz hata
    unrecoverable_frame = corrupted_frame.replace("|FEC:", "|FEC:INVALID_B64_")
    with pytest.raises(TelemetryProcessingError):
        channel.receive(unrecoverable_frame)
