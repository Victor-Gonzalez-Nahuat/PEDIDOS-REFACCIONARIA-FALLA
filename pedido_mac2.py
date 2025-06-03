import flet as ft
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime
import pandas as pd # Kept as it was in original, though not explicitly used in the provided logic.

# Define the path to your local configuration database
DB_LOCAL = "g:/py/soadin/config/config_local.db"

# === CONFIG DB ===
def obtener_config_mysql():
    try:
        return {
            "host": "tramway.proxy.rlwy.net",
            "port": 37742,
            "user": "root",
            "password": "sOcbAOvZwCWyJZmgLKYmugQgFurELgxT",
            "database": "railway",
            "connect_timeout": 30,
            "cursorclass": DictCursor
        }
    except Exception as e:
        print(f"❌ Error al obtener configuración MySQL: {e}")
        return None


# === FORMATO ===
def formatear_fecha_aammdd(valor):
    """
    Formats a 6-digit date string (YYMMDD) to DD/MM/YY.
    Returns an empty string if the value is invalid.
    """
    try:
        if valor and len(str(valor)) == 6:
            valor = str(valor)
            return f"{valor[4:6]}/{valor[2:4]}/{valor[0:2]}"
        return ""
    except Exception as e:
        print(f"❌ Error al formatear fecha {valor}: {e}")
        return ""

def dias_sin_venta(valor):
    """
    Calculates the number of days since the last sale, given a date in YYMMDD format.
    Returns an empty string if the value is invalid or an error occurs.
    """
    try:
        if valor and len(str(valor)) == 6:
            fecha_venta = datetime.strptime(str(valor), "%y%m%d")
            return (datetime.now() - fecha_venta).days
        return ""
    except Exception as e:
        print(f"❌ Error al calcular días sin venta para {valor}: {e}")
        return ""

# === DATOS ===
def cargar_grupos():
    """
    Loads product groups from the MySQL database.
    Returns a list of tuples (code, name) or an empty list on error.
    Includes a "TODOS LOS GRUPOS" option.
    """
    config = obtener_config_mysql()
    if not config:
        return []
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT dt_grupoc, dt_nombreg FROM INARGR01 ORDER BY dt_nombreg")
        datos = cursor.fetchall()
        conn.close()
        print(f"✅ Grupos cargados: {len(datos)} elementos.")
        return [("ZZZZZZ", "TODOS LOS GRUPOS")] + [(r['dt_grupoc'], r['dt_nombreg']) for r in datos]
    except Exception as e:
        print(f"❌ Error al cargar grupos desde MySQL: {e}")
        return []

def cargar_proveedores():
    """
    Loads suppliers from the MySQL database.
    Returns a list of tuples (code, name) or an empty list on error.
    """
    config = obtener_config_mysql()
    if not config:
        return []
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT dt_codigoc, dt_cliente FROM PRARMA01 ORDER BY dt_cliente")
        datos = cursor.fetchall()
        conn.close()
        print(f"✅ Proveedores cargados: {len(datos)} elementos.")
        return [(r['dt_codigoc'], r['dt_cliente']) for r in datos]
    except Exception as e:
        print(f"❌ Error al cargar proveedores desde MySQL: {e}")
        return []

def cargar_productos(grupo='', proveedor=''):
    """
    Loads product data from MySQL, filtering by group and supplier.
    Returns a list of dictionaries (product data) or an empty list on error.
    Limits results to 100.
    """
    config = obtener_config_mysql()
    if not config:
        return []
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        sql = """
            SELECT
                ma.id_codigo, ma.id_descripcion, ma.id_maximo, ma.id_minimo,
                ma.id_lista1, ma.id_provee,
                ar.dt_sadoinicial, ar.dt_entradas, ar.dt_salidas,
                ar.dt_ultimo_costo, ar.dt_ultima_venta, ar.dt_ultima_compra,
                (SELECT COUNT(*) FROM INAREQ01 eq WHERE eq.codigo_principal = ma.id_codigo) AS equiv
            FROM INARMA01 ma
            LEFT JOIN INARAR01 ar ON ma.id_codigo = ar.dt_codigo
        """
        condiciones, valores = [], []
        if grupo and grupo != 'ZZZZZZ':
            condiciones.append("LEFT(ma.id_grupo, 6) = %s")
            valores.append(grupo[:6])
        if proveedor and proveedor != 'ZZZZZZ':
            condiciones.append("LEFT(ma.id_provee, 6) = %s")
            valores.append(proveedor[:6])
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " LIMIT 100" # Limiting to 100 as per original code
        cursor.execute(sql, valores)
        datos = cursor.fetchall()
        conn.close()
        print(f"✅ Productos cargados: {len(datos)} elementos.")
        return datos
    except Exception as e:
        print(f"❌ Error al cargar productos desde MySQL: {e}")
        return []

