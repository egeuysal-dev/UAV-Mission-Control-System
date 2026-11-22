"""
Aşama 7: Simülasyon Orkestratörü (MissionSimulator) ve Görselleştirme (Plotly) Testleri.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src.models.flight_state_models import FlightCommands
from src.patterns.strategy import ShortestPathStrategy
from src.simulation.mission_simulator import MissionSimulator
from ui.components.charts import (
    create_altitude_profile_chart,
    create_avionics_gauges_chart,
    create_flight_dynamics_chart,
    create_flir_thermal_view_chart,
    create_rf_spectrum_chart,
    create_route_map_2d_chart,
    create_route_map_3d_chart,
    create_sensor_polar_and_cartesian_charts,
    create_telemetry_stage_size_chart,
    create_uav_blueprint_chart,
    create_uav_capability_radar_chart,
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

    hud = sim.get_hud_telemetry()
    assert hud["flight_phase"] == "TAKE_OFF"
    assert hud["airspeed_knots"] > 0
    assert hud["altitude_m"] > 0
    assert 0.0 <= hud["fuel_pct"] <= 100.0
    assert len(hud["security_badges"]) == 3

    fig_gauges = create_avionics_gauges_chart(hud)
    assert isinstance(fig_gauges, go.Figure)
    assert len(fig_gauges.data) == 4

    fig_live_map = create_route_map_2d_chart(
        route_plans=[sim.last_route_plan],
        restricted_zones=sim.restricted_zones,
        active_strategy_name=sim.last_route_plan.strategy_name,
        uav_position=sim.uav_position,
        uav_heading_deg=sim.heading_deg,
        flight_trail=sim.flight_trail,
        sensor_fov_range_km=sim.sensor_fov_range_km,
        sensor_fov_half_angle_deg=sim.sensor_fov_half_angle_deg,
        detected_targets=sim.last_targets,
    )
    assert isinstance(fig_live_map, go.Figure)
    assert len(fig_live_map.data) >= 6


def test_uav_movement_trail_and_automatic_low_fuel_failsafe() -> None:
    """
    Öneri B: İHA'nın rota üzerinde adım adım ilerlediğini, uçuş izi (`flight_trail`)
    bıraktığını, kritik yakıt seviyesinde (<=%15) otomatik olarak `EMERGENCY_RETURN`
    fazına geçtiğini ve Ana Üsse doğru geri döndüğünü doğrular.
    """
    sim = MissionSimulator()
    assert sim.uav_position.x_km == sim.start_point.x_km
    assert sim.uav_position.y_km == sim.start_point.y_km
    assert len(sim.flight_trail) == 1

    # Otopilot ile 3 adım ilerle
    for _ in range(3):
        sim.run_simulation_tick(auto_lifecycle=True, step_distance_km=20.0)

    assert sim.route_distance_traveled_km == 60.0
    assert sim.route_progress_pct > 0.0
    assert len(sim.flight_trail) == 4
    assert sim.uav_position.distance_to(sim.start_point) > 15.0
    assert sim.flight_controller.current_phase_name in ("TAKE_OFF", "CRUISE")

    # Kritik yakıt (<=%15) simülasyonu ve otomatik Failsafe RTB tetiklemesi
    dist_before_rtb = sim.uav_position.distance_to(sim.start_point)
    sim.current_fuel_kg = round(sim.active_platform.fuel_weight_kg * 0.12, 1)
    rtb_tick = sim.run_simulation_tick(auto_lifecycle=True, step_distance_km=15.0)

    assert rtb_tick["emergency_triggered"] is True
    assert sim.flight_controller.current_phase_name == "EMERGENCY_RETURN"
    dist_after_rtb = sim.uav_position.distance_to(sim.start_point)
    assert dist_after_rtb < dist_before_rtb

    # Üsse sıfırlama kontrolü
    sim.reset_flight_position()
    assert sim.route_distance_traveled_km == 0.0
    assert len(sim.flight_trail) == 1
    assert sim.flight_controller.current_phase_name == "PREFLIGHT_IDLE"


def test_3d_route_map_and_altitude_profile_charts() -> None:
    """
    Öneri C: 3B uçuş yörüngesi / kısıtlı bölge radar kubbeleri (`create_route_map_3d_chart`)
    ve dikey irtifa/arazi kesiti (`create_altitude_profile_chart`) grafiklerinin
    her üç strateji için de geçerli Plotly Figure nesneleri ürettiğini doğrular.
    """
    sim = MissionSimulator()
    sim.run_simulation_tick(auto_lifecycle=True, step_distance_km=25.0)
    all_plans = sim.navigation_system.compare_all_strategies(
        sim.start_point, sim.destination_point, sim.restricted_zones
    )

    fig_3d = create_route_map_3d_chart(
        route_plans=all_plans,
        restricted_zones=sim.restricted_zones,
        active_strategy_name="RADAR_EVASION",
        uav_position=sim.uav_position,
        current_altitude_m=sim.flight_controller.altitude_m,
        flight_trail=sim.flight_trail,
    )
    assert isinstance(fig_3d, go.Figure)
    assert len(fig_3d.data) >= 8

    for plan in all_plans:
        fig_vsd = create_altitude_profile_chart(
            route_plan=plan,
            distance_traveled_km=sim.route_distance_traveled_km,
            current_altitude_m=sim.flight_controller.altitude_m,
            current_phase_name=sim.flight_controller.current_phase_name,
        )
        assert isinstance(fig_vsd, go.Figure)
        assert len(fig_vsd.data) == 5


def test_uav_performance_metrics_blueprint_and_capability_radar_charts() -> None:
    """
    Öneri D: UAVPlatform.get_performance_metrics(), 2B teknik İHA gövde/istasyon şeması
    (`create_uav_blueprint_chart`) ve 5 eksenli yetenek radar grafiğinin
    (`create_uav_capability_radar_chart`) hem RECON hem STRIKE için doğru çalıştığını doğrular.
    """
    sim = MissionSimulator()
    for preset in ("STD_RECON", "HEAVY_STRIKE"):
        platform = sim.set_preset_platform(preset)
        perf = platform.get_performance_metrics()
        assert perf["endurance_hours"] > 0
        assert perf["combat_radius_km"] > 0
        assert perf["cruise_speed_kts"] > 0
        assert len(perf["radar_scores"]) == 5

        fig_bp = create_uav_blueprint_chart(platform)
        assert isinstance(fig_bp, go.Figure)
        assert len(fig_bp.data) >= 6

        fig_rad = create_uav_capability_radar_chart(platform)
        assert isinstance(fig_rad, go.Figure)
        assert len(fig_rad.data) == 2


def test_ppi_radar_sweep_and_flir_thermal_view_charts() -> None:
    """
    Öneri E: Taktik PPI radar tarama hüzmesi (`sweep_angle_deg`) ve sentetik EO/IR
    termal kamera vizörünün (`create_flir_thermal_view_chart`) hem radar hem termal
    hedefler için geçerli Plotly Figure nesneleri ürettiğini doğrular.
    """
    sim = MissionSimulator()
    sim.run_simulation_tick()
    assert len(sim.last_targets) >= 2

    polar_sweep, cart_sweep = create_sensor_polar_and_cartesian_charts(
        sim.last_targets, sweep_angle_deg=120.0
    )
    assert isinstance(polar_sweep, go.Figure)
    assert isinstance(cart_sweep, go.Figure)
    assert len(polar_sweep.data) == len(sim.last_targets) + 1
    assert len(cart_sweep.data) >= len(sim.last_targets) + 3

    for target in sim.last_targets:
        for pol in ("WHOT", "BHOT"):
            fig_flir = create_flir_thermal_view_chart(target, polarity=pol)
            assert isinstance(fig_flir, go.Figure)
            assert len(fig_flir.data) >= 5


def test_rf_spectrum_analyzer_chart() -> None:
    """
    Öneri F: Elektronik Harp (EW) RF Spektrum Analizörü grafiğinin
    (`create_rf_spectrum_chart`) karıştırma aktif/pasif ve AntiJammingDecorator
    açık/kapalı durumlarında geçerli Plotly Figure ürettiğini doğrular.
    """
    fig_protected = create_rf_spectrum_chart(
        frequency_band="SATCOM-Ku",
        active_layers=["CompressionDecorator", "AesEncryptionDecorator", "AntiJammingDecorator"],
        jamming_active=True,
        jamming_intensity_db=22.0,
    )
    assert isinstance(fig_protected, go.Figure)
    assert len(fig_protected.data) == 2

    fig_clean = create_rf_spectrum_chart(
        frequency_band="UHF-433MHz",
        active_layers=[],
        jamming_active=False,
    )
    assert isinstance(fig_clean, go.Figure)
    assert len(fig_clean.data) == 1
