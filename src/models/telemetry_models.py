"""
Telemetri katmanları (Decorator Kalıbı) için veri modelleri ve özel hatalar.

Sanal telemetri mesajını, her bir dekoratör katmanındaki veri dönüşüm adımını
ve nihai paket sonucunu temsil eden veri sınıflarını içerir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


class TelemetryProcessingError(ValueError):
    """
    Telemetri mesajı işlenirken, şifrelenirken/çözülürken, sıkıştırılırken veya
    CRC/parazit doğrulaması başarısız olduğunda fırlatılan özel istisna sınıfı.
    """


@dataclass(frozen=True)
class TelemetryMessage:
    """
    İHA'dan Yer Kontrol İstasyonu'na (YKİ) gönderilen sentetik telemetri mesajı modeli.
    """

    uav_id: str
    flight_phase: str
    altitude_m: float
    speed_knots: float
    heading_deg: float
    fuel_remaining_kg: float
    latitude: float = 39.9334
    longitude: float = 32.8597
    status_note: str = "NOMINAL_FLIGHT_TELEMETRY"

    def to_payload_string(self) -> str:
        """Telemetri verisini kanal üzerinden gönderilecek JSON dizesine dönüştürür."""
        return json.dumps(
            {
                "uav_id": self.uav_id,
                "phase": self.flight_phase,
                "alt_m": self.altitude_m,
                "spd_kts": self.speed_knots,
                "hdg_deg": self.heading_deg,
                "fuel_kg": self.fuel_remaining_kg,
                "lat": self.latitude,
                "lon": self.longitude,
                "note": self.status_note,
            },
            ensure_ascii=False,
        )


@dataclass(frozen=True)
class TelemetryStageRecord:
    """
    Telemetri mesajının Decorator zincirindeki tek bir katmandan geçerken
    uğradığı dönüşümü kayıt altına alan veri modeli.
    """

    step_index: int
    layer_name: str
    operation_summary: str
    input_data: str
    output_data: str
    input_size_bytes: int
    output_size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Kullanıcı arayüzü gösterimi için sözlük temsili döndürür."""
        return {
            "step_index": self.step_index,
            "layer_name": self.layer_name,
            "operation_summary": self.operation_summary,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "input_size_bytes": self.input_size_bytes,
            "output_size_bytes": self.output_size_bytes,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TelemetryPacketResult:
    """
    Decorator zincirinin tamamlanmasının ardından oluşan nihai telemetri paketi
    ve aşama aşama dönüşüm geçmişi.
    """

    original_payload: str
    final_payload: str
    wrapping_chain: Tuple[str, ...]
    wrapping_expression: str
    stages: Tuple[TelemetryStageRecord, ...]
    original_size_bytes: int
    final_size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        """Arayüz ve raporlama için tüm paket dönüşüm özetini döndürür."""
        return {
            "original_payload": self.original_payload,
            "final_payload": self.final_payload,
            "wrapping_chain": list(self.wrapping_chain),
            "wrapping_expression": self.wrapping_expression,
            "original_size_bytes": self.original_size_bytes,
            "final_size_bytes": self.final_size_bytes,
            "stages": [stage.to_dict() for stage in self.stages],
        }
