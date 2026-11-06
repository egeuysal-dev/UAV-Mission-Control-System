"""
Aşama 1: Mimari iskelet ve temel altyapı duman (smoke) testleri.
"""

from __future__ import annotations

import importlib

from app import get_architecture_overview
from src import __version__
from src.utils.logger import MissionEventLogger


def test_package_version() -> None:
    """Çekirdek paket sürüm bilgisinin tanımlı olduğunu doğrular."""
    assert __version__ == "0.1.0"


def test_pattern_packages_importable() -> None:
    """Beş GoF kalıbına ve katmanlara ait alt paketlerin sorunsuz import edildiğini doğrular."""
    modules = [
        "src.models",
        "src.patterns.builder",
        "src.patterns.adapter",
        "src.patterns.decorator",
        "src.patterns.state",
        "src.patterns.strategy",
        "src.simulation",
        "src.services",
        "src.utils",
        "ui.pages",
        "ui.components",
    ]
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None


def test_mission_event_logger() -> None:
    """Merkezi olay günlükçüsünün (MissionEventLogger) kayıt ve sınır davranışlarını doğrular."""
    logger = MissionEventLogger(name="TestLogger", max_events=3)
    logger.clear()

    ev1 = logger.info("Builder", "İHA yapılandırması başlatıldı.")
    ev2 = logger.warning("State", "Geçersiz komut denemesi.")
    ev3 = logger.error("Telemetry", "Simüle edilmiş paket kaybı.")

    events = logger.get_events()
    assert len(events) == 3
    assert events[0] == ev1
    assert events[1].level == "WARNING"
    assert events[2].module == "Telemetry"

    # Kapasite aşımında FIFO davranışı
    logger.info("Strategy", "Rota güncellendi.")
    events_after = logger.get_events()
    assert len(events_after) == 3
    assert events_after[0] == ev2


def test_architecture_overview_structure() -> None:
    """Uygulama iskeletindeki mimari özet tablosunun 5 GoF kalıbını içerdiğini doğrular."""
    overview = get_architecture_overview()
    assert len(overview) == 5
    pattern_names = [item["pattern"] for item in overview]
    assert "1. Builder" in pattern_names
    assert "2. Adapter" in pattern_names
    assert "3. Decorator" in pattern_names
    assert "4. State" in pattern_names
    assert "5. Strategy" in pattern_names
