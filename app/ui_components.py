"""Shared presentation for the career workspace. No data or business mutations."""
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st


def html(value):
    return escape(str(value if value is not None else ""))


def load_theme():
    css = Path(__file__).with_name("assets").joinpath("workspace.css").read_text(encoding="utf-8")
    st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)


def page_header(kicker, title, subtitle):
    st.markdown(
        '<header class="page-header"><div class="eyebrow">{0}</div>'
        '<h1>{1}</h1><p>{2}</p></header>'.format(html(kicker), html(title), html(subtitle)),
        unsafe_allow_html=True,
    )


def section_heading(title, note="", number=""):
    st.markdown(
        '<div class="section-heading"><div><span class="section-number">{0}</span>'
        '<h2>{1}</h2></div><span>{2}</span></div>'.format(html(number), html(title), html(note)),
        unsafe_allow_html=True,
    )


def empty_state(title, description):
    st.markdown('<div class="empty-state"><strong>{0}</strong><p>{1}</p></div>'.format(html(title), html(description)), unsafe_allow_html=True)


def format_date(value):
    try:
        return datetime.fromisoformat(value).strftime("%m 月 %d 日 · %H:%M")
    except (ValueError, TypeError):
        return value or "时间未记录"


def model_mode_label(mode):
    return {"model": "模型生成", "demo": "本地演示", "demo_fallback": "本地回退演示"}.get(mode or "", "状态未知")


def grounding_label(status):
    return {
        "grounded": "台账标注已核实", "verified": "台账标注已核实",
        "review_required": "资料待复核", "placeholder": "包含示例资料", "no_sources": "暂无可靠资料",
    }.get(status or "", "资料状态未知")


def render_runtime_state(mode, grounding):
    st.markdown(
        '<div class="state-strip"><span class="state-pill {0}">{1}</span>'
        '<span class="state-pill {2}">{3}</span></div>'.format(
            "ok" if mode == "model" else "warn", model_mode_label(mode),
            "ok" if grounding in ("grounded", "verified") else "warn", grounding_label(grounding)),
        unsafe_allow_html=True,
    )


def safe_link(url):
    try:
        parsed = urlparse(str(url or ""))
        return str(url) if parsed.scheme in ("http", "https") and parsed.netloc else None
    except ValueError:
        return None


def render_sources(sources):
    if not sources:
        empty_state("暂无可靠资料依据", "当前内容仅作为基于画像的初步建议，可在补充资料后重新生成。")
        return
    with st.expander("资料依据 · {0} 项来源".format(len(sources))):
        for source in sources:
            labels = []
            if source.get("is_placeholder"):
                labels.append("示例资料")
            labels.append({"verified": "台账标注已核实", "pending_review": "待复核"}.get(source.get("review_status"), "未标注复核状态"))
            if source.get("freshness") == "time_sensitive":
                labels.append("时效性资料")
            url = safe_link(source.get("source_url"))
            title = html(source.get("title", "资料"))
            if url:
                title = '<a href="{0}" target="_blank" rel="noopener noreferrer">{1} ↗</a>'.format(html(url), title)
            st.markdown('<article class="source-row"><strong>{0}</strong><p>{1} · {2}</p><span>{3}</span></article>'.format(
                title, html(source.get("source_name") or "来源未提供"), html(source.get("updated_at") or "更新时间未提供"), html(" · ".join(labels))), unsafe_allow_html=True)


def render_resources(resources):
    for resource in (resources or [])[:2]:
        url = safe_link(resource.get("source_url"))
        if not url:
            continue
        details = [resource.get("source_name") or "来源未提供"]
        for field in ("recommendation_hint", "language", "access_note", "updated_at"):
            if resource.get(field):
                details.append(resource[field])
        details.append({"verified": "台账标注已核实", "pending_review": "待复核"}.get(resource.get("review_status"), "未标注复核状态"))
        st.markdown('<div class="resource-link"><span>学习资料</span><a href="{0}" target="_blank" rel="noopener noreferrer">{1} ↗</a><p>{2}</p></div>'.format(
            html(url), html(resource.get("title", "学习资料")), html(" · ".join(details))), unsafe_allow_html=True)
