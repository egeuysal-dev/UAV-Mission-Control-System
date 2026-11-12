"""
Beş GoF Tasarım Kalıbını (Builder, Adapter, Decorator, State, Strategy)
uçtan uca birleştiren merkezi simülasyon orkestratörü (`MissionSimulator`).

Kullanıcı arayüzünden (Streamlit) tamamen bağımsızdır; hem arayüz durumu
(session state) olarak hem de entegrasyon testlerinde doğrudan kullanılabilir.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.models.flight_state_models import FlightCommands
from src.models.navigation_models import (
    DEFAULT_RESTRICTED_ZONES,
    Point2D,
    RestrictedZone,
    RoutePlan,
)
from src.models.sensor_models import TargetData
from src.models.telemetry_models import TelemetryMessage, TelemetryPacketResult
from src.patterns.adapter import (
    LegacyStanagRadarSDK,
    MissionComputer,
    StanagRadarAdapter,
    ThermalCameraAdapter,
    VendorThermalDevice,
)
from src.patterns.builder import (
    MissionPrepDirector,
    ReconUAVBuilder,
    StrikeUAVBuilder,
    UAVPlatform,
)
from src.patterns.decorator import TelemetryChannel, build_telemetry_chain
from src.patterns.state import FlightController, PreflightIdleState
from src.patterns.strategy import (
    LoiteringSearchStrategy,
    NavigationSystem,
    RadarEvasionStrategy,
    ShortestPathStrategy,
)
from src.utils.logger import system_logger


@dataclass
class MissionSimulator:
    """
    İHA Görev ve Uçuş Kontrol Yazılımının beş tasarım kalıbını koordine eden
    merkezi simülasyon bağlamı.
    """

    active_platform: UAVPlatform = field(init=False)
    flight_controller: FlightController = field(init=False)
    mission_computer: MissionComputer = field(init=False)
    radar_adapter: StanagRadarAdapter = field(init=False)
    thermal_adapter: ThermalCameraAdapter = field(init=False)
    navigation_system: NavigationSystem = field(init=False)
    decorator_layers: List[str] = field(
        default_factory=lambda: [
            "CompressionDecorator",
            "AesEncryptionDecorator",
            "AntiJammingDecorator",
        ]
    )
    frequency_band: str = "SATCOM-Ku"
    simulate_interference: bool = True
    start_point: Point2D = field(default_factory=lambda: Point2D(10.0, 10.0, "Ana Üs (Home)"))
    destination_point: Point2D = field(
        default_factory=lambda: Point2D(85.0, 80.0, "Görev Sektörü")
    )
    restricted_zones: List[RestrictedZone] = field(
        default_factory=lambda: list(DEFAULT_RESTRICTED_ZONES)
    )
    last_targets: List[TargetData] = field(default_factory=list)
    last_route_plan: Optional[RoutePlan] = None
    last_telemetry_packet: Optional[TelemetryPacketResult] = None
    tick_count: int = 0
    mission_elapsed_seconds: int = 0
    current_fuel_kg: float = 0.0
    heading_deg: float = 47.0
    uav_position: Point2D = field(init=False)
    route_distance_traveled_km: float = 0.0
    route_progress_pct: float = 0.0
    active_waypoint_index: int = 0
    flight_trail: List[Point2D] = field(default_factory=list)
    sensor_fov_range_km: float = 18.0
    sensor_fov_half_angle_deg: float = 28.0

    def __post_init__(self) -> None:
        # 1. Builder: Varsayılan olarak standart keşif İHA'sı inşa et
        director = MissionPrepDirector(ReconUAVBuilder())
        self.active_platform = director.construct_standard_recon_uav()
        self.current_fuel_kg = self.active_platform.fuel_weight_kg

        # 2. Adapter: Radar ve Termal kamera adaptörlerini MissionComputer'a kaydet
        self.radar_adapter = StanagRadarAdapter(LegacyStanagRadarSDK())
        self.thermal_adapter = ThermalCameraAdapter(VendorThermalDevice())
        self.mission_computer = MissionComputer([self.radar_adapter, self.thermal_adapter])

        # 3. State: Uçuş kontrolcüsünü başlat
        self.flight_controller = FlightController()

        # 4. Strategy: Navigasyon sistemini RadarEvasionStrategy ile başlat
        self.navigation_system = NavigationSystem(RadarEvasionStrategy())
        self.last_route_plan = self.navigation_system.calculate_route(
            self.start_point,
            self.destination_point,
            self.restricted_zones,
        )
        self.uav_position = Point2D(
            self.start_point.x_km, self.start_point.y_km, "İHA Anlık Konumu"
        )
        self.flight_trail = [self.uav_position]
        self._update_heading_from_route()

        # 5. Decorator: İlk telemetri paketini oluştur
        self.transmit_current_telemetry(status_note="INITIAL_SYSTEM_BOOT")

    @staticmethod
    def _compute_bearing_deg(p1: Point2D, p2: Point2D) -> float:
        """İki 2B nokta arasındaki pusula açısını (0°=Kuzey, 90°=Doğu) hesaplar."""
        dx = p2.x_km - p1.x_km
        dy = p2.y_km - p1.y_km
        if abs(dx) <= 1e-6 and abs(dy) <= 1e-6:
            return 0.0
        return round(math.degrees(math.atan2(dx, dy)) % 360.0, 1)

    @classmethod
    def _interpolate_point_on_route(
        cls,
        plan: RoutePlan,
        distance_km: float,
    ) -> Tuple[Point2D, float, int]:
        """
        Verilen `RoutePlan` üzerinde başlangıçtan itibaren `distance_km` mesafedeki
        2B koordinatı, aktif segmentin pusula açısını (`heading_deg`) ve aktif
        waypoint indeksini döndürür.
        """
        wps = plan.waypoints
        if not wps:
            return Point2D(0.0, 0.0, "İHA"), 0.0, 0
        if len(wps) == 1 or distance_km <= 0.0:
            hdg = cls._compute_bearing_deg(wps[0], wps[1]) if len(wps) >= 2 else 0.0
            return (
                Point2D(round(wps[0].x_km, 2), round(wps[0].y_km, 2), "İHA Konumu"),
                hdg,
                0,
            )

        remaining = distance_km
        for idx in range(len(wps) - 1):
            p1 = wps[idx]
            p2 = wps[idx + 1]
            seg_len = p1.distance_to(p2)
            if seg_len <= 1e-6:
                continue
            if remaining <= seg_len or idx == len(wps) - 2:
                ratio = min(1.0, max(0.0, remaining / seg_len))
                ix = round(p1.x_km + ratio * (p2.x_km - p1.x_km), 2)
                iy = round(p1.y_km + ratio * (p2.y_km - p1.y_km), 2)
                hdg = cls._compute_bearing_deg(p1, p2)
                return Point2D(ix, iy, f"İHA (Seg {idx + 1})"), hdg, idx
            remaining -= seg_len

        last_wp = wps[-1]
        prev_wp = wps[-2]
        return (
            Point2D(round(last_wp.x_km, 2), round(last_wp.y_km, 2), "Hedefe Ulaşıldı"),
            cls._compute_bearing_deg(prev_wp, last_wp),
            len(wps) - 2,
        )

    def _update_heading_from_route(self) -> None:
        """Aktif rotadaki mevcut ilerleme mesafesine göre konum ve pusula açısını günceller."""
        if self.last_route_plan and len(self.last_route_plan.waypoints) >= 2:
            total_dist = max(0.01, self.last_route_plan.total_distance_km)
            clamped_dist = min(self.route_distance_traveled_km, total_dist)
            pos, hdg, seg_idx = self._interpolate_point_on_route(
                self.last_route_plan, clamped_dist
            )
            self.uav_position = pos
            self.heading_deg = hdg
            self.active_waypoint_index = seg_idx
            self.route_progress_pct = round(
                min(100.0, (clamped_dist / total_dist) * 100.0), 1
            )

    def advance_uav_along_route(self, step_km: Optional[float] = None) -> Point2D:
        """
        İHA'yı aktif rota üzerinde (veya `EMERGENCY_RETURN` fazındaysa Ana Üsse doğru)
        bir adım ilerletir ve uçuş izini (`flight_trail`) günceller.
        """
        if self.last_route_plan is None or not self.last_route_plan.waypoints:
            return self.uav_position

        if step_km is None:
            speed_kts = self.flight_controller.speed_knots
            if speed_kts > 0:
                step_km = round(max(9.0, speed_kts * 0.11), 2)
            else:
                step_km = 12.0

        # Eğer İHA Acil Eve Dönüş (EMERGENCY_RETURN) fazındaysa doğrudan Ana Üsse (start_point) yönel
        if self.flight_controller.current_phase_name == "EMERGENCY_RETURN":
            dist_to_home = self.uav_position.distance_to(self.start_point)
            if dist_to_home <= 0.25:
                self.uav_position = Point2D(
                    self.start_point.x_km, self.start_point.y_km, "Üsse Dönüldü (RTB)"
                )
            else:
                self.heading_deg = self._compute_bearing_deg(
                    self.uav_position, self.start_point
                )
                ratio = min(1.0, step_km / dist_to_home)
                nx = round(
                    self.uav_position.x_km
                    + ratio * (self.start_point.x_km - self.uav_position.x_km),
                    2,
                )
                ny = round(
                    self.uav_position.y_km
                    + ratio * (self.start_point.y_km - self.uav_position.y_km),
                    2,
                )
                self.uav_position = Point2D(nx, ny, "İHA (Acil RTB)")
            self.flight_trail.append(self.uav_position)
            return self.uav_position

        total_dist = max(0.01, self.last_route_plan.total_distance_km)
        self.route_distance_traveled_km = round(
            min(total_dist, self.route_distance_traveled_km + step_km), 2
        )
        self._update_heading_from_route()
        self.flight_trail.append(self.uav_position)
        return self.uav_position

    def reset_flight_position(self) -> None:
        """İHA konumunu, uçuş izini, yakıtı ve uçuş fazını başlangıç üssüne sıfırlar."""
        self.route_distance_traveled_km = 0.0
        self.route_progress_pct = 0.0
        self.active_waypoint_index = 0
        self.mission_elapsed_seconds = 0
        self.current_fuel_kg = self.active_platform.fuel_weight_kg
        self.flight_controller.clear_emergency_reason()
        self.flight_controller.transition_to(PreflightIdleState())
        self.uav_position = Point2D(
            self.start_point.x_km, self.start_point.y_km, "İHA Anlık Konumu"
        )
        self.flight_trail = [self.uav_position]
        self._update_heading_from_route()

    @staticmethod
    def _cardinal_direction(heading_deg: float) -> str:
        """Derece cinsinden pusula açısını 8 ana/ara yöne (K, KD, D, GD...) çevirir."""
        directions = ["K", "KD", "D", "GD", "G", "GB", "B", "KB"]
        idx = int(((heading_deg + 22.5) % 360.0) // 45.0)
        return directions[idx]

    def build_telemetry_channel(self) -> TelemetryChannel:
        """Aktif dekoratör katman listesine göre TelemetryChannel nesnesi inşa eder."""
        return build_telemetry_chain(
            layer_names=self.decorator_layers,
            frequency_band=self.frequency_band,
            simulate_interference=self.simulate_interference,
        )

    def transmit_current_telemetry(
        self,
        status_note: str = "PERIODIC_MISSION_TELEMETRY",
    ) -> TelemetryPacketResult:
        """
        Aktif İHA platformu (Builder), uçuş fazı (State) ve rota (Strategy)
        verilerinden bir `TelemetryMessage` oluşturup Decorator zincirinden geçirir.
        """
        msg = TelemetryMessage(
            uav_id=self.active_platform.model_name,
            flight_phase=self.flight_controller.current_phase_name,
            altitude_m=self.flight_controller.altitude_m,
            speed_knots=self.flight_controller.speed_knots,
            heading_deg=self.heading_deg,
            fuel_remaining_kg=round(self.current_fuel_kg, 1),
            status_note=status_note,
        )
        channel = self.build_telemetry_channel()
        self.last_telemetry_packet = channel.transmit(msg.to_payload_string())
        return self.last_telemetry_packet

    def run_simulation_tick(
        self,
        auto_evade_radar_threat: bool = True,
        auto_lifecycle: bool = False,
        step_distance_km: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Beş tasarım kalıbının tamamını içeren bir simülasyon döngüsü (tick) çalıştırır:
        1. Opsiyonel otopilot yaşam döngüsü (`auto_lifecycle`) aktifse uçuş fazını
           (IDLE -> TAKE_OFF -> CRUISE -> COMBAT) rota ilerleyişine göre otomatik yönetir.
        2. MissionComputer (Adapter) üzerinden sensör hedeflerini okur.
        3. Yüksek güvenli bir RADAR_EMITTER algılanırsa ve `auto_evade_radar_threat` aktifse,
           NavigationSystem (Strategy) stratejisini otomatik olarak `RadarEvasionStrategy`'ye geçirir.
        4. İHA'yı aktif rota üzerinde (veya acil durumda Ana Üsse doğru) ilerletir, uçuş izini
           (`flight_trail`), pusula açısını (`heading_deg`) ve yakıt tüketimini günceller.
        5. Yakıt %15 veya altına düşerse otomatik olarak `EmergencyReturnState` (Failsafe) tetikler.
        6. Güncel uçuş fazı (State) ve platform (Builder) telemetrisini Decorator zinciriyle iletir.
        """
        self.tick_count += 1

        if auto_lifecycle and self.flight_controller.current_phase_name != "EMERGENCY_RETURN":
            cur_phase = self.flight_controller.current_phase_name
            if cur_phase == "PREFLIGHT_IDLE":
                self.flight_controller.execute_command(FlightCommands.TAKE_OFF)
            elif cur_phase == "TAKE_OFF" and self.route_progress_pct >= 12.0:
                self.flight_controller.execute_command(FlightCommands.CLIMB_TO_CRUISE)
            elif cur_phase == "CRUISE" and self.route_progress_pct >= 68.0:
                self.flight_controller.execute_command(FlightCommands.ENTER_MISSION_ZONE)
            elif cur_phase == "COMBAT":
                self.flight_controller.execute_command(FlightCommands.EXECUTE_SIM_TASK)

        phase = self.flight_controller.current_phase_name
        if phase == "PREFLIGHT_IDLE":
            self.mission_elapsed_seconds += 30
            fuel_burn = 1.5
        else:
            self.mission_elapsed_seconds += 180
            throttle_factor = max(0.35, self.flight_controller.throttle_pct / 100.0)
            fuel_burn = round(14.0 * throttle_factor, 2)

        self.current_fuel_kg = max(0.0, round(self.current_fuel_kg - fuel_burn, 1))
        initial_fuel = max(1.0, self.active_platform.fuel_weight_kg)
        fuel_pct = (self.current_fuel_kg / initial_fuel) * 100.0

        emergency_triggered = False
        if (
            fuel_pct <= 15.0
            and self.flight_controller.current_phase_name != "EMERGENCY_RETURN"
        ):
            self.flight_controller.trigger_emergency(
                f"Kritik Yakıt Seviyesi Uyarısı (%{fuel_pct:.1f} / {self.current_fuel_kg:.1f} kg kaldı — Otomatik Failsafe RTB)"
            )
            emergency_triggered = True

        self.last_targets = self.mission_computer.collect_all_targets()

        strategy_switched = False
        for target in self.last_targets:
            if (
                auto_evade_radar_threat
                and target.classification == "RADAR_EMITTER"
                and target.confidence_score >= 0.75
                and not isinstance(self.navigation_system.strategy, RadarEvasionStrategy)
            ):
                self.navigation_system.set_strategy(RadarEvasionStrategy())
                strategy_switched = True
                system_logger.warning(
                    "Simulator",
                    f"Sensörlerden yüksek güvenli radar emisyonu ({target.target_id}) algılandı; "
                    f"rota stratejisi otomatik olarak RadarEvasionStrategy'ye geçirildi.",
                )

        self.last_route_plan = self.navigation_system.calculate_route(
            self.start_point,
            self.destination_point,
            self.restricted_zones,
        )
        self.advance_uav_along_route(step_km=step_distance_km)

        packet = self.transmit_current_telemetry(
            status_note=f"SIM_TICK_{self.tick_count}_POS_{self.uav_position.x_km:.1f}_{self.uav_position.y_km:.1f}"
        )

        system_logger.info(
            "Simulator",
            f"Simülasyon döngüsü #{self.tick_count} tamamlandı "
            f"(Konum: [{self.uav_position.x_km:.1f}, {self.uav_position.y_km:.1f}] km, "
            f"İlerleme: %{self.route_progress_pct:.1f}, "
            f"Faz: {self.flight_controller.current_phase_name}, "
            f"Rota: {self.last_route_plan.strategy_name}, "
            f"Paket: {packet.final_size_bytes}B).",
        )
        return {
            "tick": self.tick_count,
            "platform": self.active_platform.model_name,
            "flight_phase": self.flight_controller.current_phase_name,
            "targets_collected": len(self.last_targets),
            "active_strategy": self.last_route_plan.strategy_name,
            "strategy_switched": strategy_switched,
            "emergency_triggered": emergency_triggered,
            "telemetry_bytes": packet.final_size_bytes,
            "fuel_remaining_kg": self.current_fuel_kg,
            "uav_x_km": self.uav_position.x_km,
            "uav_y_km": self.uav_position.y_km,
            "route_progress_pct": self.route_progress_pct,
        }

    def set_preset_platform(self, preset_key: str) -> UAVPlatform:
        """Director üzerinden hazır bir İHA platform reçetesi yükler."""
        if preset_key == "STD_RECON":
            director = MissionPrepDirector(ReconUAVBuilder())
            self.active_platform = director.construct_standard_recon_uav()
        elif preset_key == "LONG_RECON":
            director = MissionPrepDirector(ReconUAVBuilder())
            self.active_platform = director.construct_long_range_recon_uav()
        elif preset_key == "STD_STRIKE":
            director = MissionPrepDirector(StrikeUAVBuilder())
            self.active_platform = director.construct_standard_strike_uav()
        elif preset_key == "HEAVY_STRIKE":
            director = MissionPrepDirector(StrikeUAVBuilder())
            self.active_platform = director.construct_heavy_strike_uav()
        else:
            raise ValueError(f"Bilinmeyen platform reçetesi: {preset_key}")

        self.current_fuel_kg = self.active_platform.fuel_weight_kg
        return self.active_platform

    def switch_navigation_strategy_by_name(self, strategy_key: str) -> RoutePlan:
        """Strateji adına göre NavigationSystem algoritmasını değiştirir ve yeni rotayı döndürür."""
        if strategy_key == "SHORTEST_PATH":
            self.navigation_system.set_strategy(ShortestPathStrategy())
        elif strategy_key == "RADAR_EVASION":
            self.navigation_system.set_strategy(RadarEvasionStrategy())
        elif strategy_key == "LOITERING_SEARCH":
            self.navigation_system.set_strategy(LoiteringSearchStrategy())
        else:
            raise ValueError(f"Bilinmeyen navigasyon stratejisi: {strategy_key}")

        self.last_route_plan = self.navigation_system.calculate_route(
            self.start_point,
            self.destination_point,
            self.restricted_zones,
        )
        self._update_heading_from_route()
        return self.last_route_plan

    def get_hud_telemetry(self) -> Dict[str, Any]:
        """
        Üst Telemetri Durum Şeridi (Top HUD Bar) ve 4'lü Aviyonik PFD Kadranları
        için anlık uçuş ve sistem verilerini döndürür.
        """
        fc = self.flight_controller
        uav = self.active_platform
        initial_fuel = max(1.0, uav.fuel_weight_kg)
        fuel_pct = round(min(100.0, max(0.0, (self.current_fuel_kg / initial_fuel) * 100.0)), 1)

        hrs = self.mission_elapsed_seconds // 3600
        mins = (self.mission_elapsed_seconds % 3600) // 60
        secs = self.mission_elapsed_seconds % 60
        clock_str = f"T+{hrs:02d}:{mins:02d}:{secs:02d}"

        has_antijam = "AntiJammingDecorator" in self.decorator_layers
        has_aes = "AesEncryptionDecorator" in self.decorator_layers
        has_comp = "CompressionDecorator" in self.decorator_layers

        snr_db = 26.4 if has_antijam else (14.2 if self.simulate_interference else 22.0)
        altitude_ft = round(fc.altitude_m * 3.28084)

        sec_badges: List[str] = []
        if has_comp:
            sec_badges.append("ZLIB")
        if has_aes:
            sec_badges.append("AES-256-GCM")
        if has_antijam:
            sec_badges.append("CRC32/FEC")
        if not sec_badges:
            sec_badges.append("AÇIK RADYO (UNPROTECTED)")

        return {
            "mission_clock_str": clock_str,
            "uav_model": uav.model_name,
            "mission_type": uav.mission_type,
            "flight_phase": fc.current_phase_name,
            "phase_title": fc.state.display_title,
            "airspeed_knots": fc.speed_knots,
            "altitude_m": fc.altitude_m,
            "altitude_ft": altitude_ft,
            "throttle_pct": fc.throttle_pct,
            "fuel_remaining_kg": self.current_fuel_kg,
            "fuel_initial_kg": uav.fuel_weight_kg,
            "fuel_pct": fuel_pct,
            "heading_deg": self.heading_deg,
            "heading_cardinal": self._cardinal_direction(self.heading_deg),
            "datalink_band": self.frequency_band,
            "datalink_snr_db": snr_db,
            "security_badges": sec_badges,
            "gps_status": "3D FIX (15 SAT)",
            "bus_voltage_v": 28.4 if fc.throttle_pct > 0 else 24.2,
            "is_emergency": fc.current_phase_name == "EMERGENCY_RETURN",
            "emergency_reason": fc.emergency_reason,
            "uav_x_km": self.uav_position.x_km,
            "uav_y_km": self.uav_position.y_km,
            "route_progress_pct": self.route_progress_pct,
        }
