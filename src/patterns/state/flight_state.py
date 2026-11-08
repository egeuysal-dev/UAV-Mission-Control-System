"""
GoF State Tasarım Kalıbı (Davranışsal) — Uçuş Fazları ve Durum Geçiş Yönetimi.

Katılımcı Sınıflar:
- Context: FlightController
- State (ABC): FlightPhaseState
- ConcreteState 1: PreflightIdleState
- ConcreteState 2: TakeOffState
- ConcreteState 3: CruiseState
- ConcreteState 4: CombatState (Temsili Görev Simülasyon Fazı)
- ConcreteState 5: EmergencyReturnState (Failsafe / Acil Eve Dönüş Fazı)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from src.models.flight_state_models import (
    FlightCommands,
    InvalidFlightCommandError,
    StateTransitionResult,
)
from src.utils.logger import system_logger


class FlightPhaseState(ABC):
    """
    GoF State Kalıbı — State (Soyut Durum Arayüzü) Sınıfı.

    Her uçuş fazının kendi irtifa/motor profilini, izin verilen komutlarını
    ve durum geçiş kurallarını kapsüllemesini sağlar.
    """

    @property
    @abstractmethod
    def phase_name(self) -> str:
        """Durumun benzersiz teknik adını döndürür."""

    @property
    @abstractmethod
    def display_title(self) -> str:
        """Arayüzde gösterilecek okunabilir uçuş fazı başlığını döndürür."""

    @property
    @abstractmethod
    def allowed_commands(self) -> Tuple[str, ...]:
        """Bu uçuş fazında kabul edilen geçerli komutların listesini döndürür."""

    @abstractmethod
    def apply_phase_profile(self, controller: FlightController) -> None:
        """
        Bu faza geçildiğinde FlightController üzerindeki irtifa, hız ve motor
        tepki parametrelerini fazın karakteristik profiline göre günceller.
        """

    @abstractmethod
    def handle_command(
        self,
        controller: FlightController,
        command: str,
    ) -> Tuple[bool, str]:
        """
        Komutu mevcut uçuş fazı kurallarına göre işler.

        Returns:
            (accepted, message): Komutun kabul edilip edilmediği ve açıklama metni.
        """

    def on_emergency(
        self,
        controller: FlightController,
        reason: str,
    ) -> Tuple[bool, str]:
        """
        Acil durum (sinyal kaybı, kritik yakıt, sensör arızası) tetiklendiğinde
        İHA'yı simüle edilmiş eve dönüş durumuna (`EmergencyReturnState`) geçirir.
        """
        controller.set_emergency_reason(reason)
        controller.transition_to(EmergencyReturnState(reason=reason))
        return (
            True,
            f"ACİL DURUM PROTOKOLÜ (FAILSAFE): '{reason}' nedeniyle "
            f"EmergencyReturnState (Acil Eve Dönüş) fazına geçildi.",
        )

    def _reject_command(self, command: str, reason: str) -> Tuple[bool, str]:
        """Geçersiz bir komutu standart açıklama formatıyla reddeder."""
        return (
            False,
            f"[{self.phase_name}] '{command}' komutu reddedildi: {reason} "
            f"(İzin verilen komutlar: {list(self.allowed_commands)})",
        )


class PreflightIdleState(FlightPhaseState):
    """
    GoF State Kalıbı — ConcreteState 1 (Yerde Bekleme ve Uçuş Öncesi Hazırlık).

    İHA pist başında yerde beklemededir. İrtifa 0 m, hız 0 knot, motor rölantidedir.
    Yalnızca motor kontrolü ve kalkış (`TAKE_OFF`) komutlarını kabul eder;
    seyir veya görev komutlarını reddeder.
    """

    @property
    def phase_name(self) -> str:
        return "PREFLIGHT_IDLE"

    @property
    def display_title(self) -> str:
        return "Yerde Bekleme (Preflight Idle)"

    @property
    def allowed_commands(self) -> Tuple[str, ...]:
        return (
            FlightCommands.START_ENGINE_CHECKS,
            FlightCommands.TAKE_OFF,
        )

    def apply_phase_profile(self, controller: FlightController) -> None:
        controller.update_flight_dynamics(
            altitude_m=0.0,
            speed_knots=0.0,
            throttle_pct=12.0,
            engine_response="Rölanti / Yer Bekleme Modu (Düşük Devir)",
        )

    def handle_command(
        self,
        controller: FlightController,
        command: str,
    ) -> Tuple[bool, str]:
        if command == FlightCommands.START_ENGINE_CHECKS:
            controller.mark_preflight_checked(True)
            controller.update_flight_dynamics(
                altitude_m=0.0,
                speed_knots=0.0,
                throttle_pct=28.0,
                engine_response="Uçuş Öncesi Motor & Aviyonik Testi Tamamlandı",
            )
            return (
                True,
                "Motor, aviyonik ve kontrol yüzeyi testleri başarıyla tamamlandı; kalkışa hazır.",
            )

        if command == FlightCommands.TAKE_OFF:
            controller.transition_to(TakeOffState())
            return (
                True,
                "Kalkış komutu onaylandı. Tam güç verildi, TakeOffState fazına geçildi.",
            )

        return self._reject_command(
            command,
            "İHA henüz yerde bekleme fazında; önce kalkış (TAKE_OFF) yapılmalıdır.",
        )

    def on_emergency(
        self,
        controller: FlightController,
        reason: str,
    ) -> Tuple[bool, str]:
        """Yerdeyken acil durum tetiklenirse motorlar güvenli şekilde durdurulur, uçuş başlatılmaz."""
        controller.set_emergency_reason(reason)
        controller.update_flight_dynamics(
            altitude_m=0.0,
            speed_knots=0.0,
            throttle_pct=0.0,
            engine_response="Yerde Güvenli Kesme (Emergency Cutoff)",
        )
        return (
            True,
            f"İHA zaten yerde ({self.phase_name}); '{reason}' nedeniyle motorlar güvenli kesildi.",
        )


class TakeOffState(FlightPhaseState):
    """
    GoF State Kalıbı — ConcreteState 2 (Kalkış ve İlk Tırmanış Fazı).

    İHA maksimum motor itkisiyle (%95) pistten ayrılmış ve ilk tırmanış irtifasındadır.
    Yalnızca seyir irtifasına geçiş (`CLIMB_TO_CRUISE`) veya acil eve dönüş
    (`TRIGGER_EMERGENCY_RTB`) komutlarını kabul eder; görev icra komutlarını reddeder.
    """

    @property
    def phase_name(self) -> str:
        return "TAKE_OFF"

    @property
    def display_title(self) -> str:
        return "Kalkış ve Tırmanış (Take-Off)"

    @property
    def allowed_commands(self) -> Tuple[str, ...]:
        return (
            FlightCommands.CLIMB_TO_CRUISE,
            FlightCommands.TRIGGER_EMERGENCY_RTB,
        )

    def apply_phase_profile(self, controller: FlightController) -> None:
        controller.update_flight_dynamics(
            altitude_m=600.0,
            speed_knots=95.0,
            throttle_pct=95.0,
            engine_response="Maksimum Kalkış İtkisi (Yüksek Tırmanış Oranı)",
        )

    def handle_command(
        self,
        controller: FlightController,
        command: str,
    ) -> Tuple[bool, str]:
        if command == FlightCommands.CLIMB_TO_CRUISE:
            controller.transition_to(CruiseState())
            return (
                True,
                "Hedef irtifaya ulaşıldı; ekonomik seyir (CruiseState) fazına geçildi.",
            )

        if command == FlightCommands.TRIGGER_EMERGENCY_RTB:
            return self.on_emergency(controller, "Kalkış esnasında manuel acil dönüş komutu")

        return self._reject_command(
            command,
            "Kalkış tırmanışı tamamlanmadan bu komut çalıştırılamaz.",
        )


class CruiseState(FlightPhaseState):
    """
    GoF State Kalıbı — ConcreteState 3 (Normal Seyir Fazı).

    İHA operasyonel seyir irtifasında (6000 m) ve ekonomik motor devrindedir (%65).
    Rota koruma (`MAINTAIN_VECTOR`), görev bölgesine giriş (`ENTER_MISSION_ZONE`),
    normal iniş (`LAND_AND_PARKING`) veya acil dönüş (`TRIGGER_EMERGENCY_RTB`)
    komutlarını kabul eder.
    """

    @property
    def phase_name(self) -> str:
        return "CRUISE"

    @property
    def display_title(self) -> str:
        return "Operasyonel Seyir (Cruise)"

    @property
    def allowed_commands(self) -> Tuple[str, ...]:
        return (
            FlightCommands.MAINTAIN_VECTOR,
            FlightCommands.ENTER_MISSION_ZONE,
            FlightCommands.LAND_AND_PARKING,
            FlightCommands.TRIGGER_EMERGENCY_RTB,
        )

    def apply_phase_profile(self, controller: FlightController) -> None:
        controller.update_flight_dynamics(
            altitude_m=6000.0,
            speed_knots=140.0,
            throttle_pct=65.0,
            engine_response="Ekonomik Seyir Rejimi (Otopilot İrtifa Tutma Aktif)",
        )

    def handle_command(
        self,
        controller: FlightController,
        command: str,
    ) -> Tuple[bool, str]:
        if command == FlightCommands.MAINTAIN_VECTOR:
            controller.update_flight_dynamics(
                altitude_m=6000.0,
                speed_knots=142.0,
                throttle_pct=64.0,
                engine_response="Seyir Vektörü ve İrtifa Sabitlendi",
            )
            return (True, "Seyir irtifası (6000 m) ve rota vektörü stabil şekilde korunuyor.")

        if command == FlightCommands.ENTER_MISSION_ZONE:
            controller.transition_to(CombatState())
            return (
                True,
                "Görev bölgesine giriş yapıldı; temsili görev fazına (CombatState) geçildi.",
            )

        if command == FlightCommands.LAND_AND_PARKING:
            controller.transition_to(PreflightIdleState())
            return (
                True,
                "Alçalma ve iniş prosedürü tamamlandı; PreflightIdleState fazına dönüldü.",
            )

        if command == FlightCommands.TRIGGER_EMERGENCY_RTB:
            return self.on_emergency(controller, "Seyir esnasında acil eve dönüş komutu")

        return self._reject_command(
            command,
            "Seyir fazında doğrudan görev simülasyonu veya kalkış komutu çalıştırılamaz.",
        )


class CombatState(FlightPhaseState):
    """
    GoF State Kalıbı — ConcreteState 4 (Temsili Görev / Operasyon Fazı).

    Not: Bu sınıf yalnızca eğitim ve durum deseni simülasyonu amaçlı temsili bir
    görev fazıdır. Gerçek silah ateşleme veya fiziksel hedefleme işlemi içermez.

    Bu fazda İHA görev irtifasına (4200 m) iner ve yüksek manevra motor tepkisine (%85)
    geçer. Temsili görev adımı (`EXECUTE_SIM_TASK`), görev bölgesinden çıkış
    (`EXIT_MISSION_ZONE`) veya acil dönüş (`TRIGGER_EMERGENCY_RTB`) komutlarını kabul eder.
    """

    @property
    def phase_name(self) -> str:
        return "COMBAT"

    @property
    def display_title(self) -> str:
        return "Temsili Görev Fazı (Combat Sim)"

    @property
    def allowed_commands(self) -> Tuple[str, ...]:
        return (
            FlightCommands.EXECUTE_SIM_TASK,
            FlightCommands.EXIT_MISSION_ZONE,
            FlightCommands.TRIGGER_EMERGENCY_RTB,
        )

    def apply_phase_profile(self, controller: FlightController) -> None:
        controller.update_flight_dynamics(
            altitude_m=4200.0,
            speed_knots=165.0,
            throttle_pct=85.0,
            engine_response="Yüksek Manevra ve Görev Tepki Rejimi (Sensör/Pod Aktif)",
        )

    def handle_command(
        self,
        controller: FlightController,
        command: str,
    ) -> Tuple[bool, str]:
        if command == FlightCommands.EXECUTE_SIM_TASK:
            task_count = controller.increment_sim_tasks()
            return (
                True,
                f"Temsili görev simülasyon adımı #{task_count} (sentetik veri kaydı) başarıyla yürütüldü.",
            )

        if command == FlightCommands.EXIT_MISSION_ZONE:
            controller.transition_to(CruiseState())
            return (
                True,
                "Görev bölgesi terk edildi; standart seyir fazına (CruiseState) dönüldü.",
            )

        if command == FlightCommands.TRIGGER_EMERGENCY_RTB:
            return self.on_emergency(controller, "Görev fazında acil eve dönüş komutu")

        return self._reject_command(
            command,
            "Aktif görev fazındayken doğrudan iniş veya kalkış yapılamaz; önce EXIT_MISSION_ZONE ile seyir fazına çıkılmalıdır.",
        )


class EmergencyReturnState(FlightPhaseState):
    """
    GoF State Kalıbı — ConcreteState 5 (Failsafe / Acil Eve Dönüş Fazı).

    Sinyal kesilmesi, kritik yakıt seviyesi veya sistem arızası durumunda devreye girer.
    Güvenli dönüş irtifası (3500 m) ve korumalı motor rejimi (%75) uygulanır.
    Görevle ilgili tüm komutlar kilitlenir; yalnızca güvenli iniş (`LAND_AND_PARKING`)
    komutuna izin verilir.
    """

    def __init__(self, reason: str = "Failsafe Tetiklendi") -> None:
        self._reason = reason

    @property
    def reason(self) -> str:
        """Acil eve dönüş durumuna geçiş nedenini döndürür."""
        return self._reason

    @property
    def phase_name(self) -> str:
        return "EMERGENCY_RETURN"

    @property
    def display_title(self) -> str:
        return "Acil Eve Dönüş (Emergency RTB / Failsafe)"

    @property
    def allowed_commands(self) -> Tuple[str, ...]:
        return (FlightCommands.LAND_AND_PARKING,)

    def apply_phase_profile(self, controller: FlightController) -> None:
        controller.update_flight_dynamics(
            altitude_m=3500.0,
            speed_knots=125.0,
            throttle_pct=75.0,
            engine_response=f"Failsafe Güvenli Koridor İtkisi (Neden: {self._reason})",
        )

    def handle_command(
        self,
        controller: FlightController,
        command: str,
    ) -> Tuple[bool, str]:
        if command == FlightCommands.LAND_AND_PARKING:
            controller.clear_emergency_reason()
            controller.transition_to(PreflightIdleState())
            return (
                True,
                "Acil eve dönüş inişi başarıyla tamamlandı; İHA güvenli şekilde PreflightIdleState fazına alındı.",
            )

        return self._reject_command(
            command,
            f"Acil durum modu aktif ('{self._reason}'); güvenlik gereği yalnızca LAND_AND_PARKING komutuna izin verilir.",
        )


class FlightController:
    """
    GoF State Kalıbı — Context (Bağlam / Uçuş Kontrolcüsü) Sınıfı.

    İHA'nın aktif uçuş fazı nesnesini (`FlightPhaseState`) barındırır ve gelen
    tüm uçuş komutlarını `if-elif-else` blokları kullanmadan doğrudan aktif
    durum nesnesine delege eder.
    """

    def __init__(self, initial_state: Optional[FlightPhaseState] = None) -> None:
        self._altitude_m: float = 0.0
        self._speed_knots: float = 0.0
        self._throttle_pct: float = 0.0
        self._engine_response: str = ""
        self._preflight_checked: bool = False
        self._completed_sim_tasks: int = 0
        self._emergency_reason: Optional[str] = None
        self._history: List[StateTransitionResult] = []

        self._state: FlightPhaseState = initial_state or PreflightIdleState()
        self._state.apply_phase_profile(self)
        system_logger.info(
            "State",
            f"FlightController başlatıldı. Başlangıç fazı: {self._state.phase_name}.",
        )

    @property
    def state(self) -> FlightPhaseState:
        """Aktif FlightPhaseState nesnesini döndürür."""
        return self._state

    @property
    def current_phase_name(self) -> str:
        """Aktif uçuş fazının teknik adını döndürür."""
        return self._state.phase_name

    @property
    def altitude_m(self) -> float:
        """Anlık simüle edilmiş irtifayı (metre) döndürür."""
        return self._altitude_m

    @property
    def speed_knots(self) -> float:
        """Anlık simüle edilmiş hava hızını (knot) döndürür."""
        return self._speed_knots

    @property
    def throttle_pct(self) -> float:
        """Anlık motor gaz/itki yüzdesini döndürür."""
        return self._throttle_pct

    @property
    def engine_response(self) -> str:
        """Aktif faza özgü motor tepki modunu döndürür."""
        return self._engine_response

    @property
    def preflight_checked(self) -> bool:
        """Uçuş öncesi yer kontrollerinin yapılıp yapılmadığını döndürür."""
        return self._preflight_checked

    @property
    def completed_sim_tasks(self) -> int:
        """Görev fazında tamamlanan temsili simülasyon adımı sayısını döndürür."""
        return self._completed_sim_tasks

    @property
    def emergency_reason(self) -> Optional[str]:
        """Aktif bir acil durum varsa nedenini döndürür."""
        return self._emergency_reason

    def update_flight_dynamics(
        self,
        altitude_m: float,
        speed_knots: float,
        throttle_pct: float,
        engine_response: str,
    ) -> None:
        """Durum sınıflarının uçuş dinamiklerini güncellemesi için kullanılan metot."""
        self._altitude_m = float(altitude_m)
        self._speed_knots = float(speed_knots)
        self._throttle_pct = float(throttle_pct)
        self._engine_response = engine_response

    def mark_preflight_checked(self, checked: bool = True) -> None:
        """Uçuş öncesi kontrol bayrağını günceller."""
        self._preflight_checked = checked

    def increment_sim_tasks(self) -> int:
        """Tamamlanan temsili görev sayacını 1 artırır ve yeni değeri döndürür."""
        self._completed_sim_tasks += 1
        return self._completed_sim_tasks

    def set_emergency_reason(self, reason: str) -> None:
        """Acil durum nedenini kaydeder."""
        self._emergency_reason = reason

    def clear_emergency_reason(self) -> None:
        """Acil durum nedenini temizler."""
        self._emergency_reason = None

    def get_allowed_commands(self) -> List[str]:
        """Aktif uçuş fazında izin verilen komutların listesini döndürür."""
        return list(self._state.allowed_commands)

    def transition_to(self, new_state: FlightPhaseState) -> None:
        """
        Uçuş kontrolcüsünü yeni bir uçuş fazına (`FlightPhaseState`) geçirir,
        fazın uçuş dinamiklerini uygular ve geçişi olay günlüğüne kaydeder.
        """
        if not isinstance(new_state, FlightPhaseState):
            raise TypeError("Yeni durum FlightPhaseState arayüzünü uygulamalıdır.")

        old_phase = self._state.phase_name
        self._state = new_state
        self._state.apply_phase_profile(self)
        system_logger.info(
            "State",
            f"Durum Geçişi: {old_phase} -> {self._state.phase_name} "
            f"(İrtifa: {self._altitude_m} m, Hız: {self._speed_knots} kts, Motor: %{self._throttle_pct}).",
        )

    def execute_command(
        self,
        command: str,
        raise_on_invalid: bool = False,
    ) -> StateTransitionResult:
        """
        Verilen komutu aktif uçuş fazı nesnesine (`self._state.handle_command`) iletir.
        Geçersiz komutları reddeder, olay günlüğüne yazar ve sonucu döndürür.
        """
        previous_phase = self._state.phase_name
        accepted, message = self._state.handle_command(self, command)

        result = StateTransitionResult(
            accepted=accepted,
            command=command,
            previous_phase=previous_phase,
            current_phase=self._state.phase_name,
            altitude_m=self._altitude_m,
            speed_knots=self._speed_knots,
            throttle_pct=self._throttle_pct,
            engine_response=self._engine_response,
            message=message,
            allowed_commands=self._state.allowed_commands,
        )
        self._history.append(result)

        if accepted:
            system_logger.info("State", f"[Komut Kabul: {command}] {message}")
        else:
            system_logger.warning("State", f"[Komut Reddedildi: {command}] {message}")
            if raise_on_invalid:
                raise InvalidFlightCommandError(message)

        return result

    def trigger_emergency(
        self,
        reason: str = "Sinyal Kaybı / Kritik Yakıt Seviyesi",
    ) -> StateTransitionResult:
        """
        Herhangi bir anda acil durum senaryosunu tetikleyerek aktif fazın
        `on_emergency` davranışını çalıştırır.
        """
        previous_phase = self._state.phase_name
        accepted, message = self._state.on_emergency(self, reason)

        result = StateTransitionResult(
            accepted=accepted,
            command=FlightCommands.TRIGGER_EMERGENCY_RTB,
            previous_phase=previous_phase,
            current_phase=self._state.phase_name,
            altitude_m=self._altitude_m,
            speed_knots=self._speed_knots,
            throttle_pct=self._throttle_pct,
            engine_response=self._engine_response,
            message=message,
            allowed_commands=self._state.allowed_commands,
        )
        self._history.append(result)
        system_logger.error("State", message)
        return result

    def get_transition_history(self) -> List[StateTransitionResult]:
        """Gerçekleşen tüm komut ve durum geçiş geçmişinin kopyasını döndürür."""
        return list(self._history)

    def get_status_summary(self) -> Dict[str, Any]:
        """Kullanıcı arayüzü (Dashboard / Flight Controller) için anlık durum özetini döndürür."""
        return {
            "current_phase": self._state.phase_name,
            "display_title": self._state.display_title,
            "state_class": self._state.__class__.__name__,
            "altitude_m": self._altitude_m,
            "speed_knots": self._speed_knots,
            "throttle_pct": self._throttle_pct,
            "engine_response": self._engine_response,
            "allowed_commands": list(self._state.allowed_commands),
            "preflight_checked": self._preflight_checked,
            "completed_sim_tasks": self._completed_sim_tasks,
            "emergency_reason": self._emergency_reason,
            "history_count": len(self._history),
        }
