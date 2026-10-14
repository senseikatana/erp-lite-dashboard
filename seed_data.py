# seed_data.py
from datetime import date, timedelta
from database import (
    get_session, Customer, Vendor, Item, SalesOrder, SalesOrderLine,
    PurchaseOrder, PurchaseOrderLine, DemandLine, ShipmentRoute
)
from config import DEFAULT_COMPANY

def seed(company_code: str = DEFAULT_COMPANY):
    session = get_session(company_code)

    # Si ya hay datos, no sembrar de nuevo
    if session.query(Customer).count() > 0:
        return

    # Clientes
    customers = [
        Customer(code="C001", name="Supermercados Nordeste", city="Barcelona", postal_code="08001", email="compras@snordeste.es"),
        Customer(code="C002", name="Distribuciones Girona", city="Girona", postal_code="17001", email="info@dgi.com"),
        Customer(code="C003", name="Alimentación Lleida", city="Lleida", postal_code="25001"),
    ]
    session.add_all(customers)

    # Proveedores
    vendors = [
        Vendor(code="P001", name="Packaging Ibérica", lead_time_days=5, quality_rating=4.5),
        Vendor(code="P002", name="Metalúrgica Tarragona", lead_time_days=12, quality_rating=4.0),
        Vendor(code="P003", name="Plásticos del Vallès", lead_time_days=7, quality_rating=4.8),
    ]
    session.add_all(vendors)
    session.flush()

    # Artículos
    items = [
        Item(code="ART-001", description="Caja cartón 40x30x20", unit="UD", unit_cost=0.45, unit_price=0.85, stock=1200, min_stock=300, location="A-01", category="Packaging"),
        Item(code="ART-002", description="Film retráctil 50cm", unit="ROLLO", unit_cost=8.20, unit_price=14.50, stock=45, min_stock=20, location="B-03", category="Packaging"),
        Item(code="ART-003", description="Palet europeo madera", unit="UD", unit_cost=12.00, unit_price=20.00, stock=80, min_stock=50, location="C-01", category="Logística"),
        Item(code="ART-004", description="Etiqueta adhesiva 100x50", unit="MILLAR", unit_cost=6.50, unit_price=12.00, stock=15, min_stock=10, location="A-02", category="Etiquetado"),
        Item(code="ART-005", description="Esquinero plástico", unit="UD", unit_cost=0.15, unit_price=0.35, stock=2400, min_stock=500, location="D-02", category="Packaging"),
    ]
    session.add_all(items)
    session.flush()

    # Pedidos de venta
    so1 = SalesOrder(
        number="SO-2024-0001", customer_id=customers[0].id,
        order_date=date.today(), delivery_date=date.today() + timedelta(days=2),
        status="OPEN", total=0
    )
    so1.lines = [
        SalesOrderLine(item_id=items[0].id, quantity=500, unit_price=0.85),
        SalesOrderLine(item_id=items[4].id, quantity=1000, unit_price=0.35),
    ]
    so1.total = sum(l.quantity * l.unit_price for l in so1.lines)

    so2 = SalesOrder(
        number="SO-2024-0002", customer_id=customers[1].id,
        order_date=date.today(), delivery_date=date.today() + timedelta(days=1),
        status="PICKING", total=0
    )
    so2.lines = [
        SalesOrderLine(item_id=items[1].id, quantity=10, unit_price=14.50, qty_picked=10),
    ]
    so2.total = sum(l.quantity * l.unit_price for l in so2.lines)

    session.add_all([so1, so2])

    # Pedidos de compra
    po1 = PurchaseOrder(
        number="PO-2024-0001", vendor_id=vendors[0].id,
        order_date=date.today() - timedelta(days=3),
        expected_date=date.today() + timedelta(days=2),
        status="OPEN", total=0
    )
    po1.lines = [PurchaseOrderLine(item_id=items[0].id, quantity=2000, unit_cost=0.45)]
    po1.total = sum(l.quantity * l.unit_cost for l in po1.lines)

    po2 = PurchaseOrder(
        number="PO-2024-0002", vendor_id=vendors[2].id,
        order_date=date.today() - timedelta(days=7),
        expected_date=date.today(),
        status="QC_PENDING", total=0
    )
    po2.lines = [PurchaseOrderLine(item_id=items[1].id, quantity=50, unit_cost=8.20, qty_received=50, qc_status="PENDING")]
    po2.total = sum(l.quantity * l.unit_cost for l in po2.lines)

    session.add_all([po1, po2])

    # Hoja de demanda (artículos bajo mínimos)
    demand_lines = []
    for it in items:
        if it.stock < it.min_stock * 1.5:
            needed = max(it.min_stock * 2 - it.stock, 0)
            demand_lines.append(DemandLine(
                item_id=it.id,
                required_date=date.today() + timedelta(days=7),
                quantity_needed=needed,
                source="MIN_STOCK",
                action="PENDING"
            ))
    session.add_all(demand_lines)

    # Rutas
    routes = [
        ShipmentRoute(code="RUTA-001", carrier="SEUR", date=date.today(), status="PLANNED", stops=4),
        ShipmentRoute(code="RUTA-002", carrier="DHL", date=date.today(), status="IN_TRANSIT", stops=3),
        ShipmentRoute(code="RUTA-003", carrier="Propio", date=date.today() + timedelta(days=1), status="PLANNED", stops=6),
    ]
    session.add_all(routes)

    session.commit()
    session.close()
    print(f"✅ Datos de ejemplo cargados en {company_code}")

if __name__ == "__main__":
    seed()