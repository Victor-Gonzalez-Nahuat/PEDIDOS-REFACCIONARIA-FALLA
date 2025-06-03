import flet as ft
import sqlite3
import pymysql
from pymysql.cursors import DictCursor

# ======== CONFIGURACIÓN LOCAL =========
DB_LOCAL = "g:/py/soadin/config/config_local.db"

from pymysql.cursors import DictCursor

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


def cargar_productos(grupo='', proveedor=''):
    config = obtener_config_mysql()
    if not config:
        return []
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        sql = """
            SELECT ma.id_codigo, ma.id_descripcion, ma.id_maximo, ma.id_minimo, ma.id_lista1, ma.id_provee,
                   ar.dt_sadoinicial, ar.dt_entradas, ar.dt_salidas,
                   ar.dt_ultimo_costo, ar.dt_ultima_venta, ar.dt_ultima_compra
            FROM INARMA01 ma
            LEFT JOIN INARAR01 ar ON ma.id_codigo = ar.dt_codigo
        """
        condiciones = []
        valores = []

        if grupo and grupo != 'ZZZZZZ':
            condiciones.append("LEFT(ma.id_grupo, 6) = %s")
            valores.append(grupo[:6])
        if proveedor and proveedor != 'ZZZZZZ':
            condiciones.append("LEFT(ma.id_provee, 6) = %s")
            valores.append(proveedor[:6])

        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " LIMIT 100"

        print("🔍 SQL Ejecutado:", sql)
        print("🔍 Valores:", valores)

        cursor.execute(sql, valores)
        datos = cursor.fetchall()
        conn.close()

        for d in datos:
            print(f"📦 Código: {d['id_codigo']}, Proveedor: {d['id_provee']}")
        return datos
    except Exception as e:
        print(f"❌ Error MySQL: {e}")
        return []

def cargar_grupos():
    config = obtener_config_mysql()
    if not config:
        return []
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT dt_grupoc, dt_nombreg FROM INARGR01 ORDER BY dt_nombreg")
        datos = cursor.fetchall()
        conn.close()
        lista = [("ZZZZZZ", "TODOS LOS GRUPOS")]
        lista += [(row['dt_grupoc'], row['dt_nombreg']) for row in datos]
        return lista
    except Exception as e:
        print(f"❌ Error al cargar grupos: {e}")
        return []

def cargar_proveedores():
    config = obtener_config_mysql()
    if not config:
        return []
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT dt_codigoc, dt_cliente FROM PRARMA01 ORDER BY dt_cliente")
        datos = cursor.fetchall()
        conn.close()
        return [(row['dt_codigoc'], row['dt_cliente']) for row in datos]
    except Exception as e:
        print(f"❌ Error al cargar proveedores: {e}")
        return []
def formatear_fecha_aammdd(valor):
    try:
        if valor and len(str(valor)) == 6:
            valor = str(valor)
            return f"{valor[4:6]}/{valor[2:4]}/{valor[0:2]}"
        else:
            return ""
    except:
        return ""
