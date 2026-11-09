"""
Koyu temalı teknik simülasyon kontrol paneli için ortak stil, başlık ve
GoF tasarım kalıbı bilgi kartı bileşenleri.
"""

from __future__ import annotations

import streamlit as st


def inject_custom_css() -> None:
    """Koyu havacılık kontrol paneli görünümü için özel CSS kurallarını enjekte eder."""
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0b1120;
            color: #f1f5f9;
        }
        .pattern-banner {
            background: linear-gradient(135deg, #111827 0%, #1e293b 100%);
            border-left: 4px solid #06b6d4;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
        }
        .pattern-badge {
            display: inline-block;
            background-color: #0891b2;
            color: #ffffff;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }
        .pattern-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #38bdf8;
            margin: 0.2rem 0;
        }
        .pattern-desc {
            font-size: 0.92rem;
            color: #cbd5e1;
            margin: 0.25rem 0 0 0;
            line-height: 1.5;
        }
        .hud-box {
            background-color: #111827;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin-bottom: 0.75rem;
        }
        </style>
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
