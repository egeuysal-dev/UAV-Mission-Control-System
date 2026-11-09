"""
Koyu temalı teknik simülasyon kontrol paneli için ortak stil, Üst Telemetri
Durum Şeridi (Top HUD Bar) ve GoF tasarım kalıbı bilgi kartı bileşenleri.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def inject_custom_css() -> None:
    """Koyu havacılık kontrol paneli (YKİ / GCS) görünümü için özel CSS kurallarını enjekte eder."""
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0b1120;
            color: #f1f5f9;
        }
        /* Üst Aviyonik Telemetri Durum Şeridi (Top HUD Bar) */
        .top-hud-bar {
            background: linear-gradient(90deg, #090d16 0%, #111827 50%, #090d16 100%);
            border: 1px solid #1e293b;
            border-bottom: 2px solid #06b6d4;
            border-radius: 10px;
            padding: 0.65rem 1.1rem;
            margin-bottom: 1.1rem;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.5);
            font-family: 'Consolas', 'Courier New', monospace;
        }
        .hud-item {
            display: flex;
            flex-direction: column;
            padding: 0.15rem 0.6rem;
            border-right: 1px solid #1e293b;
        }
        .hud-item:last-child {
            border-right: none;
        }
        .hud-label {
            font-size: 0.68rem;
            color: #94a3b8;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.1rem;
        }
        .hud-value {
            font-size: 0.95rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .phase-pill {
            display: inline-block;
            padding: 0.18rem 0.65rem;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.05em;
        }
        .phase-idle { background-color: #334155; color: #e2e8f0; border: 1px solid #64748b; }
        .phase-takeoff { background-color: #0369a1; color: #e0f2fe; border: 1px solid #38bdf8; }
        .phase-cruise { background-color: #065f46; color: #d1fae5; border: 1px solid #10b981; }
        .phase-combat { background-color: #9a3412; color: #ffedd5; border: 1px solid #f97316; }
        .phase-emergency {
            background-color: #991b1b;
            color: #fee2e2;
            border: 1px solid #ef4444;
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.75);
        }
        .sec-chip {
            display: inline-block;
            background-color: #1e293b;
            border: 1px solid #0891b2;
            color: #67e8f9;
            font-size: 0.72rem;
            padding: 0.1rem 0.45rem;
            border-radius: 4px;
            margin-right: 0.25rem;
        }
        /* Tasarım Kalıbı Bilgi Kartı */
        .pattern-banner {
            background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
            border-left: 4px solid #06b6d4;
            border-radius: 8px;
            padding: 0.9rem 1.2rem;
            margin-bottom: 1.15rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
        }
        .pattern-badge {
            display: inline-block;
            background-color: #0891b2;
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.18rem 0.55rem;
            border-radius: 4px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .pattern-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #38bdf8;
            margin: 0.15rem 0;
        }
        .pattern-desc {
            font-size: 0.88rem;
            color: #cbd5e1;
            margin: 0.2rem 0 0 0;
            line-height: 1.45;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_hud_bar(hud: Dict[str, Any]) -> None:
    """
    Ekranın en üstünde gerçek bir Yer Kontrol İstasyonu (YKİ / GCS) telemetri
    durum şeridi (Top HUD Bar) çizer.
    """
    phase = hud["flight_phase"]
    phase_css_map = {
        "PREFLIGHT_IDLE": "phase-idle",
        "TAKE_OFF": "phase-takeoff",
        "CRUISE": "phase-cruise",
        "COMBAT": "phase-combat",
        "EMERGENCY_RETURN": "phase-emergency",
    }
    pill_cls = phase_css_map.get(phase, "phase-idle")

    sec_html = "".join(
        f'<span class="sec-chip">{badge}</span>' for badge in hud["security_badges"]
    )
    snr_color = "#22c55e" if hud["datalink_snr_db"] >= 20.0 else "#f59e0b"
    fuel_color = (
        "#22c55e"
        if hud["fuel_pct"] > 35.0
        else ("#f59e0b" if hud["fuel_pct"] > 15.0 else "#ef4444")
    )

    st.markdown(
        f"""
        <div class="top-hud-bar">
            <div class="hud-item">
                <span class="hud-label">🛰️ PLATFORM ({hud['mission_type']})</span>
                <span class="hud-value" style="color:#38bdf8;">{hud['uav_model']}</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">⏱️ GÖREV SAATİ</span>
                <span class="hud-value">{hud['mission_clock_str']}</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">🚦 AKTİF UÇUŞ FAZI (STATE)</span>
                <span class="phase-pill {pill_cls}">{phase}</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">🧭 BAŞ AÇISI (HDG)</span>
                <span class="hud-value">{hud['heading_deg']:05.1f}° ({hud['heading_cardinal']})</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">⛽ YAKIT DURUMU</span>
                <span class="hud-value" style="color:{fuel_color};">{hud['fuel_remaining_kg']:.0f} kg (%{hud['fuel_pct']:.0f})</span>
            </div>
            <div class="hud-item">
                <span class="hud-label">📡 VERİ BAĞI &amp; SNR</span>
                <span class="hud-value">{hud['datalink_band']} | <span style="color:{snr_color};">{hud['datalink_snr_db']:.1f} dB</span></span>
            </div>
            <div class="hud-item">
                <span class="hud-label">🛡️ DECORATOR GÜVENLİK</span>
                <div>{sec_html}</div>
            </div>
            <div class="hud-item">
                <span class="hud-label">🔋 AVİYONİK &amp; GPS</span>
                <span class="hud-value">{hud['bus_voltage_v']:.1f}V | {hud['gps_status']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pattern_header(
    badge: str,
    title: str,
    problem_solved: str,
    participants: str,
) -> None:
    """
    Her ekranın üst kısmında kullanılan tasarım kalıbının hangi problemi çözdüğünü
    ve katılımcı sınıflarını açıkça gösteren teknik bilgi kartını çizer.
    """
    st.markdown(
        f"""
        <div class="pattern-banner">
            <div class="pattern-badge">{badge}</div>
            <div class="pattern-title">{title}</div>
            <div class="pattern-desc">
                <strong>Çözülen Mimari Problem:</strong> {problem_solved}<br/>
                <strong>Katılımcı Sınıflar:</strong> <code>{participants}</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
