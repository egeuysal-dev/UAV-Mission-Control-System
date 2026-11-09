"""
Aşama 6: GoF Strategy Kalıbı (Değişken Güdüm ve Rota Planlama Algoritmaları) Birim Testleri.
"""

from __future__ import annotations

import math
import pytest

from src.models.navigation_models import (
    DEFAULT_RESTRICTED_ZONES,
    NavigationPlanningError,
    Point2D,
)
from src.patterns.strategy import (
    LoiteringSearchStrategy,
    NavigationSystem,
    RadarEvasionStrategy,
    ShortestPathStrategy,
)


def test_shortest_path_strategy_computes_direct_euclidean_route() -> None:
    """
    ShortestPathStrategy sınıfının kuş uçuşu en kısa mesafeyi hesapladığını
    ve yol üzerindeki kısıtlı bölge ihlallerini raporladığını doğrular.
    """
    start = Point2D(10.0, 10.0, "Üs")
    dest = Point2D(85.0, 80.0, "Hedef")
    strategy = ShortestPathStrategy()

    plan = strategy.plan_route(start, dest, DEFAULT_RESTRICTED_ZONES)

    expected_dist = math.hypot(85.0 - 10.0, 80.0 - 10.0)
    assert math.isclose(plan.total_distance_km, expected_dist, abs_tol=0.1)
    assert plan.strategy_name == "SHORTEST_PATH"
    assert plan.recommended_altitude_m == 6000.0
    # Doğrudan çizgi merkezdeki kısıtlı bölgeleri keser
    assert len(plan.violated_zones) >= 1
    assert plan.is_safe is False


def test_radar_evasion_strategy_avoids_all_restricted_zones() -> None:
    """
    RadarEvasionStrategy sınıfının kısıtlı bölgelerin etrafından dolaşan
    güvenli (0 ihlalli) bir 2B rota oluşturduğunu doğrular.
    """
    start = Point2D(10.0, 10.0, "Üs")
    dest = Point2D(85.0, 80.0, "Hedef")

    shortest_plan = ShortestPathStrategy().plan_route(start, dest, DEFAULT_RESTRICTED_ZONES)
    evasion_plan = RadarEvasionStrategy().plan_route(start, dest, DEFAULT_RESTRICTED_ZONES)

    assert evasion_plan.strategy_name == "RADAR_EVASION"
    assert evasion_plan.violated_zones == ()
    assert evasion_plan.is_safe is True
    assert evasion_plan.safety_score == 1.0
    assert evasion_plan.recommended_altitude_m == 1200.0
    assert evasion_plan.total_distance_km > shortest_plan.total_distance_km
    assert evasion_plan. waypoints[0].x_km == start.x_km
    assert evasion_plan.waypoints[-1].x_km == dest.x_km


def test_loitering_search_strategy_generates_serpentine_scan_pattern() -> None:
    """
    LoiteringSearchStrategy sınıfının hedef sektör üzerinde çok bacaklı
    bölge tarama (serpantin) rotası oluşturduğunu doğrular.
    """
    start = Point2D(10.0, 10.0, "Üs")
    dest = Point2D(88.0, 82.0, "Keşif Sektörü")
    strategy = LoiteringSearchStrategy(search_width_km=10.0, search_legs=4)

    plan = strategy.plan_route(start, dest, DEFAULT_RESTRICTED_ZONES)

    assert plan.strategy_name == "LOITERING_SEARCH"
    assert plan.recommended_altitude_m == 4500.0
    assert plan.waypoint_count >= 10
    assert plan.is_safe is True
    # Son nokta hedef merkez olmalıdır
    assert plan.waypoints[-1].x_km == dest.x_km
    assert plan.waypoints[-1].y_km == dest.y_km


def test_navigation_system_switches_strategies_dynamically_at_runtime() -> None:
    """
    NavigationSystem bağlam sınıfının çalışma zamanında strateji değiştirebildiğini
    ve tüm stratejileri karşılaştırabildiğini doğrular.
    """
    start = Point2D(10.0, 10.0)
    dest = Point2D(85.0, 80.0)

    nav = NavigationSystem()
    assert isinstance(nav.strategy, ShortestPathStrategy)
    plan1 = nav.calculate_route(start, dest)
    assert plan1.strategy_name == "SHORTEST_PATH"

    # Çalışma zamanında RadarEvasionStrategy'ye geç
    nav.set_strategy(RadarEvasionStrategy())
    plan2 = nav.calculate_route(start, dest)
    assert plan2.strategy_name == "RADAR_EVASION"
    assert plan2.is_safe is True

    # Çalışma zamanında LoiteringSearchStrategy'ye geç
    nav.set_strategy(LoiteringSearchStrategy())
    plan3 = nav.calculate_route(start, dest)
    assert plan3.strategy_name == "LOITERING_SEARCH"

    # 3 stratejinin toplu karşılaştırması
    comparison = nav.compare_all_strategies(start, dest)
    assert len(comparison) == 3
    assert comparison[0].total_distance_km < comparison[1].total_distance_km
    assert comparison[1].total_distance_km < comparison[2].total_distance_km


def test_navigation_system_rejects_invalid_strategy_or_identical_points() -> None:
    """Geçersiz strateji tipinin ve çakışık başlangıç/hedef noktalarının reddedildiğini doğrular."""
    nav = NavigationSystem()

    with pytest.raises(TypeError):
        nav.set_strategy("NotAStrategy")  # type: ignore[arg-type]

    same_pt = Point2D(25.0, 25.0)
    with pytest.raises(NavigationPlanningError):
        nav.calculate_route(same_pt, same_pt)
