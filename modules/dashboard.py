# modules/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from sqlalchemy import func
from database import get_session, SalesOrder, PurchaseOrder, Item, DemandLine, ShipmentRoute
from i18n import t

def render(company: str, lang: str):
    st.header(f"📊 {t('dashboard', lang)}")
    session = get_session(company)

    # --- Datos base ---
    so_count = session.query(SalesOrder).count()
    so_open = session.query(SalesOrder).filter(SalesOrder.status.in_(["OPEN", "PICKING"])).count()
    po_count = session.query(PurchaseOrder).count()
    po_qc = session.query(PurchaseOrder).filter(PurchaseOrder.status == "QC_PENDING").count()

    items = pd.read_sql(session.query(Item).statement, session.bind)
    demand = pd.read_sql(session.query(DemandLine).filter(DemandLine.action == "PENDING").statement, session.bind)
    routes = pd.read_sql(session.query(ShipmentRoute).statement, session.bind)

    # --- KPIs simulados (en producción vendrían de logs/eventos) ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("kpi_orders_accuracy", lang), "98.2 %", "+0.4")
    col2.metric(t("kpi_picks_hour", lang), "42", "+3")
    col3.metric(t("kpi_dock_to_stock", lang), "3.5 h", "-0.5")
    col4.metric(t("kpi_inventory_turnover", lang), "6.8", "+0.2")

    st.divider()

    # --- Estado general ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pedidos venta abiertos", so_open)
    c2.metric("Pedidos compra totales", po_count)
    c3.metric("Pendientes Calidad", po_qc)
    c4.metric("Líneas de demanda", len(demand))

    st.divider()

    # --- Gráficos ---
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Stock vs. Mínimo")
        if not items.empty:
            fig = px.bar(
                items, x="code", y=["stock", "min_stock"],
                barmode="group", labels={"value": "Unidades", "code": "Artículo"},
                color_discrete_sequence=["#2E86AB", "#E63946"]
            )
            st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.subheader("Rutas de hoy")
        if not routes.empty:
            fig = px.pie(routes, names="carrier", values="stops",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Alertas ---
    st.subheader("⚠️ Alertas")
    alerts = []
    if not items.empty:
        low = items[items["stock"] < items["min_stock"]]
        for _, r in low.iterrows():
            alerts.append(f"🔴 **{r['code']}** — {r['description']}: stock {r['stock']} < mínimo {r['min_stock']}")
    if po_qc > 0:
        alerts.append(f"🟡 {po_qc} pedido(s) de compra pendientes de inspección de Calidad.")
    if not alerts:
        alerts.append("✅ Sin alertas críticas.")
    for a in alerts:
        st.markdown(a)

    session.close()