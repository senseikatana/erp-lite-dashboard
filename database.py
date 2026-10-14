# database.py
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Boolean, Text, Date
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
from config import get_db_path, DEFAULT_COMPANY

Base = declarative_base()

# ---------- Entidades ----------

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(120))
    phone = Column(String(30))
    address = Column(String(200))
    city = Column(String(80))
    postal_code = Column(String(10))
    country = Column(String(60), default="España")
    tax_id = Column(String(20))

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(120))
    phone = Column(String(30))
    lead_time_days = Column(Integer, default=7)
    quality_rating = Column(Float, default=5.0)  # 0-5

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False)
    description = Column(String(200), nullable=False)
    unit = Column(String(10), default="UD")
    unit_cost = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    stock = Column(Float, default=0.0)
    min_stock = Column(Float, default=0.0)
    location = Column(String(20), default="A-01")
    category = Column(String(50))

class SalesOrder(Base):
    __tablename__ = "sales_orders"
    id = Column(Integer, primary_key=True)
    number = Column(String(20), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    order_date = Column(Date, default=datetime.utcnow)
    delivery_date = Column(Date)
    status = Column(String(20), default="OPEN")  # OPEN, PICKING, SHIPPED, INVOICED
    total = Column(Float, default=0.0)
    notes = Column(Text)
    customer = relationship("Customer")
    lines = relationship("SalesOrderLine", back_populates="order", cascade="all, delete-orphan")

class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    qty_picked = Column(Float, default=0.0)
    qty_shipped = Column(Float, default=0.0)
    order = relationship("SalesOrder", back_populates="lines")
    item = relationship("Item")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    number = Column(String(20), unique=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    order_date = Column(Date, default=datetime.utcnow)
    expected_date = Column(Date)
    status = Column(String(20), default="OPEN")  # OPEN, RECEIVED, QC_PENDING, QC_APPROVED, CLOSED
    total = Column(Float, default=0.0)
    vendor = relationship("Vendor")
    lines = relationship("PurchaseOrderLine", back_populates="order", cascade="all, delete-orphan")

class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Float, default=1.0)
    unit_cost = Column(Float, default=0.0)
    qty_received = Column(Float, default=0.0)
    qc_status = Column(String(20), default="PENDING")  # PENDING, PASSED, FAILED
    order = relationship("PurchaseOrder", back_populates="lines")
    item = relationship("Item")

class DemandLine(Base):
    """Hoja de demanda: necesidades de compra consolidadas."""
    __tablename__ = "demand_lines"
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    required_date = Column(Date)
    quantity_needed = Column(Float, default=0.0)
    source = Column(String(50))  # SALES_ORDER, MIN_STOCK, FORECAST
    action = Column(String(20), default="PENDING")  # PENDING, ORDERED, IGNORED
    item = relationship("Item")

class ShipmentRoute(Base):
    __tablename__ = "routes"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True)
    carrier = Column(String(60))  # DHL, UPS, SEUR, propio
    date = Column(Date)
    status = Column(String(20), default="PLANNED")  # PLANNED, IN_TRANSIT, DELIVERED
    stops = Column(Integer, default=0)

# ---------- Motor de BD (una BD por empresa) ----------

_engines = {}
_Session = {}

def get_engine(company_code: str = DEFAULT_COMPANY):
    if company_code not in _engines:
        _engines[company_code] = create_engine(
            f"sqlite:///{get_db_path(company_code)}",
            echo=False,
            future=True,
        )
        Base.metadata.create_all(_engines[company_code])
        _Session[company_code] = sessionmaker(bind=_engines[company_code], future=True)
    return _engines[company_code]

def get_session(company_code: str = DEFAULT_COMPANY):
    get_engine(company_code)
    return _Session[company_code]()