"""
Aşama 5: GoF State Kalıbı (Uçuş Fazları ve Durum Geçişleri) Birim Testleri.
"""

from __future__ import annotations

import pytest

from src.models.flight_state_models import FlightCommands, InvalidFlightCommandError
from src.patterns.state import (
    CombatState,
    CruiseState,
    EmergencyReturnState,
    FlightController,
    PreflightIdleState,
    TakeOffState,
)
from src.utils.logger import system_logger


def test_initial_state_is_preflight_idle() -> None:
    """FlightController'ın varsayılan olarak PreflightIdleState ile başladığını doğrular."""
    controller = FlightController()

    assert isinstance(controller.state, PreflightIdleState)
    assert controller.current_phase_name == "PREFLIGHT_IDLE"
    assert controller.altitude_m == 0.0
    assert controller.speed_knots == 0.0
    assert controller.get_allowed_commands() == [
        FlightCommands.START_ENGINE_CHECKS,
        FlightCommands.TAKE_OFF,
    ]


def test_full_nominal_flight_lifecycle_transitions() -> None:
    """
    Yerde Bekleme -> Kalkış -> Seyir -> Temsili Görev Fazı -> Seyir -> İniş
    tam görev döngüsünü ve her fazdaki irtifa/motor değişimini doğrular.
    """
    controller = FlightController()

    # 1. Yer motor kontrolleri
    res_check = controller.execute_command(FlightCommands.START_ENGINE_CHECKS)
    assert res_check.accepted is True
    assert controller.preflight_checked is True
    assert controller.current_phase_name == "PREFLIGHT_IDLE"

    # 2. Kalkış (PREFLIGHT_IDLE -> TAKE_OFF)
    res_takeoff = controller.execute_command(FlightCommands.TAKE_OFF)
    assert res_takeoff.accepted is True
    assert isinstance(controller.state, TakeOffState)
    assert controller.altitude_m == 600.0
    assert controller.throttle_pct == 95.0

    # 3. Seyir irtifasına tırmanış (TAKE_OFF -> CRUISE)
    res_cruise = controller.execute_command(FlightCommands.CLIMB_TO_CRUISE)
    assert res_cruise.accepted is True
    assert isinstance(controller.state, CruiseState)
    assert controller.altitude_m == 6000.0
    assert controller.throttle_pct == 65.0

    # 4. Görev bölgesine giriş (CRUISE -> COMBAT)
    res_combat = controller.execute_command(FlightCommands.ENTER_MISSION_ZONE)
    assert res_combat.accepted is True
    assert isinstance(controller.state, CombatState)
    assert controller.altitude_m == 4200.0
    assert controller.throttle_pct == 85.0

    # 5. Temsili görev simülasyon adımı yürütme (COMBAT içinde kalır)
    res_task = controller.execute_command(FlightCommands.EXECUTE_SIM_TASK)
    assert res_task.accepted is True
    assert controller.completed_sim_tasks == 1
    assert controller.current_phase_name == "COMBAT"

    # 6. Görev bölgesinden çıkış (COMBAT -> CRUISE)
    res_exit = controller.execute_command(FlightCommands.EXIT_MISSION_ZONE)
    assert res_exit.accepted is True
    assert isinstance(controller.state, CruiseState)
    assert controller.altitude_m == 6000.0

    # 7. İniş ve park (CRUISE -> PREFLIGHT_IDLE)
    res_land = controller.execute_command(FlightCommands.LAND_AND_PARKING)
    assert res_land.accepted is True
    assert isinstance(controller.state, PreflightIdleState)
    assert controller.altitude_m == 0.0
    assert controller.speed_knots == 0.0


