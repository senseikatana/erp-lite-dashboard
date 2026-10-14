# 🏢 ERP-Lite: Dashboard estilo Dynamics NAV con Python + Streamlit

Vamos a construir una base sólida, extensible y multiempresa de un ERP ligero inspirado en Dynamics NAV. Empezaremos con un MVP funcional que puedas ejecutar hoy mismo y luego iremos añadiendo módulos.

## Project Structure:

```
erp_lite/
├── app.py                  # Punto de entrada principal
├── database.py             # Configuración SQLite + modelos
├── seed_data.py            # Datos de ejemplo
├── i18n.py                 # Traducciones (ES/CA/EN)
├── config.py               # Configuración multiempresa
├── modules/
│   ├── __init__.py
│   ├── dashboard.py        # KPIs y vista general
│   ├── ventas.py           # Pedidos de venta
│   ├── compras.py          # Pedidos de compra + recepciones
│   ├── almacen.py          # Stock y picking
│   ├── demanda.py          # Hoja de demanda
│   └── rutas.py            # Transporte y rutas
└── requirements.txt
```


## requirements.txt

```txt

streamlit>=1.32.0
pandas>=2.0.0
plotly>=5.18.0
sqlalchemy>=2.0.0

```

