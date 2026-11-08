"""
Uçuş fazları (State Kalıbı) için veri modelleri, komut sabitleri ve özel hatalar.

İHA'nın farklı uçuş fazlarındaki (Idle, TakeOff, Cruise, Combat Sim, Emergency Return)
durum geçiş sonuçlarını ve geçmiş kayıtlarını temsil eder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple


class InvalidFlightCommandError(ValueError):
    """
    Aktif uçuş fazında izin verilmeyen bir komut çalıştırılmak istendiğinde
    (`raise_on_invalid=True` modunda) fırlatılan özel istisna sınıfı.
    """


class FlightCommands:
    """Uçuş kontrolcüsü tarafından desteklenen standart komut sabitleri."""

    START_ENGINE_CHECKS = "START_ENGINE_CHECKS"
    TAKE_OFF = "TAKE_OFF"
    CLIMB_TO_CRUISE = "CLIMB_TO_CRUISE"
    MAINTAIN_VECTOR = "MAINTAIN_VECTOR"
    ENTER_MISSION_ZONE = "ENTER_MISSION_ZONE"
    EXECUTE_SIM_TASK = "EXECUTE_SIM_TASK"
    EXIT_MISSION_ZONE = "EXIT_MISSION_ZONE"
    LAND_AND_PARKING = "LAND_AND_PARKING"
    TRIGGER_EMERGENCY_RTB = "TRIGGER_EMERGENCY_RTB"

    ALL_COMMANDS: Tuple[str, ...] = (
        START_ENGINE_CHECKS,
        TAKE_OFF,
        CLIMB_TO_CRUISE,
        MAINTAIN_VECTOR,
        ENTER_MISSION_ZONE,
        EXECUTE_SIM_TASK,
        EXIT_MISSION_ZONE,
        LAND_AND_PARKING,
        TRIGGER_EMERGENCY_RTB,
    )


@dataclass(frozen=True)
class StateTransitionResult:
    """
    FlightController üzerinde bir komut veya acil durum tetiklendiğinde
    dönen yapılandırılmış işlem sonucu.
    """

    accepted: bool
    command: str
    previous_phase: str
    current_phase: str
    altitude_m: float
    speed_knots: float
    throttle_pct: float
    engine_response: str
    message: str
    allowed_commands: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        """Kullanıcı arayüzü ve raporlama için sözlük temsili döndürür."""
        return {
            "accepted": self.accepted,
            "command": self.command,
            "previous_phase": self.previous_phase,
            "current_phase": self.current_phase,
            "altitude_m": self.altitude_m,
            "speed_knots": self.speed_knots,
            "throttle_pct": self.throttle_pct,
            "engine_response": self.engine_response,
            "message": self.message,
            "allowed_commands": list(self.allowed_commands),
        }