def test_invalid_commands_are_rejected_in_each_phase() -> None:
    """
    Her uçuş fazında izin verilmeyen komutların reddedildiğini, durumu değiştirmediğini
    ve `raise_on_invalid=True` verildiğinde InvalidFlightCommandError fırlattığını doğrular.
    """
    controller = FlightController()

    # PreflightIdleState içindeyken görev komutu reddedilmeli
    res = controller.execute_command(FlightCommands.EXECUTE_SIM_TASK)
    assert res.accepted is False
    assert controller.current_phase_name == "PREFLIGHT_IDLE"

    with pytest.raises(InvalidFlightCommandError):
        controller.execute_command(FlightCommands.CLIMB_TO_CRUISE, raise_on_invalid=True)

    # Kalkışa geç
    controller.execute_command(FlightCommands.TAKE_OFF)
    # TakeOffState içindeyken doğrudan görev fazına girilemez
    res_takeoff_invalid = controller.execute_command(FlightCommands.ENTER_MISSION_ZONE)
    assert res_takeoff_invalid.accepted is False
    assert controller.current_phase_name == "TAKE_OFF"

    # Seyire geç ve görev fazına gir
    controller.execute_command(FlightCommands.CLIMB_TO_CRUISE)
    controller.execute_command(FlightCommands.ENTER_MISSION_ZONE)
    # CombatState içindeyken doğrudan iniş yapılamaz (önce EXIT_MISSION_ZONE gerekir)
    res_combat_land = controller.execute_command(FlightCommands.LAND_AND_PARKING)
    assert res_combat_land.accepted is False
    assert controller.current_phase_name == "COMBAT"


def test_emergency_return_scenario_locks_mission_commands_until_landing() -> None:
    """
    Acil durum tetiklendiğinde EmergencyReturnState fazına geçildiğini,
    görev komutlarının kilitlendiğini ve yalnızca iniş komutuyla normale dönüldüğünü doğrular.
    """
    controller = FlightController(initial_state=CombatState())
    assert controller.current_phase_name == "COMBAT"

    # Sinyal kesintisi acil durumu tetikle
    emg_result = controller.trigger_emergency("Veri Bağı (Data Link) Sinyal Kesintisi")
    assert emg_result.accepted is True
    assert isinstance(controller.state, EmergencyReturnState)
    assert controller.current_phase_name == "EMERGENCY_RETURN"
    assert controller.altitude_m == 3500.0
    assert controller.emergency_reason == "Veri Bağı (Data Link) Sinyal Kesintisi"
    assert controller.get_allowed_commands() == [FlightCommands.LAND_AND_PARKING]

    # Acil dönüş sırasında görev komutu reddedilmeli
    rejected = controller.execute_command(FlightCommands.EXECUTE_SIM_TASK)
    assert rejected.accepted is False
    assert controller.current_phase_name == "EMERGENCY_RETURN"

    # Güvenli iniş komutu kabul edilmeli ve PreflightIdleState'e dönmeli
    landed = controller.execute_command(FlightCommands.LAND_AND_PARKING)
    assert landed.accepted is True
    assert isinstance(controller.state, PreflightIdleState)
    assert controller.emergency_reason is None
    assert controller.altitude_m == 0.0


def test_emergency_on_ground_cuts_throttle_without_flying() -> None:
    """Yerde bekleme fazındayken acil durum tetiklenirse uçuşa geçmeden motorların kesildiğini doğrular."""
    controller = FlightController()
    result = controller.trigger_emergency("Yer Güç Ünitesi Arızası")

    assert result.accepted is True
    assert controller.current_phase_name == "PREFLIGHT_IDLE"
    assert controller.throttle_pct == 0.0


def test_transition_history_and_logger_integration() -> None:
    """Durum geçişlerinin hem FlightController geçmişine hem de merkezi olay günlüğüne yazıldığını doğrular."""
    system_logger.clear()
    controller = FlightController()
    controller.execute_command(FlightCommands.TAKE_OFF)
    controller.execute_command(FlightCommands.EXECUTE_SIM_TASK)  # Reddedilen komut

    history = controller.get_transition_history()
    assert len(history) == 2
    assert history[0].accepted is True
    assert history[0].current_phase == "TAKE_OFF"
    assert history[1].accepted is False

    summary = controller.get_status_summary()
    assert summary["current_phase"] == "TAKE_OFF"
    assert summary["history_count"] == 2

    events = system_logger.get_events()
    assert any(ev.module == "State" and "TAKE_OFF" in ev.message for ev in events)
