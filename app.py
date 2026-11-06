"""
İHA Görev ve Uçuş Kontrol Yazılımı — Ana Uygulama Giriş Noktası (Aşama 1 İskeleti).

Bu dosya, Aşama 1 kapsamında çalıştırılabilir minimal uygulama iskeletini sunar.
İlerleyen aşamalarda 5 GoF tasarım kalıbı ve ilgili simülasyon sayfaları
modüler olarak bu giriş noktasına bağlanacaktır.
"""

from __future__ import annotations

from typing import Dict, List

from src import __version__
from src.utils.logger import system_logger


def get_architecture_overview() -> List[Dict[str, str]]:
    """Projedeki 5 GoF tasarım kalıbının mimari özet tablosunu döndürür."""
    return [
        {
            "pattern": "1. Builder",
            "category": "Yaratımsal (Creational)",
            "module": "src.patterns.builder",
            "classes": "UAVConfigurationBuilder, StrikeUAVBuilder, ReconUAVBuilder, MissionPrepDirector, UAVPlatform",
            "status": "Aşama 2'de geliştirilecek",
        },
        {
            "pattern": "2. Adapter",
            "category": "Yapısal (Structural)",
            "module": "src.patterns.adapter",
            "classes": "TargetSensor, StanagRadarAdapter, ThermalCameraAdapter, LegacyStanagRadarSDK, VendorThermalDevice, MissionComputer",
            "status": "Aşama 3'te geliştirilecek",
        },
        {
            "pattern": "3. Decorator",
            "category": "Yapısal (Structural)",
            "module": "src.patterns.decorator",
            "classes": "TelemetryChannel, BaseRadioChannel, TelemetryChannelDecorator, AesEncryptionDecorator, CompressionDecorator, AntiJammingDecorator",
            "status": "Aşama 4'te geliştirilecek",
        },
        {
            "pattern": "4. State",
            "category": "Davranışsal (Behavioral)",
            "module": "src.patterns.state",
            "classes": "FlightController, FlightPhaseState, PreflightIdleState, TakeOffState, CruiseState, CombatState, EmergencyReturnState",
            "status": "Aşama 5'te geliştirilecek",
        },
        {
            "pattern": "5. Strategy",
            "category": "Davranışsal (Behavioral)",
            "module": "src.patterns.strategy",
            "classes": "NavigationSystem, RoutePlanningStrategy, ShortestPathStrategy, RadarEvasionStrategy, LoiteringSearchStrategy",
            "status": "Aşama 6'da geliştirilecek",
        },
    ]


def render_streamlit_skeleton() -> None:
    """Streamlit tabanlı minimal simülasyon kontrol paneli iskeletini çizer."""
    import streamlit as st

    st.set_page_config(
        page_title="İHA Görev ve Uçuş Kontrol Yazılımı",
        page_icon="🛸",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🛸 İHA Görev ve Uçuş Kontrol Yazılımı")
    st.caption(
        f"Sürüm v{__version__} | Eğitim ve Sentetik Simülasyon Platformu | Aşama 1: Mimari İskelet"
    )

    st.info(
        "Sistem mimarisi ve klasör iskeleti başarıyla hazırlandı. "
        "Beş temel GoF tasarım kalıbı Aşama 2–6 arasında adım adım entegre edilecektir."
    )

    st.subheader("Planlanan GoF Tasarım Kalıpları ve Katmanlar")
    st.table(get_architecture_overview())

    if st.button("Test Sistem Olayı Kaydet"):
        system_logger.info("CoreSkeleton", "Aşama 1 sistem doğrulama sinyali üretildi.")

    st.subheader("Sistem Olay Günlüğü (Event Log)")
    events = system_logger.get_events()
    if not events:
        st.write("Henüz kayıtlı sistem olayı bulunmuyor.")
    else:
        for ev in reversed(events):
            st.code(f"[{ev.timestamp}] [{ev.level}] [{ev.module}] {ev.message}")


if __name__ == "__main__":
    system_logger.info("Bootstrap", f"İHA Görev ve Uçuş Kontrol Yazılımı v{__version__} başlatıldı.")
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            render_streamlit_skeleton()
        else:
            for item in get_architecture_overview():
                print(f"- {item['pattern']} ({item['category']}): {item['status']}")
    except ImportError:
        for item in get_architecture_overview():
            print(f"- {item['pattern']} ({item['category']}): {item['status']}")