def main(page: ft.Page):
    page.title = "📦 Pedido de Productos (Flet Web)"
    page.scroll = True
    page.bgcolor = "#f0f4ff"
    page.padding = 10

    # Dropdowns
    grupos_data = cargar_grupos()
    proveedores_data = cargar_proveedores()

    dropdown_grupo = ft.Dropdown(
        label="Grupo",
        width=350,
        hint_text="Grupo",
        options=[ft.dropdown.Option(str(grp[0]), f"{grp[0]} - {grp[1] if grp[1] else ''}") for grp in grupos_data],
        on_change=lambda e: print(f"Grupo seleccionado: {e.control.value}"),
        value=str(grupos_data[0][0]) if grupos_data else None,
        text_style=ft.TextStyle(size=11)
    )

    dropdown_prov = ft.Dropdown(
        label="Proveedor",
        width=350,
        hint_text="Proveedor",
        options=[ft.dropdown.Option(str(prov[0]), f"{prov[0]} - {prov[1] if prov[1] else ''}") for prov in proveedores_data],
        on_change=lambda e: print(f"Proveedor seleccionado: {e.control.value}"),
        value=str(proveedores_data[0][0]) if proveedores_data else None,
        text_style=ft.TextStyle(size=11)
    )
    chk_pedir = ft.Checkbox(value=False)
    chk_maxmin = ft.Checkbox(value=False)
    filtros = ft.Row([
        dropdown_grupo,
        dropdown_prov,
        ft.Row([
            chk_pedir,
            ft.Text("Quitar por Pedir = 0", size=12, weight="bold")
        ], vertical_alignment="center"),
        ft.Row([
            chk_maxmin,
            ft.Text("Ocultar Max=0 Min=0 Exi=0", size=12, weight="bold")
        ], vertical_alignment="center"),
    ], spacing=15)

    encabezado = ft.Row([
        ft.Text("Código", size=10, weight="bold", width=100),
        ft.Text("Descripción", size=10, weight="bold", width=200),
        ft.Text("Existencia", size=10, weight="bold", width=70),
        ft.Text("Máximo", size=10, weight="bold", width=70),  # ✅ NUEVO
        ft.Text("Mínimo", size=10, weight="bold", width=70),  # ✅ NUEVO
        ft.Text("Por Pedir", size=10, weight="bold", width=70),
        ft.Text("Costo", size=10, weight="bold", width=70),
        ft.Text("Lista1", size=10, weight="bold", width=70),
        ft.Text("% Utilidad", size=10, weight="bold", width=50),
        ft.Text("Últ. Venta", size=10, weight="bold", width=70),
        ft.Text("Últ. Compra", size=10, weight="bold", width=70),
    ], spacing=10)

    filas_con_scroll = ft.Column(scroll="always", height=450, spacing=5)

    def actualizar_tabla(e=None):
        grupo_sel = dropdown_grupo.value or ''
        proveedor_sel = dropdown_prov.value or ''
        productos = cargar_productos(grupo_sel, proveedor_sel)
        filas_con_scroll.controls.clear()
        for row in productos:
            existencia = (row.get("dt_sadoinicial") or 0) + (row.get("dt_entradas") or 0) - (row.get("dt_salidas") or 0)
            costo = row.get("dt_ultimo_costo") or 0
            lista = row.get("id_lista1") or 0
            utilidad = ((lista - costo) / costo * 100) if costo else 0
            maximo = row.get("id_maximo") or 0  # ✅ NUEVO
            minimo = row.get("id_minimo") or 0  # ✅ NUEVO
            if existencia <= minimo:
                pedido = maximo - existencia
            else:
                pedido = 0
            filas_con_scroll.controls.append(
                ft.Row([
                    ft.Text(row.get("id_codigo", ""), size=10, width=100),
                    ft.Text(row.get("id_descripcion", ""), size=10, width=200),
                    ft.Text(f"{existencia:,.2f}", size=10, width=70),
                    ft.Text(f"{maximo:,.0f}", size=10, width=70),  # ✅ NUEVO
                    ft.Text(f"{minimo:,.0f}", size=10, width=70),
                    ft.Text(f"{pedido:,.0f}", size=10, width=70),
                    ft.Text(f"${costo:,.2f}", size=10, width=70),
                    ft.Text(f"${lista:,.2f}", size=10, width=70),
                    ft.Text(f"{utilidad:,.2f}%", size=10, width=50),
                    ft.Text(formatear_fecha_aammdd(row.get("dt_ultima_venta")), size=10, width=70),  # ✅
                    ft.Text(formatear_fecha_aammdd(row.get("dt_ultima_compra")), size=10, width=70),  # ✅
                ], spacing=10)
            )
        page.update()

    botones = ft.Row([
        ft.ElevatedButton("🔄 Cargar", on_click=actualizar_tabla, icon=ft.Icons.REFRESH),
        ft.ElevatedButton("📤 Exportar Excel"),
        ft.ElevatedButton("📄 Ver PDF"),
        ft.ElevatedButton("📊 Estadísticas"),
        ft.ElevatedButton("📦 Equivalentes"),
    ], spacing=10)

    page.add(
        ft.Text("🔍 Consulta de Productos (Web)", size=22, weight="bold"),
        filtros,
        ft.Divider(),
        botones,
        ft.Divider(),
        encabezado,
        filas_con_scroll
    )

ft.app(target=main)
