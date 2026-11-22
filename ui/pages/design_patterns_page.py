"""
Ekran 7: Design Patterns — Görsel Mermaid UML Sınıf Diyagramları ve Canlı Kalıp Nesne Denetçisi.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

from src.simulation.mission_simulator import MissionSimulator
from ui.components.theme import render_pattern_header


def get_architecture_overview() -> List[Dict[str, str]]:
    """Projedeki 5 GoF tasarım kalıbının mimari özet tablosunu döndürür."""
    return [
        {
            "pattern": "1. Builder",
            "category": "Yaratımsal (Creational)",
            "module": "src.patterns.builder",
            "classes": "UAVConfigurationBuilder, StrikeUAVBuilder, ReconUAVBuilder, MissionPrepDirector, UAVPlatform",
            "status": "Tamamlandı (Aşama 2 + Öneri D)",
        },
        {
            "pattern": "2. Adapter",
            "category": "Yapısal (Structural)",
            "module": "src.patterns.adapter",
            "classes": "TargetSensor, StanagRadarAdapter, ThermalCameraAdapter, LegacyStanagRadarSDK, VendorThermalDevice, MissionComputer",
            "status": "Tamamlandı (Aşama 3 + Öneri E)",
        },
        {
            "pattern": "3. Decorator",
            "category": "Yapısal (Structural)",
            "module": "src.patterns.decorator",
            "classes": "TelemetryChannel, BaseRadioChannel, TelemetryChannelDecorator, AesEncryptionDecorator, CompressionDecorator, AntiJammingDecorator",
            "status": "Tamamlandı (Aşama 4 + Öneri F)",
        },
        {
            "pattern": "4. State",
            "category": "Davranışsal (Behavioral)",
            "module": "src.patterns.state",
            "classes": "FlightController, FlightPhaseState, PreflightIdleState, TakeOffState, CruiseState, CombatState, EmergencyReturnState",
            "status": "Tamamlandı (Aşama 5 + Öneri G)",
        },
        {
            "pattern": "5. Strategy",
            "category": "Davranışsal (Behavioral)",
            "module": "src.patterns.strategy",
            "classes": "NavigationSystem, RoutePlanningStrategy, ShortestPathStrategy, RadarEvasionStrategy, LoiteringSearchStrategy",
            "status": "Tamamlandı (Aşama 6 + Öneri B/C)",
        },
    ]


def extract_mermaid_blocks(markdown_text: str) -> List[Tuple[str, str]]:
    """
    `docs/architecture_and_uml.md` dosyasındaki tüm ```mermaid ... ``` bloklarını
    başlıklarıyla birlikte ayrıştırır.
    """
    titles = [
        "0. Sistem Geneli — 5 Kalıp Etkileşim Akışı",
        "1. Builder Kalıbı (UML Sınıf Diyagramı)",
        "2. Adapter Kalıbı (UML Sınıf Diyagramı)",
        "3. Decorator Kalıbı (UML Sınıf Diyagramı)",
        "4. State Kalıbı (UML Sınıf Diyagramı)",
        "5. Strategy Kalıbı (UML Sınıf Diyagramı)",
    ]
    matches = re.findall(r"```mermaid\s*(.*?)```", markdown_text, flags=re.DOTALL)
    result: List[Tuple[str, str]] = []
    for idx, code in enumerate(matches):
        label = titles[idx] if idx < len(titles) else f"Diyagram #{idx + 1}"
        result.append((label, code.strip()))
    return result


def build_live_pattern_inspection(sim: MissionSimulator) -> List[Dict[str, Any]]:
    """
    Öneri H — Canlı Kalıp Nesne Denetçisi (Live Pattern Object Inspector):
    `MissionSimulator` içinde o an bellekte aktif olan 5 GoF tasarım kalıbı
    nesnesinin gerçek Python sınıflarını, bellek adreslerini (`id`) ve anlık
    çalışma zamanı durumlarını döndürür.
    """
    uav = sim.active_platform
    mc = sim.mission_computer
    fc = sim.flight_controller
    nav = sim.navigation_system
    active_channel = sim.build_telemetry_channel()

    return [
        {
            "pattern": "1. Builder (Yaratımsal)",
            "context_or_product": f"{type(uav).__name__} @ {hex(id(uav))}",
            "active_concrete_class": (
                "StrikeUAVBuilder -> UAVPlatform"
                if uav.mission_type == "STRIKE"
                else "ReconUAVBuilder -> UAVPlatform"
            ),
            "runtime_state": (
                f"Model: {uav.model_name} | Tip: {uav.mission_type} | "
                f"Ağırlık: {uav.total_weight_kg:.1f}/{uav.max_takeoff_weight_kg:.0f} kg | "
                f"Sensör: {len(uav.sensors)} | Yük: {len(uav.payloads)}"
            ),
        },
        {
            "pattern": "2. Adapter (Yapısal)",
            "context_or_product": f"{type(mc).__name__} @ {hex(id(mc))}",
            "active_concrete_class": (
                f"{type(sim.radar_adapter).__name__}({type(sim.radar_adapter.adaptee).__name__}), "
                f"{type(sim.thermal_adapter).__name__}({type(sim.thermal_adapter.adaptee).__name__})"
            ),
            "runtime_state": (
                f"Kayıtlı Adaptör: {len(mc.get_registered_sensors())} | "
                f"Son Normalize Hedef: {len(sim.last_targets)} iz"
            ),
        },
        {
            "pattern": "3. Decorator (Yapısal)",
            "context_or_product": f"{type(active_channel).__name__} @ {hex(id(active_channel))}",
            "active_concrete_class": active_channel.format_wrapping_chain(),
            "runtime_state": (
                f"Bant: {sim.frequency_band} | Aktif Katman: {len(sim.decorator_layers)} | "
                f"Son Paket: {sim.last_telemetry_packet.final_size_bytes if sim.last_telemetry_packet else 0} Bayt"
            ),
        },
        {
            "pattern": "4. State (Davranışsal)",
            "context_or_product": f"{type(fc).__name__} @ {hex(id(fc))}",
            "active_concrete_class": f"{type(fc.state).__name__} @ {hex(id(fc.state))}",
            "runtime_state": (
                f"Faz: {fc.current_phase_name} | İrtifa: {fc.altitude_m:.0f} m | "
                f"Hız: {fc.speed_knots:.0f} kts | Motor: %{fc.throttle_pct:.0f}"
            ),
        },
        {
            "pattern": "5. Strategy (Davranışsal)",
            "context_or_product": f"{type(nav).__name__} @ {hex(id(nav))}",
            "active_concrete_class": f"{type(nav.strategy).__name__} @ {hex(id(nav.strategy))}",
            "runtime_state": (
                f"Strateji: {nav.strategy.strategy_name} | "
                f"Rota: {sim.last_route_plan.total_distance_km if sim.last_route_plan else 0:.1f} km | "
                f"İlerleme: %{sim.route_progress_pct:.1f}"
            ),
        },
    ]


def _render_mermaid_svg_component(mermaid_code: str, height_px: int = 560) -> None:
    """
    Mermaid UML diyagramını koyu havacılık temasıyla tarayıcı içinde gerçek
    etkileşimli SVG grafiği olarak çizer (`streamlit.components.v1.html`).

    Not: `mermaid.render()` API'si ile JSON üzerinden ham kaynak metin aktarılır;
    böylece `<<abstract>>`, `<|--` ve `~` gibi UML karakterleri HTML kaçışından
    etkilenmeden her zaman eksiksiz SVG olarak üretilir.
    """
    json_source = json.dumps(mermaid_code)
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{
          margin: 0;
          padding: 14px;
          background-color: #0f172a;
          color: #e2e8f0;
          font-family: 'Segoe UI', Tahoma, sans-serif;
          display: flex;
          justify-content: center;
          align-items: flex-start;
          overflow: auto;
        }}
        .mermaid-wrap {{
          width: 100%;
          min-height: 200px;
          text-align: center;
          background: #111827;
          border: 1px solid #1e293b;
          border-radius: 10px;
          padding: 18px;
          box-sizing: border-box;
        }}
        .mermaid-wrap svg {{
          max-width: 100% !important;
          height: auto !important;
        }}
        .err-box {{
          color: #fca5a5;
          background: #450a0a;
          border: 1px solid #ef4444;
          border-radius: 6px;
          padding: 12px;
          text-align: left;
          font-family: Consolas, monospace;
          font-size: 13px;
        }}
      </style>
    </head>
    <body>
      <div id="mermaid-target" class="mermaid-wrap">Diyagram çiziliyor...</div>
      <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
        const diagramSource = {json_source};
        mermaid.initialize({{
          startOnLoad: false,
          securityLevel: 'loose',
          theme: 'dark',
          themeVariables: {{
            primaryColor: '#1e293b',
            primaryTextColor: '#f8fafc',
            primaryBorderColor: '#06b6d4',
            lineColor: '#38bdf8',
            secondaryColor: '#0f172a',
            tertiaryColor: '#111827',
            fontFamily: 'Consolas, Segoe UI, sans-serif'
          }}
        }});
        const targetEl = document.getElementById('mermaid-target');
        try {{
          const {{ svg }} = await mermaid.render('uml_diagram_svg', diagramSource);
          targetEl.innerHTML = svg;
        }} catch (err) {{
          targetEl.innerHTML = `<div class="err-box"><strong>Mermaid Çizim Hatası:</strong><br/>${{String(err)}}</div>`;
        }}
      </script>
    </body>
    </html>
    """
    components.html(html_doc, height=height_px, scrolling=True)


