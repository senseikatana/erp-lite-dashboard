# modules/almacen.py
import streamlit as st
import pandas as pd
from database import get_session, Item
from i18n import t

def render(company: str, lang: str):
    st.header(f"🏭 {t('warehouse', lang)}")
    session = get_session(company)
    items = pd.read_sql(session.query(Item).statement, session.bind)

    if items.empty:
        st.info("No hay artículos registrados.")
        session.close()
        return

    st.subheader("Inventario actual")
    # Semáforo de stock
    def stock_status(row):
        if row["stock"] < row["min_stock"]:
            return "🔴 Bajo mínimo"
        elif row["stock"] < row["min_stock"] * 1.5:
            return "🟡 Cerca del mínimo"
        return "🟢 OK"

    items["estado"] = items.apply(stock_status, axis=1)
    st.dataframe(
        items[["code", "description", "category", "location", "stock", "min_stock", "estado"]],
        use_container_width=True, hide_index=True
    )

    st.divider()
    st.subheader("Picking por ubicación")
    locs = items.groupby("location")["stock"].sum().reset_index()
    st.bar_chart(locs.set_index("location"))

    session.close()