"""
Aşama 7: Simülasyon Orkestratörü (MissionSimulator) ve Görselleştirme (Plotly) Testleri.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src.models.flight_state_models import FlightCommands
from src.patterns.strategy import ShortestPathStrategy
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import (
    create_flight_dynamics_chart,
    create_route_map_2d_chart,
    create_sensor_polar_and_cartesian_charts,
    create_telemetry_stage_size_chart,
    create_weight_breakdown_chart,
)


def test_mission_simulator_end_to_end_initialization_and_tick() -> None:
    """
    MissionSimulator sınıfının 5 GoF kalıbını birleştirerek başlatıldığını
    ve simülasyon döngüsünü (tick) uçtan uca çalıştırdığını doğrular.
    """
    sim = MissionSimulator()

    assert sim.active_platform.mission_type == "RECON"
    assert sim.flight_controller.current_phase_name == "PREFLIGHT_IDLE"
    assert sim.last_route_plan is not None
    assert sim.last_telemetry_packet is not None

    tick1 = sim.run_simulation_tick()
    assert tick1["tick"] == 1
    assert tick1["targets_collected"] == 2
    assert tick1["telemetry_bytes"] > 0


def test_mission_simulator_auto_switches_to_radar_evasion_on_radar_emitter() -> None:
    """
    Sensörlerden yüksek güvenli RADAR_EMITTER algılandığında NavigationSystem'in
    ShortestPathStrategy'den otomatik olarak RadarEvasionStrategy'ye geçtiğini doğrular.
    """
    sim = MissionSimulator()
    sim.switch_navigation_strategy_by_name("SHORTEST_PATH")
    assert isinstance(sim.navigation_system.strategy, ShortestPathStrategy)

    # 1. okuma: TGT-RAD-104 (SURFACE_VEHICLE), 2. okuma: TGT-RAD-109 (RADAR_EMITTER, güven=0.78)
    sim.run_simulation_tick(auto_evade_radar_threat=True)
    tick2 = sim.run_simulation_tick(auto_evade_radar_threat=True)

    assert tick2["strategy_switched"] is True
    assert tick2["active_strategy"] == "RADAR_EVASION"


def test_mission_simulator_preset_platforms_and_strategy_switching() -> None:
    """Hazır İHA reçetelerinin ve strateji geçişlerinin doğru çalıştığını doğrular."""
    sim = MissionSimulator()

    for preset in ("STD_RECON", "LONG_RECON", "STD_STRIKE", "HEAVY_STRIKE"):
        uav = sim.set_preset_platform(preset)
        assert uav.total_weight_kg <= uav.max_takeoff_weight_kg

    for strat_key in ("SHORTEST_PATH", "RADAR_EVASION", "LOITERING_SEARCH"):
        plan = sim.switch_navigation_strategy_by_name(strat_key)
        assert plan.strategy_name == strat_key


def test_plotly_chart_builders_return_valid_figures() -> None:
    """Beş kalıp için oluşturulan tüm Plotly grafik fonksiyonlarının geçerli Figure döndürdüğünü doğrular."""
    sim = MissionSimulator()
    sim.flight_controller.execute_command(FlightCommands.TAKE_OFF)
    sim.run_simulation_tick()

    fig_weight = create_weight_breakdown_chart(sim.active_platform)
    assert isinstance(fig_weight, go.Figure)
    assert len(fig_weight.data) == 5

    fig_polar, fig_cart = create_sensor_polar_and_cartesian_charts(sim.last_targets)
    assert isinstance(fig_polar, go.Figure)
    assert isinstance(fig_cart, go.Figure)
    assert len(fig_polar.data) == 2

    assert sim.last_telemetry_packet is not None
    fig_tel = create_telemetry_stage_size_chart(sim.last_telemetry_packet)
    assert isinstance(fig_tel, go.Figure)

    fig_dyn = create_flight_dynamics_chart(sim.flight_controller)
    assert isinstance(fig_dyn, go.Figure)
    assert len(fig_dyn.data) == 3

    assert sim.last_route_plan is not None
    fig_map = create_route_map_2d_chart([sim.last_route_plan], sim.restricted_zones)
    assert isinstance(fig_map, go.Figure)
    assert len(fig_map.data) >= 3
