"""
GoF Strategy Tasarım Kalıbı (Davranışsal) — Değişken Güdüm ve Rota Planlama Algoritmaları.

Katılımcı Sınıflar:
- Context: NavigationSystem
- Strategy (ABC): RoutePlanningStrategy
- ConcreteStrategy 1: ShortestPathStrategy
- ConcreteStrategy 2: RadarEvasionStrategy (Sentetik Kısıtlı Bölge Kaçınma)
- ConcreteStrategy 3: LoiteringSearchStrategy (Bölge Tarama / Loitering)
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence, Tuple

from src.models.navigation_models import (
    DEFAULT_RESTRICTED_ZONES,
    NavigationPlanningError,
    Point2D,
    RestrictedZone,
    RoutePlan,
)
from src.utils.logger import system_logger


class RoutePlanningStrategy(ABC):
    """
    GoF Strategy Kalıbı — Strategy (Soyut Rota Planlama Arayüzü) Sınıfı.

    NavigationSystem sınıfının somut rota algoritmalarından bağımsız çalışmasını
    sağlayan ortak arayüzü ve yardımcı metrik hesaplamalarını tanımlar.
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Stratejinin benzersiz teknik tanımlayıcısını döndürür."""

    @property
    @abstractmethod
    def strategy_title(self) -> str:
        """Arayüzde gösterilecek okunabilir strateji başlığını döndürür."""

    @abstractmethod
    def plan_route(
        self,
        start: Point2D,
        destination: Point2D,
        restricted_zones: Optional[Sequence[RestrictedZone]] = None,
    ) -> RoutePlan:
        """
        Başlangıç ve hedef noktaları arasında kısıtlı bölgeleri dikkate alarak
        2B rota planı (`RoutePlan`) üretir.
        """

    @staticmethod
    def _validate_endpoints(start: Point2D, destination: Point2D) -> None:
        if not isinstance(start, Point2D) or not isinstance(destination, Point2D):
            raise NavigationPlanningError("Başlangıç ve hedef noktaları Point2D tipinde olmalıdır.")
        if start.distance_to(destination) < 0.1:
            raise NavigationPlanningError(
                "Başlangıç ve hedef noktaları birbirine çok yakın (< 0.1 km)."
            )

    @staticmethod
    def _calculate_total_distance(waypoints: Sequence[Point2D]) -> float:
        if len(waypoints) < 2:
            return 0.0
        total = sum(
            waypoints[i].distance_to(waypoints[i + 1]) for i in range(len(waypoints) - 1)
        )
        return round(total, 2)

    @staticmethod
    def _find_violated_zones(
        waypoints: Sequence[Point2D],
        zones: Sequence[RestrictedZone],
    ) -> Tuple[str, ...]:
        violated: List[str] = []
        for zone in zones:
            for i in range(len(waypoints) - 1):
                if zone.intersects_segment(waypoints[i], waypoints[i + 1]):
                    if zone.zone_id not in violated:
                        violated.append(zone.zone_id)
                    break
        return tuple(violated)


class ShortestPathStrategy(RoutePlanningStrategy):
    """
    GoF Strategy Kalıbı — ConcreteStrategy 1 (En Kısa Rota Stratejisi).

    Başlangıç ve hedef noktaları arasında doğrudan Öklid (kuş uçuşu) doğrusal
    rotası oluşturur. Minimum mesafe ve minimum yakıt tüketimi sağlar; ancak
    yol üzerindeki kısıtlı bölgelerin etrafından dolaşmaz.
    """

    @property
    def strategy_name(self) -> str:
        return "SHORTEST_PATH"

    @property
    def strategy_title(self) -> str:
        return "En Kısa Rota (Shortest Path)"

    def plan_route(
        self,
        start: Point2D,
        destination: Point2D,
        restricted_zones: Optional[Sequence[RestrictedZone]] = None,
    ) -> RoutePlan:
        self._validate_endpoints(start, destination)
        zones = (
            list(restricted_zones)
            if restricted_zones is not None
            else list(DEFAULT_RESTRICTED_ZONES)
        )

        # Doğrusal hat üzerinde 4 eşit segment oluşturan ara kontrol noktaları
        waypoints: List[Point2D] = [
            Point2D(start.x_km, start.y_km, start.label or " Kalkış (Start)")
        ]
        num_segments = 4
        for step in range(1, num_segments):
            ratio = step / num_segments
            wx = round(start.x_km + (destination.x_km - start.x_km) * ratio, 2)
            wy = round(start.y_km + (destination.y_km - start.y_km) * ratio, 2)
            waypoints.append(Point2D(wx, wy, f"WP-{step}"))
        waypoints.append(
            Point2D(destination.x_km, destination.y_km, destination.label or "Hedef (Target)")
        )

        total_dist = self._calculate_total_distance(waypoints)
        # Ortalama seyir hızı: 260 km/s (~140 knots)
        duration_min = round((total_dist / 260.0) * 60.0, 1)
        fuel_kg = round(total_dist * 0.65, 2)
        violated = self._find_violated_zones(waypoints, zones)
        safety_score = round(max(0.0, 1.0 - 0.45 * len(violated)), 2)

        notes = (
            "Doğrudan kuş uçuşu en kısa rota. Minimum mesafe ve yakıt tüketimi sağlar"
            + (
                f"; ancak {list(violated)} kısıtlı bölgelerinden geçmektedir."
                if violated
                else "; kısıtlı bölge ihlali bulunmamaktadır."
            )
        )
        return RoutePlan(
            strategy_name=self.strategy_name,
            strategy_title=self.strategy_title,
            waypoints=tuple(waypoints),
            total_distance_km=total_dist,
            estimated_duration_min=duration_min,
            estimated_fuel_kg=fuel_kg,
            recommended_altitude_m=6000.0,
            violated_zones=violated,
            safety_score=safety_score,
            notes=notes,
        )


class RadarEvasionStrategy(RoutePlanningStrategy):
    """
    GoF Strategy Kalıbı — ConcreteStrategy 2 (Kısıtlı Bölgelerden Kaçınma Stratejisi).

    Not: Bu sınıf gerçek bir radar veya hava savunma sistemi modeli değildir.
    Yalnızca sentetik 2B harita üzerinde işaretlenen dairesel kısıtlı bölgeleri
    (`RestrictedZone`) dikkate alarak güvenli teğet geçiş noktaları (bypass waypoints)
    üreten genel amaçlı geometrik yol planlama algoritmasıdır.
    """

    _SAFETY_MARGIN_KM: float = 4.0

    @property
    def strategy_name(self) -> str:
        return "RADAR_EVASION"

    @property
    def strategy_title(self) -> str:
        return "Kısıtlı Bölgeden Kaçınma (Radar Evasion / Alçak İrtifa)"

    @classmethod
    def compute_safe_waypoints(
        cls,
        start: Point2D,
        destination: Point2D,
        zones: Sequence[RestrictedZone],
    ) -> List[Point2D]:
        """
        Başlangıç ve bitiş noktaları arasındaki doğru parçalarını tarar;
        herhangi bir kısıtlı bölge ile kesişim tespit ederse güvenli çevre
        noktaları ekleyerek tüm bölgelerin etrafından dolaşan rota üretir.
        """
        waypoints: List[Point2D] = [
            Point2D(start.x_km, start.y_km, start.label or "Kalkış (Start)"),
            Point2D(destination.x_km, destination.y_km, destination.label or "Hedef (Target)"),
        ]

        if not zones:
            return waypoints

        alpha_rad = math.radians(35.0)
        cos_a = math.cos(alpha_rad)
        sin_a = math.sin(alpha_rad)
        bypass_counter = 1

        for _iteration in range(12):
            modified = False
            for idx in range(len(waypoints) - 1):
                p1 = waypoints[idx]
                p2 = waypoints[idx + 1]

                # Bu segmenti kesen ilk kısıtlı bölgeyi bul (p1'e en yakın olanı seç)
                intersecting_zones = [
                    z for z in zones if z.intersects_segment(p1, p2, margin_km=0.5)
                ]
                if not intersecting_zones:
                    continue

                intersecting_zones.sort(key=lambda z: p1.distance_to(z.center))
                zone = intersecting_zones[0]

                dx = p2.x_km - p1.x_km
                dy = p2.y_km - p1.y_km
                seg_len = math.hypot(dx, dy)
                if seg_len <= 1e-6:
                    continue

                ux = dx / seg_len
                uy = dy / seg_len
                # İki dik birim normal vektör
                normals = [(-uy, ux), (uy, -ux)]
                safe_dist = (zone.radius_km + cls._SAFETY_MARGIN_KM) / cos_a

                best_pair: Optional[Tuple[Point2D, Point2D]] = None
                best_score: float = float("inf")

                for nx, ny in normals:
                    wa = Point2D(
                        round(zone.center.x_km + safe_dist * (cos_a * nx - sin_a * ux), 2),
                        round(zone.center.y_km + safe_dist * (cos_a * ny - sin_a * uy), 2),
                        f"EVD-{bypass_counter}A",
                    )
                    wb = Point2D(
                        round(zone.center.x_km + safe_dist * (cos_a * nx + sin_a * ux), 2),
                        round(zone.center.y_km + safe_dist * (cos_a * ny + sin_a * uy), 2),
                        f"EVD-{bypass_counter}B",
                    )
                    # Diğer kısıtlı bölgelerin içine düşüp düşmediğini cezalandır
                    penalty = 0.0
                    for other_z in zones:
                        if other_z.contains_point(wa, margin_km=1.0):
                            penalty += 500.0
                        if other_z.contains_point(wb, margin_km=1.0):
                            penalty += 500.0
                        if other_z.intersects_segment(wa, wb, margin_km=0.5):
                            penalty += 300.0

                    detour_len = p1.distance_to(wa) + wa.distance_to(wb) + wb.distance_to(p2)
                    score = detour_len + penalty
                    if score < best_score:
                        best_score = score
                        best_pair = (wa, wb)

                if best_pair is not None:
                    waypoints[idx + 1 : idx + 1] = [best_pair[0], best_pair[1]]
                    bypass_counter += 1
                    modified = True
                    break

            if not modified:
                break

        return waypoints

    def plan_route(
        self,
        start: Point2D,
        destination: Point2D,
        restricted_zones: Optional[Sequence[RestrictedZone]] = None,
    ) -> RoutePlan:
        self._validate_endpoints(start, destination)
        zones = (
            list(restricted_zones)
            if restricted_zones is not None
            else list(DEFAULT_RESTRICTED_ZONES)
        )

        waypoints = self.compute_safe_waypoints(start, destination, zones)
        total_dist = self._calculate_total_distance(waypoints)
        # Alçak irtifa kaçınma hızı: 250 km/s, daha yüksek hava yoğunluğu nedeniyle 0.78 kg/km yakıt
        duration_min = round((total_dist / 250.0) * 60.0, 1)
        fuel_kg = round(total_dist * 0.78, 2)
        violated = self._find_violated_zones(waypoints, zones)
        safety_score = round(max(0.0, 1.0 - 0.5 * len(violated)), 2)

        notes = (
            f"Sentetik haritadaki {len(zones)} kısıtlı bölgeden +{self._SAFETY_MARGIN_KM:.0f} km "
            f"güvenlik marjıyla kaçınan alçak irtifa (1200 m) rotası."
        )
        return RoutePlan(
            strategy_name=self.strategy_name,
            strategy_title=self.strategy_title,
            waypoints=tuple(waypoints),
            total_distance_km=total_dist,
            estimated_duration_min=duration_min,
            estimated_fuel_kg=fuel_kg,
            recommended_altitude_m=1200.0,
            violated_zones=violated,
            safety_score=safety_score,
            notes=notes,
        )


class LoiteringSearchStrategy(RoutePlanningStrategy):
    """
    GoF Strategy Kalıbı — ConcreteStrategy 3 (Bölge Tarama / Loitering Stratejisi).

    Hedef bölgeye güvenli intikal yaptıktan sonra hedef koordinat çevresinde
    sistematik 2B serpantin (biçerdöver / lawnmower) tarama deseni oluşturur.
    Keşif ve gözetleme görevleri için maksimum alan kapsama sağlar.
    """

    def __init__(self, search_width_km: float = 12.0, search_legs: int = 4) -> None:
        self._search_width_km = search_width_km
        self._search_legs = max(2, search_legs)

    @property
    def strategy_name(self) -> str:
        return "LOITERING_SEARCH"

    @property
    def strategy_title(self) -> str:
        return "Bölge Tarama (Loitering Search Pattern)"

    def plan_route(
        self,
        start: Point2D,
        destination: Point2D,
        restricted_zones: Optional[Sequence[RestrictedZone]] = None,
    ) -> RoutePlan:
        self._validate_endpoints(start, destination)
        zones = (
            list(restricted_zones)
            if restricted_zones is not None
            else list(DEFAULT_RESTRICTED_ZONES)
        )

        half_w = self._search_width_km / 2.0
        entry_point = Point2D(
            round(destination.x_km - half_w, 2),
            round(destination.y_km - half_w, 2),
            "TARAMA-GİRİŞ",
        )

        # İntikal safhasında kısıtlı bölgelerden kaçın
        transit_waypoints = RadarEvasionStrategy.compute_safe_waypoints(
            start, entry_point, zones
        )
        waypoints: List[Point2D] = list(transit_waypoints[:-1])

        # Hedef sektör üzerinde serpantin (lawnmower) tarama bacakları oluştur
        step_y = self._search_width_km / (self._search_legs - 1)
        for leg_idx in range(self._search_legs):
            y_coord = round((destination.y_km - half_w) + leg_idx * step_y, 2)
            x_left = round(destination.x_km - half_w, 2)
            x_right = round(destination.x_km + half_w, 2)

            if leg_idx % 2 == 0:
                waypoints.append(Point2D(x_left, y_coord, f"SCN-{leg_idx + 1}L"))
                waypoints.append(Point2D(x_right, y_coord, f"SCN-{leg_idx + 1}R"))
            else:
                waypoints.append(Point2D(x_right, y_coord, f"SCN-{leg_idx + 1}R"))
                waypoints.append(Point2D(x_left, y_coord, f"SCN-{leg_idx + 1}L"))

        # Son olarak hedef merkez noktasına kapanış
        waypoints.append(
            Point2D(
                destination.x_km,
                destination.y_km,
                destination.label or "Hedef Merkez (Target)",
            )
        )

        total_dist = self._calculate_total_distance(waypoints)
        # Tarama hızı daha düşüktür: 210 km/s (~113 knots), ekonomik yakıt: 0.58 kg/km
        duration_min = round((total_dist / 210.0) * 60.0, 1)
        fuel_kg = round(total_dist * 0.58, 2)
        violated = self._find_violated_zones(waypoints, zones)
        safety_score = round(max(0.0, 1.0 - 0.5 * len(violated)), 2)

        notes = (
            f"Hedef sektör çevresinde {self._search_width_km:.0f}x{self._search_width_km:.0f} km "
            f"alanda {self._search_legs} geçişli serpantin bölge tarama (loitering) rotası."
        )
        return RoutePlan(
            strategy_name=self.strategy_name,
            strategy_title=self.strategy_title,
            waypoints=tuple(waypoints),
            total_distance_km=total_dist,
            estimated_duration_min=duration_min,
            estimated_fuel_kg=fuel_kg,
            recommended_altitude_m=4500.0,
            violated_zones=violated,
            safety_score=safety_score,
            notes=notes,
        )


class NavigationSystem:
    """
    GoF Strategy Kalıbı — Context (Bağlam / Navigasyon Sistemi) Sınıfı.

    Aktif rota planlama stratejisini (`RoutePlanningStrategy`) referans olarak
    tutar, çalışma zamanında strateji değişimine (`set_strategy`) izin verir
    ve farklı stratejilerin sonuçlarını karşılaştırır.
    """

    def __init__(self, strategy: Optional[RoutePlanningStrategy] = None) -> None:
        self._strategy: RoutePlanningStrategy = strategy or ShortestPathStrategy()
        system_logger.info(
            "Strategy",
            f"NavigationSystem başlatıldı. Aktif strateji: {self._strategy.strategy_name}.",
        )

    @property
    def strategy(self) -> RoutePlanningStrategy:
        """Aktif RoutePlanningStrategy nesnesini döndürür."""
        return self._strategy

    def set_strategy(self, strategy: RoutePlanningStrategy) -> None:
        """Çalışma zamanında rota hesaplama algoritmasını dinamik olarak değiştirir."""
        if not isinstance(strategy, RoutePlanningStrategy):
            raise TypeError(
                f"Strateji nesnesi RoutePlanningStrategy arayüzünü uygulamalıdır; "
                f"verilen tip: {type(strategy).__name__}"
            )
        old_name = self._strategy.strategy_name
        self._strategy = strategy
        system_logger.info(
            "Strategy",
            f"Navigasyon stratejisi değiştirildi: {old_name} -> {self._strategy.strategy_name}.",
        )

    def calculate_route(
        self,
        start: Point2D,
        destination: Point2D,
        restricted_zones: Optional[Sequence[RestrictedZone]] = None,
    ) -> RoutePlan:
        """Aktif strateji üzerinden 2B rota planını hesaplar ve döndürür."""
        plan = self._strategy.plan_route(start, destination, restricted_zones)
        system_logger.info(
            "Strategy",
            f"[{plan.strategy_name}] Rota hesaplandı: {plan.total_distance_km} km, "
            f"{plan.waypoint_count} nokta, İhlal: {len(plan.violated_zones)}.",
        )
        return plan

    def compare_all_strategies(
        self,
        start: Point2D,
        destination: Point2D,
        restricted_zones: Optional[Sequence[RestrictedZone]] = None,
    ) -> List[RoutePlan]:
        """
        Üç temel rota stratejisinin tamamını aynı harita senaryosu üzerinde
        çalıştırarak karşılaştırma listesi döndürür (aktif stratejiyi bozmaz).
        """
        strategies: List[RoutePlanningStrategy] = [
            ShortestPathStrategy(),
            RadarEvasionStrategy(),
            LoiteringSearchStrategy(),
        ]
        return [s.plan_route(start, destination, restricted_zones) for s in strategies]


STRATEGY_REGISTRY: Dict[str, RoutePlanningStrategy] = {
    "ShortestPathStrategy": ShortestPathStrategy(),
    "RadarEvasionStrategy": RadarEvasionStrategy(),
    "LoiteringSearchStrategy": LoiteringSearchStrategy(),
}
