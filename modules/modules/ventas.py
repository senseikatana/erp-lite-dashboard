# modules/ventas.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import get_session, SalesOrder, SalesOrderLine, Customer, Item
from i18n import t

def render(company: str, lang: str):
    st.header(f"🛒 {t('sales', lang)}")
    session = get_session(company)

    tab1, tab2 = st.tabs(["📋 Pedidos", "➕ Nuevo pedido"])

    with tab1:
        orders = pd.read_sql(session.query(SalesOrder).statement, session.bind)
        if orders.empty:
            st.info("No hay pedidos de venta.")
        else:
            # Filtro por estado
            status_filter = st.multiselect(
                "Filtrar por estado",
                options=orders["status"].unique().tolist(),
                default=orders["status"].unique().tolist()
            )
            filtered = orders[orders["status"].isin(status_filter)]

            for _, o in filtered.iterrows():
                with st.expander(f"**{o['number']}** · Cliente #{o['customer_id']} · {o['status']} · {o['total']:.2f} €"):
                    st.write(f"Fecha pedido: {o['order_date']}")
                    st.write(f"Fecha entrega: {o['delivery_date']}")
                    # Líneas
                    lines = pd.read_sql(
                        session.query(SalesOrderLine).filter(SalesOrderLine.order_id == o["id"]).statement,
                        session.bind
                    )
                    st.dataframe(lines[["item_id", "quantity", "unit_price", "qty_picked", "qty_shipped"]],
                                 use_container_width=True)

                    c1, c2, c3 = st.columns(3)
                    if o["status"] == "OPEN" and c1.button(f"▶️ Picking", key=f"pick_{o['id']}"):
                        session.query(SalesOrder).filter_by(id=o["id"]).update({"status": "PICKING"})
                        session.commit()
                        st.rerun()
                    if o["status"] == "PICKING" and c2.button(f"🚚 Enviar", key=f"ship_{o['id']}"):
                        session.query(SalesOrder).filter_by(id=o["id"]).update({"status": "SHIPPED"})
                        session.commit()
                        st.rerun()
                    if o["status"] == "SHIPPED" and c3.button(f"🧾 Facturar", key=f"inv_{o['id']}"):
                        session.query(SalesOrder).filter_by(id=o["id"]).update({"status": "INVOICED"})
                        session.commit()
                        st.rerun()

    with tab2:
        st.subheader(t("new_order", lang))
        customers = pd.read_sql(session.query(Customer).statement, session.bind)
        items = pd.read_sql(session.query(Item).statement, session.bind)

        if customers.empty or items.empty:
            st.warning("Necesitas clientes y artículos registrados.")
            session.close()
            return

        with st.form("new_so"):
            cust = st.selectbox("Cliente", customers["name"].tolist())
            cust_id = int(customers[customers["name"] == cust]["id"].iloc[0])
            deliv = st.date_input("Fecha entrega", value=date.today() + timedelta(days=2))
            item_names = st.multiselect("Artículos", items["description"].tolist())
            quantities = {}
            for it in item_names:
                quantities[it] = st.number_input(f"Cantidad · {it}", min_value=1.0, value=1.0, step=1.0)
            submitted = st.form_submit_button(t("save", lang))

            if submitted and item_names:
                last = session.query(SalesOrder).count() + 1
                number = f"SO-{date.today().year}-{last:04d}"
                so = SalesOrder(number=number, customer_id=cust_id,
                                delivery_date=deliv, status="OPEN", total=0.0)
                session.add(so)
                session.flush()
                total = 0.0
                for it_name in item_names:
                    row = items[items["description"] == it_name].iloc[0]
                    qty = quantities[it_name]
                    price = float(row["unit_price"])
                    line = SalesOrderLine(order_id=so.id, item_id=int(row["id"]),
                                          quantity=qty, unit_price=price)
                    session.add(line)
                    total += qty * price
                so.total = total
                session.commit()
                st.success(f"Pedido {number} creado.")
                st.rerun()

    session.close()