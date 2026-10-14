# config.py
import os
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class CompanyConfig:
    """Configuración por empresa. Cada empresa tiene su propia BD."""
    name: str
    currency: str = "EUR"
    locale: str = "es_ES"
    logo_path: str = ""
    modules_enabled: list = field(default_factory=lambda: [
        "dashboard", "ventas", "compras", "almacen", "demanda", "rutas"
    ])
    quality_check_required: bool = True  # Coordinación con Calidad
    default_language: str = "es"

# Directorio de datos (ajústalo a tu entorno)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Empresas registradas (multiempresa desde el día 1)
COMPANIES: Dict[str, CompanyConfig] = {
    "DEMO_SL": CompanyConfig(name="Demo Logística S.L."),
    "ACME_SA": CompanyConfig(name="Acme Manufacturing S.A.", currency="EUR"),
}

# Empresa activa por defecto
DEFAULT_COMPANY = "DEMO_SL"

def get_db_path(company_code: str) -> str:
    return os.path.join(DATA_DIR, f"{company_code}.db")