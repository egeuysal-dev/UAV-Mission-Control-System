"""
GoF Decorator Tasarım Kalıbı (Yapısal) — Dinamik Telemetri Güvenlik ve İşleme Katmanları.

Python'un `@decorator` fonksiyon sözdizimi yerine, GoF nesne tabanlı sarmalama
(object composition/wrapping) kalıbı uygulanmıştır.

Katılımcı Sınıflar:
- Component (ABC): TelemetryChannel
- ConcreteComponent: BaseRadioChannel
- Decorator (ABC): TelemetryChannelDecorator
- ConcreteDecorator 1: AesEncryptionDecorator
- ConcreteDecorator 2: CompressionDecorator
- ConcreteDecorator 3: AntiJammingDecorator
"""

from __future__ import annotations

import base64
import binascii
import os
import zlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.models.telemetry_models import (
    TelemetryPacketResult,
    TelemetryProcessingError,
    TelemetryStageRecord,
)
from src.utils.logger import system_logger


class TelemetryChannel(ABC):
    """
    GoF Decorator Kalıbı — Component (Soyut Bileşen Arayüzü) Sınıfı.

    Hem temel radyo kanalı (`BaseRadioChannel`) hem de tüm dekoratör katmanları
    (`TelemetryChannelDecorator` alt sınıfları) bu arayüzü uygular.
    """

    @abstractmethod
    def transmit(self, payload: str) -> TelemetryPacketResult:
        """
        Telemetri mesajını kanal ve sarmalayıcı katmanlar üzerinden işleyerek
        aşama kayıtlarını içeren `TelemetryPacketResult` döndürür.
        """

    @abstractmethod
    def receive(self, frame: str) -> str:
        """
        İletilen çerçeveyi (frame) dış katmandan iç katmana doğru çözerek
        orijinal telemetri mesajını geri elde eder.
        """

    @abstractmethod
    def get_pipeline_layers(self) -> List[str]:
        """İçten dışa doğru aktif nesne sarmalama zincirindeki sınıf isimlerini döndürür."""

    @abstractmethod
    def format_wrapping_chain(self) -> str:
        """Nesne sarmalama yapısını `Outer(Inner(BaseRadioChannel))` biçiminde metinleştirir."""


class BaseRadioChannel(TelemetryChannel):
    """
    GoF Decorator Kalıbı — ConcreteComponent (Somut Temel Bileşen) Sınıfı.

    Hiçbir ek şifreleme, sıkıştırma veya parazit koruma katmanı olmadan
    temel radyo frekansı üzerinden ham telemetri paketi oluşturan çekirdek sınıf.
    """

    def __init__(self, frequency_band: str = "UHF-433MHz") -> None:
        self._frequency_band = frequency_band

    @property
    def frequency_band(self) -> str:
        """Radyo kanalının frekans bandı bilgisini döndürür."""
        return self._frequency_band

    def get_pipeline_layers(self) -> List[str]:
        """Temel kanalın tek elemanlı katman listesini döndürür."""
        return [self.__class__.__name__]

    def format_wrapping_chain(self) -> str:
        """Temel kanalın sınıf adını döndürür."""
        return f"{self.__class__.__name__}({self._frequency_band})"

    def transmit(self, payload: str) -> TelemetryPacketResult:
        """Ham telemetri mesajını temel radyo çerçevesine dönüştürür."""
        if not isinstance(payload, str) or not payload.strip():
            raise TelemetryProcessingError("Telemetri mesajı boş olamaz.")

        prefix = f"RAW_RADIO[{self._frequency_band}]:"
        framed_output = f"{prefix}{payload}"
        in_bytes = len(payload.encode("utf-8"))
        out_bytes = len(framed_output.encode("utf-8"))

        stage = TelemetryStageRecord(
            step_index=0,
            layer_name=self.__class__.__name__,
            operation_summary=f"Temel Radyo Çerçeveleme ({self._frequency_band})",
            input_data=payload,
            output_data=framed_output,
            input_size_bytes=in_bytes,
            output_size_bytes=out_bytes,
            metadata={"frequency_band": self._frequency_band},
        )
        chain = tuple(self.get_pipeline_layers())
        expr = self.format_wrapping_chain()
        system_logger.info(
            "Decorator",
            f"[BaseRadioChannel] Ham telemetri çerçevesi oluşturuldu ({out_bytes} bayt).",
        )
        return TelemetryPacketResult(
            original_payload=payload,
            final_payload=framed_output,
            wrapping_chain=chain,
            wrapping_expression=expr,
            stages=(stage,),
            original_size_bytes=in_bytes,
            final_size_bytes=out_bytes,
        )

    def receive(self, frame: str) -> str:
        """Temel radyo çerçeve başlığını kaldırarak ham mesajı döndürür."""
        prefix = f"RAW_RADIO[{self._frequency_band}]:"
        if not frame.startswith(prefix):
            raise TelemetryProcessingError(
                f"BaseRadioChannel başlığı uyuşmuyor (beklenen: '{prefix}')."
            )
        return frame[len(prefix) :]


