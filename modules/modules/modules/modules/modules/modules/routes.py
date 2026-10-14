# modules/rutas.py
import streamlit as st
import pandas as pd
from database import get_session, ShipmentRoute
from i18n import t

def render(company: str, lang: str):
    st.header(f"🚚 {t('routes', lang)}")
    session = get_session(company)

    routes = pd.read_sql(session.query(ShipmentRoute).statement, session.bind)
    if routes.empty:
        st.info("No hay rutas planificadas.")
    else:
        st.dataframe(routes[["code", "carrier", "date", "status", "stops"]],
                     use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Estado de rutas")
        status_counts = routes["status"].value_counts()
        st.bar_chart(status_counts)

    session.close()