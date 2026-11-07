"""
Sensör entegrasyonu (Adapter Kalıbı) için ortak hedef veri modeli ve özel hatalar.

Farklı üretici ve protokollere sahip sanal sensörlerin ham verileri,
Adapter sınıfları tarafından bu modüldeki `TargetData` modeline dönüştürülür.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


class SensorIntegrationError(ValueError):
    """
    Harici sensör verisi okunurken, ayrıştırılırken veya sensör donanım durum kodu
    hatalı olduğunda fırlatılan özel istisna sınıfı.
    """


@dataclass(frozen=True)
class TargetData:
    """
    MissionComputer (İstemci) tarafından beklenen standart ve normalize edilmiş hedef verisi.

    Birim Standartları:
    - bearing_deg: [0.0, 360.0) derece (Kuzey = 0°, Saat yönü)
    - distance_km: Kilometre (km)
    - altitude_m: Metre (m)
    - confidence_score: [0.0, 1.0] aralığında normalize güven skoru
    - cartesian_x_km / cartesian_y_km: İHA merkezli 2B Kartezyen koordinatlar (km)
    """

    target_id: str
    source_sensor_name: str
    sensor_protocol: str
    bearing_deg: float
    distance_km: float
    altitude_m: float
    confidence_score: float
    classification: str
    cartesian_x_km: float
    cartesian_y_km: float
    raw_payload: Any
    transformation_notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        """Kullanıcı arayüzü tabloları ve raporlama için sözlük temsili döndürür."""
        return {
            "target_id": self.target_id,
            "source_sensor_name": self.source_sensor_name,
            "sensor_protocol": self.sensor_protocol,
            "bearing_deg": self.bearing_deg,
            "distance_km": self.distance_km,
            "altitude_m": self.altitude_m,
            "confidence_score": self.confidence_score,
            "classification": self.classification,
            "cartesian_x_km": self.cartesian_x_km,
            "cartesian_y_km": self.cartesian_y_km,
            "raw_payload": self.raw_payload,
            "transformation_notes": list(self.transformation_notes),
        }