class TelemetryChannelDecorator(TelemetryChannel):
    """
    GoF Decorator Kalıbı — Decorator (Soyut Sarmalayıcı) Sınıfı.

    Bir `TelemetryChannel` nesnesini kompozisyon (nesne referansı) yoluyla
    sarmalar ve alt dekoratör sınıflar için ortak şablon davranışını tanımlar.
    """

    def __init__(self, wrapped_channel: TelemetryChannel) -> None:
        if not isinstance(wrapped_channel, TelemetryChannel):
            raise TypeError(
                f"TelemetryChannelDecorator yalnızca TelemetryChannel nesnelerini sarmalayabilir; "
                f"verilen tip: {type(wrapped_channel).__name__}"
            )
        self._wrapped_channel: TelemetryChannel = wrapped_channel

    @property
    def wrapped_channel(self) -> TelemetryChannel:
        """Sarmalanan iç TelemetryChannel nesnesini döndürür."""
        return self._wrapped_channel

    def set_wrapped_channel(self, channel: TelemetryChannel) -> None:
        """Katman kaldırma veya yeniden sıralama işlemlerinde iç referansı günceller."""
        if not isinstance(channel, TelemetryChannel):
            raise TypeError("Sarmalanacak nesne TelemetryChannel arayüzünü uygulamalıdır.")
        self._wrapped_channel = channel

    def get_pipeline_layers(self) -> List[str]:
        """İç katmanların listesine kendi sınıf adını ekleyerek döndürür."""
        return self._wrapped_channel.get_pipeline_layers() + [self.__class__.__name__]

    def format_wrapping_chain(self) -> str:
        """Sarmalama zincirini iç içe fonksiyon/nesne gösterimiyle döndürür."""
        return f"{self.__class__.__name__}({self._wrapped_channel.format_wrapping_chain()})"

    @abstractmethod
    def _apply_layer(self, input_data: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Alt dekoratör sınıfın kendi veri dönüşümünü uyguladığı soyut metot.

        Returns:
            (output_data, operation_summary, metadata)
        """

    @abstractmethod
    def _reverse_layer(self, framed_data: str) -> str:
        """
        Alt dekoratör sınıfın kendi dönüşümünü tersine çevirdiği (çözdüğü) soyut metot.
        """

    def transmit(self, payload: str) -> TelemetryPacketResult:
        """
        Önce sarmalanan iç kanalın `transmit` işlemini çalıştırır, ardından
        elde edilen çıktıya kendi katman dönüşümünü ekleyerek yeni aşamayı kaydeder.
        """
        inner_result = self._wrapped_channel.transmit(payload)
        current_input = inner_result.final_payload
        in_bytes = len(current_input.encode("utf-8"))

        transformed_output, summary, metadata = self._apply_layer(current_input)
        out_bytes = len(transformed_output.encode("utf-8"))
        step_idx = len(inner_result.stages)

        new_stage = TelemetryStageRecord(
            step_index=step_idx,
            layer_name=self.__class__.__name__,
            operation_summary=summary,
            input_data=current_input,
            output_data=transformed_output,
            input_size_bytes=in_bytes,
            output_size_bytes=out_bytes,
            metadata=metadata,
        )

        chain = tuple(self.get_pipeline_layers())
        expr = self.format_wrapping_chain()
        system_logger.info(
            "Decorator",
            f"[{self.__class__.__name__}] Katman #{step_idx} uygulandı ({in_bytes}B -> {out_bytes}B).",
        )
        return TelemetryPacketResult(
            original_payload=inner_result.original_payload,
            final_payload=transformed_output,
            wrapping_chain=chain,
            wrapping_expression=expr,
            stages=inner_result.stages + (new_stage,),
            original_size_bytes=inner_result.original_size_bytes,
            final_size_bytes=out_bytes,
        )

    def receive(self, frame: str) -> str:
        """
        Dış katmandan başlayarak kendi dönüşümünü tersine çevirir ve
        elde edilen veriyi sarmalanan iç kanala iletir.
        """
        inner_frame = self._reverse_layer(frame)
        return self._wrapped_channel.receive(inner_frame)


class CompressionDecorator(TelemetryChannelDecorator):
    """
    GoF Decorator Kalıbı — ConcreteDecorator 1 (Veri Sıkıştırma Katmanı).

    Telemetri verisini `zlib` (DEFLATE) algoritmasıyla sıkıştırır ve güvenli
    metin aktarımı için Base64 formatında kodlar.
    """

    _PREFIX: str = "ZLIB_B64:"

    def __init__(
        self,
        wrapped_channel: TelemetryChannel,
        compression_level: int = 6,
    ) -> None:
        super().__init__(wrapped_channel)
        if not (1 <= compression_level <= 9):
            raise ValueError("Sıkıştırma seviyesi 1 ile 9 arasında olmalıdır.")
        self._compression_level = compression_level

    def _apply_layer(self, input_data: str) -> Tuple[str, str, Dict[str, Any]]:
        raw_bytes = input_data.encode("utf-8")
        compressed_bytes = zlib.compress(raw_bytes, level=self._compression_level)
        encoded_b64 = base64.b64encode(compressed_bytes).decode("ascii")
        output_data = f"{self._PREFIX}{encoded_b64}"

        raw_len = len(raw_bytes)
        comp_len = len(compressed_bytes)
        ratio_pct = round((comp_len / raw_len) * 100.0, 1) if raw_len > 0 else 100.0

        summary = (
            f"ZLIB Sıkıştırma (Seviye {self._compression_level}): "
            f"Ham {raw_len}B -> Sıkıştırılmış {comp_len}B (%{ratio_pct}) + Base64"
        )
        metadata = {
            "algorithm": "DEFLATE (zlib)",
            "compression_level": self._compression_level,
            "raw_bytes": raw_len,
            "compressed_raw_bytes": comp_len,
            "compression_ratio_pct": ratio_pct,
        }
        return output_data, summary, metadata

    def _reverse_layer(self, framed_data: str) -> str:
        if not framed_data.startswith(self._PREFIX):
            raise TelemetryProcessingError(
                f"CompressionDecorator başlığı bulunamadı (beklenen: '{self._PREFIX}')."
            )
        b64_part = framed_data[len(self._PREFIX) :]
        try:
            compressed_bytes = base64.b64decode(b64_part.encode("ascii"), validate=True)
            decompressed_bytes = zlib.decompress(compressed_bytes)
            return decompressed_bytes.decode("utf-8")
        except (binascii.Error, zlib.error, UnicodeDecodeError) as exc:
            raise TelemetryProcessingError(f"Sıkıştırılmış telemetri verisi çözülemedi: {exc}") from exc


class AesEncryptionDecorator(TelemetryChannelDecorator):
    """
    GoF Decorator Kalıbı — ConcreteDecorator 2 (AES-256-GCM Şifreleme Katmanı).

    `cryptography` kütüphanesinin `AESGCM` sınıfını kullanarak gerçek kimlik
    doğrulamalı AES-256-GCM şifrelemesi uygular.

    Güvenlik Prensibi:
    Kaynak kod içerisine hiçbir sabit anahtar gömülmemiştir. Anahtar parametre
    olarak verilmezse önce `UAV_TELEMETRY_AES_KEY_B64` ortam değişkenine bakılır;
    tanımlı değilse çalışma zamanında kriptografik olarak güvenli `AESGCM.generate_key(256)`
    ile dinamik oturum anahtarı üretilir.
    """

    _PREFIX: str = "AES256GCM:"

    def __init__(
        self,
        wrapped_channel: TelemetryChannel,
        key: Optional[bytes] = None,
    ) -> None:
        super().__init__(wrapped_channel)
        self._key: bytes = self._resolve_or_generate_key(key)
        self._aesgcm: AESGCM = AESGCM(self._key)

    @staticmethod
    def _resolve_or_generate_key(explicit_key: Optional[bytes]) -> bytes:
        """
        Çalışma zamanı AES-256 anahtarını doğrular, ortam değişkeninden okur
        veya `os.urandom` tabanlı `AESGCM.generate_key` ile dinamik üretir.
        """
        if explicit_key is not None:
            if len(explicit_key) not in (16, 24, 32):
                raise ValueError("AES anahtarı 16, 24 veya 32 bayt (128/192/256 bit) olmalıdır.")
            return explicit_key

        env_key_b64 = os.environ.get("UAV_TELEMETRY_AES_KEY_B64")
        if env_key_b64:
            decoded = base64.b64decode(env_key_b64)
            if len(decoded) not in (16, 24, 32):
                raise ValueError("UAV_TELEMETRY_AES_KEY_B64 geçerli bir AES anahtar uzunluğunda değil.")
            return decoded

        return AESGCM.generate_key(bit_length=256)

    @property
    def session_key(self) -> bytes:
        """Testlerde alıcı-verici eşleşmesi için oturum anahtarına erişim sağlar."""
        return self._key

    def _apply_layer(self, input_data: str) -> Tuple[str, str, Dict[str, Any]]:
        nonce = os.urandom(12)  # 96-bit GCM standart nonce
        plaintext_bytes = input_data.encode("utf-8")
        ciphertext_with_tag = self._aesgcm.encrypt(nonce, plaintext_bytes, associated_data=None)

        nonce_b64 = base64.b64encode(nonce).decode("ascii")
        cipher_b64 = base64.b64encode(ciphertext_with_tag).decode("ascii")
        output_data = f"{self._PREFIX}{nonce_b64}:{cipher_b64}"

        key_bits = len(self._key) * 8
        nonce_hex_preview = nonce.hex()[:8]
        summary = (
            f"AES-{key_bits}-GCM Şifreleme (Nonce: {nonce_hex_preview}..., "
            f"128-bit GCM Bütünlük Etiketi)"
        )
        metadata = {
            "cipher": f"AES-{key_bits}-GCM",
            "nonce_bits": 96,
            "nonce_hex_preview": nonce_hex_preview,
            "auth_tag_bits": 128,
            "key_source": "RUNTIME_DYNAMIC",
        }
        return output_data, summary, metadata

    def _reverse_layer(self, framed_data: str) -> str:
        if not framed_data.startswith(self._PREFIX):
            raise TelemetryProcessingError(
                f"AesEncryptionDecorator başlığı bulunamadı (beklenen: '{self._PREFIX}')."
            )
        body = framed_data[len(self._PREFIX) :]
        parts = body.split(":", 1)
        if len(parts) != 2:
            raise TelemetryProcessingError("AES256GCM çerçeve formatı geçersiz (nonce:ciphertext bekleniyordu).")

        nonce_b64, cipher_b64 = parts
        try:
            nonce = base64.b64decode(nonce_b64.encode("ascii"), validate=True)
            ciphertext = base64.b64decode(cipher_b64.encode("ascii"), validate=True)
            plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            return plaintext_bytes.decode("utf-8")
        except (binascii.Error, InvalidTag, ValueError, UnicodeDecodeError) as exc:
            raise TelemetryProcessingError(
                f"AES-GCM şifre çözme veya bütünlük doğrulaması başarısız oldu: {exc}"
            ) from exc


class AntiJammingDecorator(TelemetryChannelDecorator):
    """
    GoF Decorator Kalıbı — ConcreteDecorator 3 (Temsili Parazit ve Hata Düzeltme Katmanı).

    Not: Bu sınıf gerçek radyo frekansı veya elektronik harp algoritması içermez.
    Yalnızca eğitim amaçlı olarak CRC32 sağlama toplamı (checksum), temsili parazit
    (bit/karakter bozulması) enjeksiyonu ve yedekli blok (FEC simülasyonu) ile
    hata kurtarma davranışını modeller.
    """

    _PREFIX: str = "AJ_FEC|"

    def __init__(
        self,
        wrapped_channel: TelemetryChannel,
        simulate_interference: bool = False,
    ) -> None:
        super().__init__(wrapped_channel)
        self._simulate_interference = simulate_interference

    @property
    def simulate_interference(self) -> bool:
        """Temsili parazit enjeksiyonu simülasyonunun aktif olup olmadığını döndürür."""
        return self._simulate_interference

    def _apply_layer(self, input_data: str) -> Tuple[str, str, Dict[str, Any]]:
        raw_bytes = input_data.encode("utf-8")
        crc_value = zlib.crc32(raw_bytes) & 0xFFFFFFFF
        crc_hex = f"{crc_value:08X}"

        # Temsili FEC yedek (parity/recovery) bloğu
        fec_backup_b64 = base64.b64encode(raw_bytes).decode("ascii")

        errors_fixed = 0
        if self._simulate_interference and len(raw_bytes) > 0:
            # Temsili olarak ilk baytın terslenerek bozulduğunu ve FEC yedek bloğu
            # artı CRC32 kontrolüyle otomatik onarıldığını simüle et
            corrupted_sample = bytearray(raw_bytes)
            corrupted_sample[0] ^= 0xFF
            corrupted_crc = zlib.crc32(bytes(corrupted_sample)) & 0xFFFFFFFF
            if corrupted_crc != crc_value:
                recovered_bytes = base64.b64decode(fec_backup_b64.encode("ascii"))
                assert (zlib.crc32(recovered_bytes) & 0xFFFFFFFF) == crc_value
                errors_fixed = 1

        output_data = (
            f"{self._PREFIX}CRC32:{crc_hex}|FEC:{fec_backup_b64}|FIXED:{errors_fixed}|{input_data}"
        )

        if errors_fixed > 0:
            summary = (
                f"Anti-Jamming CRC32 ({crc_hex}) + Temsili FEC: "
                f"1 simüle edilmiş kanal hatası tespit edildi ve onarıldı"
            )
        else:
            summary = f"Anti-Jamming CRC32 ({crc_hex}) + Temsili FEC Koruma Bloğu Eklendi"

        metadata = {
            "crc32_hex": crc_hex,
            "simulated_interference": self._simulate_interference,
            "simulated_errors_fixed": errors_fixed,
            "fec_redundancy_active": True,
        }
        return output_data, summary, metadata

    def _reverse_layer(self, framed_data: str) -> str:
        if not framed_data.startswith(self._PREFIX):
            raise TelemetryProcessingError(
                f"AntiJammingDecorator başlığı bulunamadı (beklenen: '{self._PREFIX}')."
            )

        parts = framed_data.split("|", 4)
        if len(parts) != 5:
            raise TelemetryProcessingError("AntiJammingDecorator çerçeve yapısı bozuk.")

        _, crc_token, fec_token, _fixed_token, payload = parts
        if not crc_token.startswith("CRC32:") or not fec_token.startswith("FEC:"):
            raise TelemetryProcessingError("AntiJammingDecorator CRC32 veya FEC alanı eksik.")

        expected_crc_hex = crc_token.split(":", 1)[1]
        fec_b64 = fec_token.split(":", 1)[1]

        actual_crc_val = zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF
        actual_crc_hex = f"{actual_crc_val:08X}"

        if actual_crc_hex == expected_crc_hex:
            return payload

        # Gövde bozulmuşsa temsili FEC yedek bloğundan kurtarmayı dene
        try:
            recovered_bytes = base64.b64decode(fec_b64.encode("ascii"), validate=True)
            recovered_crc_hex = f"{(zlib.crc32(recovered_bytes) & 0xFFFFFFFF):08X}"
            if recovered_crc_hex == expected_crc_hex:
                system_logger.warning(
                    "Decorator",
                    f"[AntiJammingDecorator] CRC uyuşmazlığı ({actual_crc_hex} != {expected_crc_hex}) "
                    f"temsili FEC bloğu ile onarıldı.",
                )
                return recovered_bytes.decode("utf-8")
        except Exception as exc:
            raise TelemetryProcessingError(
                "AntiJammingDecorator: Bozuk paket FEC ile kurtarılamadı."
            ) from exc

        raise TelemetryProcessingError(
            f"AntiJammingDecorator: CRC32 doğrulaması başarısız ({actual_crc_hex} != {expected_crc_hex}) "
            f"ve FEC kurtarma bloğu geçersiz."
        )


# Dinamik Katman Yönetimi Yardımcıları (Sıra Değiştirme / Katman Ekleme-Çıkarma)
DECORATOR_REGISTRY: Dict[str, Type[TelemetryChannelDecorator]] = {
    "CompressionDecorator": CompressionDecorator,
    "AesEncryptionDecorator": AesEncryptionDecorator,
    "AntiJammingDecorator": AntiJammingDecorator,
}


def build_telemetry_chain(
    layer_names: List[str],
    frequency_band: str = "UHF-433MHz",
    aes_key: Optional[bytes] = None,
    simulate_interference: bool = False,
) -> TelemetryChannel:
    """
    Verilen katman isimleri listesine göre çalışma zamanında `BaseRadioChannel`
    üzerine istenilen sırada Decorator zinciri inşa eder.
    """
    channel: TelemetryChannel = BaseRadioChannel(frequency_band=frequency_band)
    for name in layer_names:
        if name not in DECORATOR_REGISTRY:
            raise TelemetryProcessingError(
                f"Bilinmeyen telemetri dekoratörü: '{name}'. "
                f"Geçerli katmanlar: {list(DECORATOR_REGISTRY.keys())}"
            )
        if name == "CompressionDecorator":
            channel = CompressionDecorator(channel)
        elif name == "AesEncryptionDecorator":
            channel = AesEncryptionDecorator(channel, key=aes_key)
        elif name == "AntiJammingDecorator":
            channel = AntiJammingDecorator(channel, simulate_interference=simulate_interference)
    return channel


def remove_decorator_layer(
    channel: TelemetryChannel,
    layer_to_remove: Union[str, Type[TelemetryChannelDecorator]],
) -> TelemetryChannel:
    """
    Mevcut bir Decorator sarmalama zincirinden belirtilen katmanı (sınıf adı veya
    sınıf tipi ile) çalışma zamanında çıkarır ve kalan zinciri koruyarak döndürür.
    """
    target_name = (
        layer_to_remove if isinstance(layer_to_remove, str) else layer_to_remove.__name__
    )

    # İçten dışa tüm dekoratör nesnelerini topla
    decorators: List[TelemetryChannelDecorator] = []
    cursor: TelemetryChannel = channel
    while isinstance(cursor, TelemetryChannelDecorator):
        decorators.append(cursor)
        cursor = cursor.wrapped_channel

    base_channel = cursor
    # İçten dışa sırala ve çıkarılmak istenen katmanı filtrele
    decorators.reverse()
    remaining = [d for d in decorators if d.__class__.__name__ != target_name]

    rebuilt: TelemetryChannel = base_channel
    for dec in remaining:
        dec.set_wrapped_channel(rebuilt)
        rebuilt = dec
    return rebuilt
