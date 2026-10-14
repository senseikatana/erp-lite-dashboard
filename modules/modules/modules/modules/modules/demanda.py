# modules/demanda.py
import streamlit as st
import pandas as pd
from database import get_session, DemandLine, Item
from i18n import t

def render(company: str, lang: str):
    st.header(f"📈 {t('demand', lang)}")
    session = get_session(company)

    demand = pd.read_sql(
        session.query(DemandLine).filter(DemandLine.action == "PENDING").statement,
        session.bind
    )
    items = pd.read_sql(session.query(Item).statement, session.bind)

    if demand.empty:
        st.success("✅ No hay necesidades de compra pendientes.")
    else:
        merged = demand.merge(items, left_on="item_id", right_on="id", suffixes=("", "_item"))
        st.dataframe(
            merged[["code", "description", "quantity_needed", "required_date", "source"]],
            use_container_width=True, hide_index=True
        )

        if st.button("🛒 Generar pedidos de compra sugeridos"):
            st.info("En la siguiente iteración conectaremos esto con el módulo de Compras para crear POs automáticamente.")
            # Aquí iría la lógica: agrupar por proveedor preferido y crear PurchaseOrder

    st.divider()
    st.subheader("Simulador de reposición")
    if not items.empty:
        item_sel = st.selectbox("Artículo", items["description"].tolist())
        row = items[items["description"] == item_sel].iloc[0]
        cobertura = st.slider("Días de cobertura deseados", 1, 60, 15)
        consumo_diario = st.number_input("Consumo diario estimado (uds)", min_value=1.0, value=10.0)
        sugerido = max(0, cobertura * consumo_diario - row["stock"])
        st.metric("Cantidad sugerida a pedir", f"{sugerido:.0f} uds")

    session.close()