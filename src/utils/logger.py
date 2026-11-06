"""
Merkezi sistem ve görev olay günlüğü (Event Logger) modülü.

Standart Python `logging` modülünü sarmalar ve aynı zamanda kullanıcı arayüzünde
(Dashboard / Flight Controller) gerçek zamanlı gösterim için bellek içi yapılandırılmış
olay kayıtları (SystemEvent) tutar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass(frozen=True)
class SystemEvent:
    """Sistem içinde gerçekleşen tek bir olayı temsil eden veri modeli."""

    timestamp: str
    level: str
    module: str
    message: str


class MissionEventLogger:
    """
    İş mantığı katmanı ile kullanıcı arayüzünden bağımsız çalışan olay kaydedici.
    Hem standart Python logger'ına yazar hem de bellek içi geçmişi yönetir.
    """

    def __init__(self, name: str = "UAVMissionControl", max_events: int = 200) -> None:
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

        self._max_events = max_events
        self._events: List[SystemEvent] = []

    def log(self, level: str, module: str, message: str) -> SystemEvent:
        """Yeni bir sistem olayı kaydeder ve oluşturulan kaydı döndürür."""
        normalized_level = level.upper()
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        event = SystemEvent(
            timestamp=timestamp,
            level=normalized_level,
            module=module,
            message=message,
        )
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)

        log_level = getattr(logging, normalized_level, logging.INFO)
        self._logger.log(log_level, f"[{module}] {message}")
        return event

    def info(self, module: str, message: str) -> SystemEvent:
        """Bilgi seviyesinde olay kaydı ekler."""
        return self.log("INFO", module, message)

    def warning(self, module: str, message: str) -> SystemEvent:
        """Uyarı seviyesinde olay kaydı ekler."""
        return self.log("WARNING", module, message)

    def error(self, module: str, message: str) -> SystemEvent:
        """Hata seviyesinde olay kaydı ekler."""
        return self.log("ERROR", module, message)

    def get_events(self) -> List[SystemEvent]:
        """Kayıtlı tüm olayların kopyasını döndürür."""
        return list(self._events)

    def clear(self) -> None:
        """Bellek içi olay kayıtlarını temizler."""
        self._events.clear()


# Varsayılan paylaşımlı sistem günlükçüsü
system_logger = MissionEventLogger()
