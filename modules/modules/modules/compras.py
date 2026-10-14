# modules/compras.py
import streamlit as st
import pandas as pd
from datetime import date
from database import get_session, PurchaseOrder, PurchaseOrderLine, Vendor, Item
from i18n import t

def render(company: str, lang: str):
    st.header(f"📦 {t('purchases', lang)}")
    session = get_session(company)

    tab1, tab2 = st.tabs(["📋 Pedidos", "✅ Recepción + Calidad"])

    with tab1:
        orders = pd.read_sql(session.query(PurchaseOrder).statement, session.bind)
        if orders.empty:
            st.info("No hay pedidos de compra.")
        else:
            for _, o in orders.iterrows():
                with st.expander(f"**{o['number']}** · Proveedor #{o['vendor_id']} · {o['status']} · {o['total']:.2f} €"):
                    st.write(f"Fecha: {o['order_date']} · Entrega esperada: {o['expected_date']}")
                    lines = pd.read_sql(
                        session.query(PurchaseOrderLine).filter(PurchaseOrderLine.order_id == o["id"]).statement,
                        session.bind
                    )
                    st.dataframe(lines[["item_id", "quantity", "unit_cost", "qty_received", "qc_status"]],
                                 use_container_width=True)

    with tab2:
        st.subheader("Recepción de mercancía y control de calidad")
        pending = pd.read_sql(
            session.query(PurchaseOrder).filter(PurchaseOrder.status.in_(["OPEN", "RECEIVED", "QC_PENDING"])).statement,
            session.bind
        )
        if pending.empty:
            st.info("No hay pedidos pendientes de recepción.")
        else:
            po_sel = st.selectbox("Pedido a recepcionar", pending["number"].tolist())
            po_id = int(pending[pending["number"] == po_sel]["id"].iloc[0])

            lines = pd.read_sql(
                session.query(PurchaseOrderLine).filter(PurchaseOrderLine.order_id == po_id).statement,
                session.bind
            )
            st.dataframe(lines[["item_id", "quantity", "qty_received", "qc_status"]],
                         use_container_width=True)

            c1, c2, c3 = st.columns(3)
            if c1.button("📥 Registrar recepción"):
                for _, l in lines.iterrows():
                    session.query(PurchaseOrderLine).filter_by(id=l["id"]).update({
                        "qty_received": l["quantity"],
                        "qc_status": "PENDING"
                    })
                session.query(PurchaseOrder).filter_by(id=po_id).update({"status": "QC_PENDING"})
                session.commit()
                st.success("Recepción registrada. Pendiente de Calidad.")
                st.rerun()

            if c2.button("✅ Aprobar Calidad"):
                for _, l in lines.iterrows():
                    session.query(PurchaseOrderLine).filter_by(id=l["id"]).update({"qc_status": "PASSED"})
                    # Incrementar stock
                    item = session.query(Item).filter_by(id=l["item_id"]).first()
                    if item:
                        item.stock += l["quantity"]
                session.query(PurchaseOrder).filter_by(id=po_id).update({"status": "QC_APPROVED"})
                session.commit()
                st.success("Calidad aprobada. Stock actualizado.")
                st.rerun()

            if c3.button("❌ Rechazar Calidad"):
                for _, l in lines.iterrows():
                    session.query(PurchaseOrderLine).filter_by(id=l["id"]).update({"qc_status": "FAILED"})
                session.query(PurchaseOrder).filter_by(id=po_id).update({"status": "OPEN"})
                session.commit()
                st.warning("Calidad rechazada. Pedido devuelto a proveedor.")
                st.rerun()

    session.close()