def render_design_patterns_page(sim: Optional[MissionSimulator] = None) -> None:
    """Beş GoF tasarım kalıbının görsel UML diyagramlarını ve canlı nesne denetçisini çizer."""
    render_pattern_header(
        badge="MİMARİ DOKÜMANTASYON, GÖRSEL UML & CANLI NESNE DENETÇİSİ",
        title="Gang of Four (GoF) Tasarım Kalıpları, Görsel UML Diyagramları ve SOLID Prensipleri",
        problem_solved=(
            "Uygulamanın merkezinde yer alan 5 GoF tasarım kalıbının (Builder, Adapter, Decorator, State, Strategy) "
            "görsel UML sınıf diyagramlarını, GoF katılımcı rollerini ve o an bellekte çalışan gerçek Python nesnelerini belgeler."
        ),
        participants="Builder (Yaratımsal) | Adapter & Decorator (Yapısal) | State & Strategy (Davranışsal)",
    )

    # 1. Canlı Kalıp Nesne Denetçisi (Live Runtime Object Inspector)
    if sim is not None:
        st.subheader("🔬 Canlı Kalıp Nesne Denetçisi (Bellekteki Aktif GoF Nesneleri)")
        st.caption(
            "Diğer ekranlarda uçuş fazını, rota stratejisini, İHA platformunu veya telemetri katmanlarını "
            "değiştirdiğinizde, bu tablo Python çalışma zamanındaki gerçek sınıf referanslarını ve bellek adreslerini (`id`) canlı günceller."
        )
        live_rows = build_live_pattern_inspection(sim)
        st.dataframe(
            [
                {
                    "GoF Kalıbı": r["pattern"],
                    "Bağlam / Ürün Nesnesi (id)": r["context_or_product"],
                    "Aktif Somut Sınıf / Sarmalama Zinciri": r["active_concrete_class"],
                    "Anlık Çalışma Zamanı Durumu": r["runtime_state"],
                }
                for r in live_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.divider()

    # 2. Görsel Mermaid UML Diyagramları
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "architecture_and_uml.md"
    if doc_path.exists():
        content = doc_path.read_text(encoding="utf-8")
        mermaid_blocks = extract_mermaid_blocks(content)

        if mermaid_blocks:
            st.subheader("📐 İnteraktif Görsel UML Sınıf ve Akış Diyagramları (Mermaid SVG)")
            block_titles = [title for title, _ in mermaid_blocks]
            selected_idx = st.radio(
                "Görüntülenecek UML Diyagramını Seçin:",
                options=list(range(len(mermaid_blocks))),
                format_func=lambda i: block_titles[i],
                horizontal=True,
                key="uml_diagram_selector",
            )
            sel_title, sel_code = mermaid_blocks[selected_idx]
            diag_height = 580 if "Akışı" in sel_title or "Flowchart" in sel_title else 560
            _render_mermaid_svg_component(sel_code, height_px=diag_height)
            with st.expander(f"📝 {sel_title} — Mermaid Kaynak Kodu", expanded=False):
                st.code(sel_code, language="mermaid")

        st.divider()
        st.subheader("📋 GoF Tasarım Kalıpları Özet Tablosu")
        st.dataframe(get_architecture_overview(), use_container_width=True, hide_index=True)

        with st.expander("📄 Tam Mimari Analiz Dokümanını Oku (`docs/architecture_and_uml.md`)", expanded=False):
            st.markdown(content)
    else:
        st.warning("`docs/architecture_and_uml.md` dosyası bulunamadı.")
