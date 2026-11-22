"""
İHA Görev ve Uçuş Kontrol Yazılımı — Ana Streamlit Uygulaması.

Yedi etkileşimli simülasyon ekranını (Dashboard, UAV Configuration, Sensor Integration,
Telemetry System, Flight Controller, Navigation, Design Patterns) yöneten giriş noktası.
"""

from __future__ import annotations

from src import __version__
from src.simulation.mission_simulator import MissionSimulator
from src.utils.logger import system_logger
from ui.components.theme import inject_custom_css, render_top_hud_bar
from ui.pages import (
    get_architecture_overview,
    render_dashboard_page,
    render_design_patterns_page,
    render_flight_controller_page,
    render_navigation_page,
    render_sensor_integration_page,
    render_telemetry_system_page,
    render_uav_config_page,
)


def render_app() -> None:
    """Ana Streamlit kontrol paneli arayüzünü ve kenar çubuğu (sidebar) navigasyonunu çizer."""
    import streamlit as st

    st.set_page_config(
        page_title="İHA Görev ve Uçuş Kontrol Yazılımı",
        page_icon="🛸",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()

    if (
        "simulator" not in st.session_state
        or not hasattr(st.session_state["simulator"], "get_hud_telemetry")
        or not hasattr(st.session_state["simulator"], "uav_position")
        or not hasattr(st.session_state["simulator"], "run_tactical_scenario")
    ):
        st.session_state["simulator"] = MissionSimulator()

    sim: MissionSimulator = st.session_state["simulator"]

    # Sol Kenar Çubuğu (Sidebar)
    with st.sidebar:
        st.markdown("## 🛸 İHA Görev Kontrol")
        st.caption(f"Sürüm v{__version__} | GoF Simülasyon Platformu")
        st.divider()

        pages = {
            "1. 📊 Dashboard (Genel Durum)": "DASHBOARD",
            "2. 🛠️ UAV Configuration (Builder)": "BUILDER",
            "3. 📡 Sensor Integration (Adapter)": "ADAPTER",
            "4. 🔐 Telemetry System (Decorator)": "DECORATOR",
            "5. 🎮 Flight Controller (State)": "STATE",
            "6. 🧭 Navigation (Strategy)": "STRATEGY",
            "7. 📐 Design Patterns (UML)": "PATTERNS",
        }
        selected_label = st.radio("Simülasyon Ekranları:", options=list(pages.keys()))
        active_page = pages[selected_label]

        st.divider()
        st.markdown("### 📌 Anlık Telemetri Özeti")
        st.markdown(f"- **Platform:** `{sim.active_platform.model_name}`")
        st.markdown(f"- **Uçuş Fazı:** `{sim.flight_controller.current_phase_name}`")
        st.markdown(f"- **İrtifa / Hız:** `{sim.flight_controller.altitude_m:.0f} m` / `{sim.flight_controller.speed_knots:.0f} kts`")
        st.markdown(f"- **İHA Konumu:** `({sim.uav_position.x_km:.1f}, {sim.uav_position.y_km:.1f}) km` (`%{sim.route_progress_pct:.0f}`)")
        if sim.last_route_plan:
            st.markdown(f"- **Aktif Rota:** `{sim.last_route_plan.strategy_name}`")
        st.markdown(f"- **Telemetri Katmanı:** `{len(sim.decorator_layers)}` aktif")

        if st.button("🔄 Tüm Simülasyonu Sıfırla", use_container_width=True):
            st.session_state["simulator"] = MissionSimulator()
            st.rerun()

    # Üst Aviyonik Telemetri Durum Şeridi (Top HUD Bar)
    render_top_hud_bar(sim.get_hud_telemetry())

    # Seçilen Ekranı Çiz
    if active_page == "DASHBOARD":
        render_dashboard_page(sim)
    elif active_page == "BUILDER":
        render_uav_config_page(sim)
    elif active_page == "ADAPTER":
        render_sensor_integration_page(sim)
    elif active_page == "DECORATOR":
        render_telemetry_system_page(sim)
    elif active_page == "STATE":
        render_flight_controller_page(sim)
    elif active_page == "STRATEGY":
        render_navigation_page(sim)
    elif active_page == "PATTERNS":
        render_design_patterns_page(sim)


if __name__ == "__main__":
    system_logger.info("Bootstrap", f"İHA Görev ve Uçuş Kontrol Yazılımı v{__version__} başlatıldı.")
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            render_app()
        else:
            for item in get_architecture_overview():
                print(f"- {item['pattern']} ({item['category']}): {item['status']}")
    except ImportError:
        for item in get_architecture_overview():
            print(f"- {item['pattern']} ({item['category']}): {item['status']}")
