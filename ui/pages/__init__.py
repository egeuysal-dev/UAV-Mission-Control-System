"""Simülasyon paneli ekranları (sayfalar)."""

from ui.pages.dashboard_page import render_dashboard_page
from ui.pages.design_patterns_page import (
    get_architecture_overview,
    render_design_patterns_page,
)
from ui.pages.flight_controller_page import render_flight_controller_page
from ui.pages.navigation_page import render_navigation_page
from ui.pages.sensor_integration_page import render_sensor_integration_page
from ui.pages.telemetry_system_page import render_telemetry_system_page
from ui.pages.uav_config_page import render_uav_config_page

__all__ = [
    "get_architecture_overview",
    "render_dashboard_page",
    "render_design_patterns_page",
    "render_flight_controller_page",
    "render_navigation_page",
    "render_sensor_integration_page",
    "render_telemetry_system_page",
    "render_uav_config_page",
]
