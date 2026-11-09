"""
Ekran 7: Design Patterns — Kullanılan 5 GoF Tasarım Kalıbının UML Diyagramları ve Sınıf İlişkileri.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import streamlit as st

from ui.components.theme import render_pattern_header


def get_architecture_overview() -> List[Dict[str, str]]:
    """Projedeki 5 GoF tasarım kalıbının mimari özet tablosunu döndürür."""
    return [
        {
            "pattern": "1. Builder",
            "category": "Yaratımsal (Creational)",
            "module": "src.patterns.builder",
            "classes": "UAVConfigurationBuilder, StrikeUAVBuilder, ReconUAVBuilder, MissionPrepDirector, UAVPlatform",
            "status": "Tamamlandı (Aşama 2)",
        },
        {
            "pattern": "2. Adapter",
            "category": "Yapısal (Structural)",
            "module": "src.patterns.adapter",
            "classes": "TargetSensor, StanagRadarAdapter, ThermalCameraAdapter, LegacyStanagRadarSDK, VendorThermalDevice, MissionComputer",
            "status": "Tamamlandı (Aşama 3)",
        },
        {
            "pattern": "3. Decorator",
            "category": "Yapısal (Structural)",
            "module": "src.patterns.decorator",
            "classes": "TelemetryChannel, BaseRadioChannel, TelemetryChannelDecorator, AesEncryptionDecorator, CompressionDecorator, AntiJammingDecorator",
            "status": "Tamamlandı (Aşama 4)",
        },
        {
            "pattern": "4. State",
            "category": "Davranışsal (Behavioral)",
            "module": "src.patterns.state",
            "classes": "FlightController, FlightPhaseState, PreflightIdleState, TakeOffState, CruiseState, CombatState, EmergencyReturnState",
            "status": "Tamamlandı (Aşama 5)",
        },
        {
            "pattern": "5. Strategy",
            "category": "Davranışsal (Behavioral)",
            "module": "src.patterns.strategy",
            "classes": "NavigationSystem, RoutePlanningStrategy, ShortestPathStrategy, RadarEvasionStrategy, LoiteringSearchStrategy",
            "status": "Tamamlandı (Aşama 6)",
        },
    ]


def render_design_patterns_page() -> None:
    """Beş GoF tasarım kalıbının UML diyagramlarını ve sınıf ilişkilerini gösteren ekranı çizer."""
    render_pattern_header(
        badge="MİMARİ DOKÜMANTASYON & UML SINIF DİYAGRAMLARI",
        title="Gang of Four (GoF) Tasarım Kalıpları ve SOLID Prensipleri",
        problem_solved=(
            "Uygulamanın merkezinde yer alan 5 GoF tasarım kalıbının (Builder, Adapter, Decorator, State, Strategy) "
            "sınıf hiyerarşilerini, GoF katılımcı rollerini ve kalıplar arası etkileşimi belgeler."
        ),
        participants="Builder (Yaratımsal) | Adapter & Decorator (Yapısal) | State & Strategy (Davranışsal)",
    )

    st.subheader("📋 GoF Tasarım Kalıpları Özet Tablosu")
    st.dataframe(get_architecture_overview(), use_container_width=True, hide_index=True)

    st.divider()

    doc_path = Path(__file__).resolve().parents[2] / "docs" / "architecture_and_uml.md"
    if doc_path.exists():
        st.subheader("📐 Detaylı Mimari Analiz ve Mermaid UML Diyagramları")
        content = doc_path.read_text(encoding="utf-8")
        st.markdown(content)
    else:
        st.warning("`docs/architecture_and_uml.md` dosyası bulunamadı.")
