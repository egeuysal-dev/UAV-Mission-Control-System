"""
Beş GoF Tasarım Kalıbını (Builder, Adapter, Decorator, State, Strategy)
uçtan uca birleştiren merkezi simülasyon orkestratörü (`MissionSimulator`).

Kullanıcı arayüzünden (Streamlit) tamamen bağımsızdır; hem arayüz durumu
(session state) olarak hem de entegrasyon testlerinde doğrudan kullanılabilir.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
from src.patterns.state import FlightController
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
        self._update_heading_from_route()

        # 5. Decorator: İlk telemetri paketini oluştur
        self.transmit_current_telemetry(status_note="INITIAL_SYSTEM_BOOT")

    def _update_heading_from_route(self) -> None:
        """Aktif rotanın ilk segmentine göre pusula baş açısını (0-360°) günceller."""
        if self.last_route_plan and len(self.last_route_plan.waypoints) >= 2:
            p1 = self.last_route_plan.waypoints[0]
            p2 = self.last_route_plan.waypoints[1]
            dx = p2.x_km - p1.x_km
            dy = p2.y_km - p1.y_km
            if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                angle = math.degrees(math.atan2(dx, dy)) % 360.0
                self.heading_deg = round(angle, 1)

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

    def run_simulation_tick(self, auto_evade_radar_threat: bool = True) -> Dict[str, Any]:
        """
        Beş tasarım kalıbının tamamını içeren bir simülasyon döngüsü (tick) çalıştırır:
        1. MissionComputer (Adapter) üzerinden sensör hedeflerini okur.
        2. Yüksek güvenli bir RADAR_EMITTER algılanırsa ve `auto_evade_radar_threat` aktifse,
           NavigationSystem (Strategy) stratejisini otomatik olarak `RadarEvasionStrategy`'ye geçirir.
        3. Aktif rotayı yeniden hesaplar, görev süresini ve yakıt tüketimini günceller.
        4. Güncel uçuş fazı (State) ve platform (Builder) telemetrisini Decorator zinciriyle iletir.
        """
        self.tick_count += 1
        phase = self.flight_controller.current_phase_name
        if phase == "PREFLIGHT_IDLE":
            self.mission_elapsed_seconds += 30
            fuel_burn = 0.5
        else:
            self.mission_elapsed_seconds += 180
            throttle_factor = max(0.25, self.flight_controller.throttle_pct / 100.0)
            fuel_burn = round(4.5 * throttle_factor, 2)

        self.current_fuel_kg = max(0.0, round(self.current_fuel_kg - fuel_burn, 1))
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
        self._update_heading_from_route()
        packet = self.transmit_current_telemetry(
            status_note=f"SIM_TICK_{self.tick_count}_TARGETS_{len(self.last_targets)}"
        )

        system_logger.info(
            "Simulator",
            f"Simülasyon döngüsü #{self.tick_count} tamamlandı "
            f"(Faz: {self.flight_controller.current_phase_name}, "
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
            "telemetry_bytes": packet.final_size_bytes,
            "fuel_remaining_kg": self.current_fuel_kg,
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
        }