# === MAIN FLET APPLICATION ===
def main(page: ft.Page):
    page.title = "📦 Pedido de Productos"
    page.scroll = True
    page.bgcolor = "#f0f4ff"
    page.padding = 10

    # Stores the currently selected product's code
    producto_sel = {"codigo": None}

    # Load initial data for dropdowns
    grupos = cargar_grupos()
    proveedores = cargar_proveedores()

    # Prepare dropdown options, ensuring they are not empty even if data loading fails
    dropdown_grupo_options = [ft.dropdown.Option(str(c), f"{c} - {n}") for c, n in grupos] if grupos else [ft.dropdown.Option("N/A", "No hay grupos")]
    dropdown_prov_options = [ft.dropdown.Option(str(c), f"{c} - {n}") for c, n in proveedores] if proveedores else [ft.dropdown.Option("N/A", "No hay proveedores")]
    dialogo = ft.AlertDialog(modal=True)
    # page.dialog is assigned dynamically in ver_equivalentes and set to None in cerrar_dialogo

    dropdown_grupo = ft.Dropdown(
        label="Grupo",
        width=400,
        options=dropdown_grupo_options,
        value=grupos[0][0] if grupos else "N/A",  # Set initial value if groups exist
        on_change=lambda e: actualizar_tabla(),  # Add on_change to filter
        # === APLICAR ESTILO DE FUENTE AL LABEL Y AL TEXTO SELECCIONADO ===
        label_style=ft.TextStyle(font_family="Roboto", size=11, weight=ft.FontWeight.BOLD),
        text_style=ft.TextStyle(font_family="Open Sans", size=11, color=ft.Colors.BLUE_700)
        # Corrected color constant: ft.Colors
    )

    dropdown_prov = ft.Dropdown(
        label="Proveedor",
        width=400,
        options=dropdown_prov_options,
        value=proveedores[0][0] if proveedores else "N/A",  # Set initial value if suppliers exist
        on_change=lambda e: actualizar_tabla(),  # Add on_change to filter
        # === APLICAR ESTILO DE FUENTE AL LABEL Y AL TEXTO SELECCIONADO ===
        label_style=ft.TextStyle(font_family="Roboto", size=11, weight=ft.FontWeight.BOLD),
        text_style=ft.TextStyle(font_family="Open Sans", size=11, color=ft.Colors.BLUE_700)
        # Corrected color constant: ft.Colors
    )
    filas_con_scroll = ft.Column(scroll="always", spacing=5)
    texto_total = ft.Text("Total por pedir: 0", size=14, weight="bold", color="blue")
    productos_actuales = [] # This will hold the list of products currently displayed

    def calcular_total_pedido(products_list):
        """Calculates the total quantity to order for all products in the list."""
        total = 0
        for p in products_list:
            existencia = (p.get("dt_sadoinicial") or 0) + (p.get("dt_entradas") or 0) - (p.get("dt_salidas") or 0)
            maximo = p.get("id_maximo") or 0
            minimo = p.get("id_minimo") or 0
            pedido = maximo - existencia if existencia <= minimo else 0
            total += pedido
        return total

    def generar_row(row_data, seleccionado=False):
        """
        Generates a Flet Row widget for a product, with a GestureDetector for selection.
        Returns the Flet widget and the 'por pedir' quantity for that row.
        """
        existencia = (row_data.get("dt_sadoinicial") or 0) + \
                     (row_data.get("dt_entradas") or 0) - \
                     (row_data.get("dt_salidas") or 0)
        costo = row_data.get("dt_ultimo_costo") or 0
        lista = row_data.get("id_lista1") or 0
        utilidad = ((lista - costo) / costo * 100) if costo else 0
        maximo = row_data.get("id_maximo") or 0
        minimo = row_data.get("id_minimo") or 0
        pedido = maximo - existencia if existencia <= minimo else 0
        dias = dias_sin_venta(row_data.get("dt_ultima_venta"))
        equiv = row_data.get("equiv", 0)

        fila_content = ft.Row([
            ft.Text(row_data.get("id_codigo", ""), size=10, width=100),
            ft.Text(row_data.get("id_descripcion", ""), size=10, width=200),
            ft.Text(f"{existencia:,.2f}", size=10, width=70),
            ft.Text(f"{equiv:,.0f}", size=10, width=50),
            ft.Text(f"{maximo:,.0f}", size=10, width=70),
            ft.Text(f"{minimo:,.0f}", size=10, width=70),
            ft.Text(f"{pedido:,.0f}", size=10, width=70),
            ft.Text(f"${costo:,.2f}", size=10, width=70),
            ft.Text(f"${lista:,.2f}", size=10, width=70),
            ft.Text(f"{utilidad:,.2f}%", size=10, width=50),
            ft.Text(formatear_fecha_aammdd(row_data.get("dt_ultima_venta")), size=10, width=70),
            ft.Text(str(dias), size=10, width=60, color="red" if isinstance(dias, int) and dias > 90 else None),
            ft.Text(formatear_fecha_aammdd(row_data.get("dt_ultima_compra")), size=10, width=70),
        ], spacing=5)

        return ft.GestureDetector(
            content=ft.Container(content=fila_content, bgcolor="#cce5ff" if seleccionado else None, padding=5),
            on_tap=lambda e: seleccionar_fila(row_data) # Pass the full row_data
        ), pedido

    def seleccionar_fila(row):
        """
        Handles row selection, updates the selected product, and re-renders the table
        to highlight the selected row.
        """
        print(f"🔄 Fila seleccionada: {row.get('id_codigo')}")
        producto_sel["codigo"] = row.get("id_codigo")
        filas_con_scroll.controls.clear()
        for r in productos_actuales: # Iterate through the actual data list
            seleccionado = r['id_codigo'] == producto_sel["codigo"]
            widget, _ = generar_row(r, seleccionado) # Recalculate 'pedido' but we don't need it here
            filas_con_scroll.controls.append(widget)
        # Recalculate total for all products after selection
        texto_total.value = f"Total por pedir: {calcular_total_pedido(productos_actuales):,.0f}"
        page.update()

    def actualizar_tabla(e=None):
        """
        Loads products based on current dropdown selections and updates the UI table.
        """
        print(f"🔄 Actualizando tabla para Grupo: {dropdown_grupo.value}, Proveedor: {dropdown_prov.value}")
        nonlocal productos_actuales
        productos_actuales = cargar_productos(dropdown_grupo.value, dropdown_prov.value)
        filas_con_scroll.controls.clear()
        for row in productos_actuales:
            widget, _ = generar_row(row) # No need for 'pedido' here, it's calculated in total
            filas_con_scroll.controls.append(widget)
        texto_total.value = f"Total por pedir: {calcular_total_pedido(productos_actuales):,.0f}"
        page.update()
        print("✅ Tabla actualizada.")

    def cerrar_dialogo(e=None):
        """
        Cierra el diálogo de equivalentes y re-renderiza la tabla completa con el producto seleccionado.
        """
        if dialogo.open:
            print("🧹 Cerrando diálogo de equivalentes...")
            dialogo.open = False
            page.update()

        # Re-renderizar tabla completa con el producto seleccionado resaltado
        filas_con_scroll.controls.clear()
        for r in productos_actuales:
            seleccionado = r['id_codigo'] == producto_sel["codigo"]
            widget, _ = generar_row(r, seleccionado)
            filas_con_scroll.controls.append(widget)

        texto_total.value = f"Total por pedir: {calcular_total_pedido(productos_actuales):,.0f}"
        page.update()

    global etiquetas_completas
    anio_actual = datetime.now().year
    meses = [f"{mes:02d}" for mes in range(1, 13)]
    etiquetas_2024 = [f"24-{mes}" for mes in meses]
    etiquetas_actual = [f"{str(anio_actual)[2:]}-{mes}" for mes in meses]
    etiquetas_completas = etiquetas_2024 + etiquetas_actual
    def ver_compras(e=None):
        config = obtener_config_mysql()
        if not config:
            page.snack_bar = ft.SnackBar(ft.Text("❌ No se pudo conectar a la base de datos"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        try:
            conn = pymysql.connect(**config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT mv_fechat, mv_cantidad
                FROM INARMV01
                WHERE mv_concepto IN ('0001', '0021') AND mv_tipo = 'E'
                  AND LEFT(mv_fechat, 2) IN ('24', '25')  -- ejercicio anterior y actual
            """)
            datos = cursor.fetchall()
            conn.close()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error al consultar compras: {ex}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        # Agrupar por año-mes
        resumen = {et: 0 for et in etiquetas_completas}
        for fila in datos:
            fecha = str(fila['mv_fechat'])  # formato aammdd
            if len(fecha) == 6:
                clave = f"{fecha[:2]}-{fecha[2:4]}"
                if clave in resumen:
                    resumen[clave] += fila['mv_cantidad'] or 0

        # Mostrar en pantalla
        contenido = [ft.Text("Resumen Compras por Mes", size=16, weight="bold")]
        for k in etiquetas_completas:
            contenido.append(ft.Text(f"{k}: {resumen[k]:,.2f}"))

        dialogo.title = ft.Text("🛒 Compras por Mes")
        dialogo.content = ft.Container(content=ft.Column(contenido, scroll="auto"), width=400)
        dialogo.actions = [ft.TextButton("Cerrar", on_click=cerrar_dialogo)]
        if dialogo not in page.overlay:
            page.overlay.append(dialogo)
        dialogo.open = True
        page.update()

    anio_actual = datetime.now().year
    meses = [f"{mes:02d}" for mes in range(1, 13)]
    etiquetas_2024 = [f"24-{mes}" for mes in meses]
    etiquetas_actual = [f"{str(anio_actual)[2:]}-{mes}" for mes in meses]
    etiquetas_completas = etiquetas_2024 + etiquetas_actual
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import io
    import base64

    def ver_ventas(e=None):
        import matplotlib.pyplot as plt
        import io, base64

        codigo = producto_sel.get("codigo")
        if not codigo:
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ Selecciona un producto primero."), bgcolor="orange")
            page.snack_bar.open = True
            page.update()
            return

        config = obtener_config_mysql()
        if not config:
            page.snack_bar = ft.SnackBar(ft.Text("❌ No se pudo conectar a la base de datos"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        try:
            conn = pymysql.connect(**config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT vm_fechat, vm_cantidad
                FROM VEARMO01
                WHERE LEFT(vm_folio, 1) IN ('R', 'F', 'N')
                  AND vm_bandera = 0
                  AND vm_codigo = %s
                  AND LEFT(vm_fechat, 2) IN ('24', '25')
            """, (codigo,))
            datos = cursor.fetchall()
            conn.close()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error al consultar ventas: {ex}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        resumen = {
            "Ene": [0, 0], "Feb": [0, 0], "Mar": [0, 0], "Abr": [0, 0],
            "May": [0, 0], "Jun": [0, 0], "Jul": [0, 0], "Ago": [0, 0],
            "Sep": [0, 0], "Oct": [0, 0], "Nov": [0, 0], "Dic": [0, 0],
        }
        nombres_meses = list(resumen.keys())

        for fila in datos:
            fecha = str(fila["vm_fechat"])
            if len(fecha) == 6:
                anio = fecha[:2]
                mes = int(fecha[2:4])
                idx = 0 if anio == "24" else 1
                mes_nombre = nombres_meses[mes - 1]
                resumen[mes_nombre][idx] += fila["vm_cantidad"] or 0

        total_2024 = sum([resumen[m][0] for m in nombres_meses])
        total_2025 = sum([resumen[m][1] for m in nombres_meses])
        diferencia = total_2025 - total_2024
        porcentaje = (diferencia / total_2024 * 100) if total_2024 else 0

        filas = [
            ft.Row([
                ft.Text("Mes", width=60, weight="bold"),
                ft.Text("2024", width=70, weight="bold"),
                ft.Text("2025", width=70, weight="bold"),
                ft.Text("DIF", width=70, weight="bold"),
                ft.Text("%", width=60, weight="bold"),
            ], spacing=8)
        ]

        unidades_2024 = []
        unidades_2025 = []

        for mes in nombres_meses:
            val_2024, val_2025 = resumen[mes]
            dif = val_2025 - val_2024
            porc = (dif / val_2024 * 100) if val_2024 else 0
            color = "green" if dif > 0 else "red"

            unidades_2024.append(val_2024)
            unidades_2025.append(val_2025)

            filas.append(
                ft.Row([
                    ft.Text(mes, width=60),
                    ft.Text(f"{val_2024:,.0f}", width=70),
                    ft.Text(f"{val_2025:,.0f}", width=70),
                    ft.Text(f"{dif:+,}", width=70, color=color),
                    ft.Text(f"{porc:+.1f}%", width=60, color=color),
                ], spacing=8)
            )

        filas.append(ft.Divider())
        filas.append(
            ft.Row([
                ft.Text("TOTAL", width=60, weight="bold"),
                ft.Text(f"{total_2024:,.0f}", width=70, weight="bold"),
                ft.Text(f"{total_2025:,.0f}", width=70, weight="bold"),
                ft.Text(f"{diferencia:+,}", width=70, weight="bold", color="green" if diferencia > 0 else "red"),
                ft.Text(f"{porcentaje:+.1f}%", width=60, weight="bold", color="green" if porcentaje > 0 else "red"),
            ], spacing=8)
        )

        # === GRÁFICA ===
        plt.figure(figsize=(6, 2.5))
        plt.plot(nombres_meses, unidades_2024, label="2024", marker="o")
        plt.plot(nombres_meses, unidades_2025, label="2025", marker="o")
        plt.title(f"Ventas {codigo} (Unidades por mes)")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        grafica = ft.Image(src_base64=img_base64, width=580, height=180)

        # === DIÁLOGO ===
        dialogo.title = ft.Text(f"📦 Ventas por Mes: {codigo}", weight="bold")
        dialogo.content = ft.Container(
            content=ft.Column(filas + [ft.Divider(), grafica], scroll="auto"),
            width=600
        )
        dialogo.actions = [ft.TextButton("Cerrar", on_click=cerrar_dialogo)]
        if dialogo not in page.overlay:
            page.overlay.append(dialogo)
        dialogo.open = True
        page.update()

    def ver_equivalentes(e=None):
        """
        Opens a dialog displaying equivalent products for the selected main product.
        """
        codigo = producto_sel.get("codigo")
        print(f"Attempting to view equivalents for: {codigo}")

        if not codigo:
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ Selecciona un producto primero para ver equivalentes."), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            print("❌ No hay producto seleccionado.")
            return

        config = obtener_config_mysql()
        if not config:
            page.snack_bar = ft.SnackBar(ft.Text("❌ Error: No se pudo obtener la configuración de la base de datos."), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            print("❌ No se pudo obtener la configuración de MySQL.")
            return

        try:
            conn = pymysql.connect(**config)
            cursor = conn.cursor()
            query = """
                SELECT
                    eq.codigo_equivalente AS codigo,
                    ma.id_descripcion AS descripcion,
                    IFNULL(ar.dt_sadoinicial, 0) + IFNULL(ar.dt_entradas, 0) - IFNULL(ar.dt_salidas, 0) AS existencia,
                    IFNULL(ar.dt_ultimo_costo, 0) AS costo,
                    IFNULL(ma.id_lista1, 0) AS lista1,
                    ar.dt_ultima_venta AS uventa,
                    ar.dt_ultima_compra AS ucompra
                FROM INAREQ01 eq
                LEFT JOIN INARMA01 ma ON eq.codigo_equivalente = ma.id_codigo
                LEFT JOIN INARAR01 ar ON eq.codigo_equivalente = ar.dt_codigo
                WHERE eq.codigo_principal = %s
            """
            cursor.execute(query, (codigo,))
            datos = cursor.fetchall()
            conn.close()
            print(f"✅ Consulta de equivalentes para {codigo} ejecutada. Resultados: {len(datos)}")
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error al consultar equivalentes: {ex}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            print(f"❌ Excepción al consultar equivalentes: {ex}")
            return

        if not datos:
            page.snack_bar = ft.SnackBar(ft.Text(f"ℹ️ No se encontraron equivalentes para el producto {codigo}."), bgcolor="orange")
            page.snack_bar.open = True
            page.update()
            print(f"⚠️ No hay equivalentes para {codigo}.")
            return

        # Build the header row for the equivalents dialog
        encabezado = ft.Row([
            ft.Text("Código", width=100, size=11, weight="bold"),
            ft.Text("Descripción", width=200, size=11, weight="bold"),
            ft.Text("Exist.", width=60, size=11, weight="bold"),
            ft.Text("Costo", width=70, size=11, weight="bold"),
            ft.Text("Lista1", width=70, size=11, weight="bold"),
            ft.Text("Ult. Venta", width=80, size=11, weight="bold"),
            ft.Text("Días S/V", width=60, size=11, weight="bold"),
            ft.Text("Ult. Compra", width=80, size=11, weight="bold"),
        ], spacing=5)

        # Build the data rows for the equivalents dialog
        filas = []
        for row in datos:
            dias = dias_sin_venta(row["uventa"])
            filas.append(ft.Row([
                ft.Text(row["codigo"], width=100, size=10),
                ft.Text(row["descripcion"] or "", width=200, size=10),
                ft.Text(f"{row['existencia']:,.2f}", width=60, size=10),
                ft.Text(f"${row['costo']:,.2f}", width=70, size=10),
                ft.Text(f"${row['lista1']:,.2f}", width=70, size=10),
                ft.Text(formatear_fecha_aammdd(row["uventa"]), width=80, size=10),
                ft.Text(str(dias), width=60, size=10, color="red" if isinstance(dias, int) and dias > 90 else None),
                ft.Text(formatear_fecha_aammdd(row["ucompra"]), width=80, size=10),
            ], spacing=5))

        # Set dialog content and open it
        dialogo.title = ft.Text(f"Equivalentes de {codigo}", weight="bold")
        dialogo.content = ft.Container(
            content=ft.Column([encabezado] + filas, scroll="auto", height=400),
            width=850
        )
        dialogo.actions = [ft.TextButton("Cerrar", on_click=cerrar_dialogo)] # Use the defined function

        # Add the dialog to the page's overlay and then open it
        if dialogo not in page.overlay: # Prevent adding multiple times
            page.overlay.append(dialogo)
        dialogo.open = True
        page.update() # Important: update the page to show the dialog
        print("✅ Diálogo de equivalentes abierto.")

    # Buttons for actions
    botones = ft.Row([
        ft.ElevatedButton("🔄 Cargar Productos", on_click=actualizar_tabla),
        ft.ElevatedButton("📦 Ver Equivalentes", on_click=ver_equivalentes),
        ft.ElevatedButton("🛒 Ver Compras", on_click=ver_compras),
        ft.ElevatedButton("💵 Ver Ventas", on_click=ver_ventas),
    ])

    # Header for the main product table
    encabezado_productos = ft.Row([
        ft.Text("Código", size=10, weight="bold", width=100),
        ft.Text("Descripción", size=10, weight="bold", width=200),
        ft.Text("Existencia", size=10, weight="bold", width=70),
        ft.Text("Equiv.", size=10, weight="bold", width=50),
        ft.Text("Máximo", size=10, weight="bold", width=70),
        ft.Text("Mínimo", size=10, weight="bold", width=70),
        ft.Text("Por Pedir", size=10, weight="bold", width=70),
        ft.Text("Costo", size=10, weight="bold", width=70),
        ft.Text("Lista1", size=10, weight="bold", width=70),
        ft.Text("% Utilidad", size=10, weight="bold", width=50),
        ft.Text("Últ. Venta", size=10, weight="bold", width=70),
        ft.Text("Días S/V", size=10, weight="bold", width=60),
        ft.Text("Últ. Compra", size=10, weight="bold", width=70),
    ], spacing=5)

    # Add all controls to the page
    page.add(
        ft.Text("🔍 Pedido Web (ERP Meteorito)", size=22, weight="bold"),
        ft.Row([dropdown_grupo, dropdown_prov], spacing=15),
        ft.Divider(),
        botones,
        ft.Divider(),
        encabezado_productos,
        ft.Container(content=filas_con_scroll, height=450, border=ft.border.all(1, "#999999"), padding=5, bgcolor="#ffffff"),
        texto_total
    )

    # Initial data load when the page is ready
    page.on_ready = actualizar_tabla

# Run the Flet application
ft.app(target=main)
