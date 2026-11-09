"""
Navigasyon algoritmaları (Strategy Kalıbı) için 2B koordinat, kısıtlı bölge ve rota modelleri.

Sentetik 2B harita üzerindeki başlangıç/hedef noktalarını, dairesel kısıtlı bölgeleri
ve stratejilerin ürettiği karşılaştırılabilir rota planı çıktılarını temsil eder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


class NavigationPlanningError(ValueError):
    """Geçersiz koordinat veya rota planlama parametresi verildiğinde fırlatılan istisna."""


@dataclass(frozen=True)
class Point2D:
    """Sentetik 2B harita üzerindeki (X, Y) kilometre koordinat noktası."""

    x_km: float
    y_km: float
    label: str = ""

    def distance_to(self, other: Point2D) -> float:
        """İki 2B nokta arasındaki Öklid mesafesini (km) hesaplar."""
        return math.hypot(self.x_km - other.x_km, self.y_km - other.y_km)

    def to_dict(self) -> Dict[str, Any]:
        """Noktayı sözlük formatında döndürür."""
        return {"x_km": round(self.x_km, 2), "y_km": round(self.y_km, 2), "label": self.label}


@dataclass(frozen=True)
class RestrictedZone:
    """
    Sentetik 2B harita üzerinde tanımlanmış dairesel kısıtlı / uçuşa kapalı bölge.
    """

    zone_id: str
    name: str
    center: Point2D
    radius_km: float

    def contains_point(self, point: Point2D, margin_km: float = 0.0) -> bool:
        """Verilen noktanın kısıtlı bölge daire sınırları içinde olup olmadığını kontrol eder."""
        return self.center.distance_to(point) < (self.radius_km + margin_km - 1e-6)

    def distance_to_segment(self, p1: Point2D, p2: Point2D) -> float:
        """Bölge merkezinin [p1, p2] doğru parçasına olan en kısa dik mesafesini (km) hesaplar."""
        dx = p2.x_km - p1.x_km
        dy = p2.y_km - p1.y_km
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq <= 1e-9:
            return self.center.distance_to(p1)

        t = ((self.center.x_km - p1.x_km) * dx + (self.center.y_km - p1.y_km) * dy) / seg_len_sq
        t_clamped = max(0.0, min(1.0, t))
        closest_x = p1.x_km + t_clamped * dx
        closest_y = p1.y_km + t_clamped * dy
        return math.hypot(self.center.x_km - closest_x, self.center.y_km - closest_y)

    def intersects_segment(self, p1: Point2D, p2: Point2D, margin_km: float = 0.0) -> bool:
        """[p1, p2] rota segmentinin bu kısıtlı bölgeyi ihlal edip etmediğini döndürür."""
        return self.distance_to_segment(p1, p2) < (self.radius_km + margin_km - 1e-6)

    def to_dict(self) -> Dict[str, Any]:
        """Kısıtlı bölge bilgilerini sözlük olarak döndürür."""
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "center_x_km": self.center.x_km,
            "center_y_km": self.center.y_km,
            "radius_km": self.radius_km,
        }


@dataclass(frozen=True)
class RoutePlan:
    """
    Bir RoutePlanningStrategy tarafından üretilen hesaplanmış 2B rota ve performans metrikleri.
    """

    strategy_name: str
    strategy_title: str
    waypoints: Tuple[Point2D, ...]
    total_distance_km: float
    estimated_duration_min: float
    estimated_fuel_kg: float
    recommended_altitude_m: float
    violated_zones: Tuple[str, ...]
    safety_score: float
    notes: str

    @property
    def waypoint_count(self) -> int:
        """Rota üzerindeki toplam dönüş/kontrol noktası sayısını döndürür."""
        return len(self.waypoints)

    @property
    def is_safe(self) -> bool:
        """Rotanın hiçbir kısıtlı bölgeyi ihlal etmediğini doğrular."""
        return len(self.violated_zones) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Arayüz karşılaştırma tabloları ve grafik çizimi için sözlük temsili döndürür."""
        return {
            "strategy_name": self.strategy_name,
            "strategy_title": self.strategy_title,
            "waypoint_count": self.waypoint_count,
            "waypoints": [wp.to_dict() for wp in self.waypoints],
            "total_distance_km": self.total_distance_km,
            "estimated_duration_min": self.estimated_duration_min,
            "estimated_fuel_kg": self.estimated_fuel_kg,
            "recommended_altitude_m": self.recommended_altitude_m,
            "violated_zones": list(self.violated_zones),
            "is_safe": self.is_safe,
            "safety_score": self.safety_score,
            "notes": self.notes,
        }


# Varsayılan Sentetik Harita Kısıtlı Bölgeleri (100x100 km Harita)
DEFAULT_RESTRICTED_ZONES: Tuple[RestrictedZone, ...] = (
    RestrictedZone(
        zone_id="RZ-ALPHA",
        name="Kısıtlı Bölge Alfa (Merkez Sektör)",
        center=Point2D(42.0, 40.0, "RZ-ALPHA"),
        radius_km=14.0,
    ),
    RestrictedZone(
        zone_id="RZ-BRAVO",
        name="Kısıtlı Bölge Bravo (Kuzeydoğu Sektör)",
        center=Point2D(66.0, 62.0, "RZ-BRAVO"),
        radius_km=11.0,
    ),
)
