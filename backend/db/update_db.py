import duckdb
from pandas import DataFrame

def actualitzar_ventes(conn:duckdb.DuckDBPyConnection,ventas_df:DataFrame) -> bool:
    try:
        conn.execute("TRUNCATE ventas")
        conn.append("ventas",ventas_df)
        conn.commit()
        return True

    except Exception as e:
        print(f"Error añadiendo ventas a BDD: {e}")
        return False
    
def actualitzar_productes_procesar(conn:duckdb.DuckDBPyConnection, productos_procesar_df:DataFrame) -> bool:
    try:
        conn.execute("TRUNCATE productos_procesar")
        conn.append("productos_procesar",productos_procesar_df)
        conn.commit()
        return True

    except Exception as e: 
        print(f"Error añadiendo productos_procesar a BDD: {e}")
        quit()

def actualitzar_productos(conn:duckdb.DuckDBPyConnection, productos_df:DataFrame) -> bool:
    try:
        conn.execute("TRUNCATE productos")
        conn.append("productos",productos_df)
        conn.commit()
        return True

    except Exception as e: 
        print(f"Error añadiendo productos a BDD: {e}")
        quit()

def actualitzar_stocks(conn:duckdb.DuckDBPyConnection, stock_df:DataFrame) -> bool:
    try:
        conn.execute("TRUNCATE stock")
        conn.append("stock",stock_df)
        conn.commit()
        return True

    except Exception as e:
        print(f"Error añadiendo stock a BDD: {e}")
        return False
    
def actualitzar_stock_ventas_centro(conn:duckdb.DuckDBPyConnection, stock_ventas_centro_df:DataFrame) -> bool:
    try:
        conn.execute("TRUNCATE stock_ventas_centro")
        conn.append("stock_ventas_centro",stock_ventas_centro_df)
        conn.commit()
        return True

    except Exception as e:
        print(f"Error añadiendo stock_ventas_centro a BDD: {e}")
        return False
    
def actualitzar_stock_ventas_centro(conn:duckdb.DuckDBPyConnection, stock_ventas_centro_df:DataFrame) -> bool:
    try:
        conn.execute("TRUNCATE stock_ventas_centro")
        conn.append("stock_ventas_centro",stock_ventas_centro_df)
        conn.commit()
        return True

    except Exception as e:
        print(f"Error añadiendo stock_ventas_centro a BDD: {e}")
        return False
    
def actualitzar_moviments(conn:duckdb.DuckDBPyConnection, movimientos_df:DataFrame) -> bool:
    try:

        from datetime import datetime

        # OBTENER LA SEMANA QUE SE PROPUSO LOS MOVIMIENTOS PARA AÑADIRLA A HISTORICOS
        # !!!!   SI SE EJECUTA EL LUNES DEBE SER 'week' - 1   !!!!
        # !!!!   SI SE EJECUTA VIERNES SE DEJA COMO ESTA      !!!!
        fecha = datetime.now()
        semana = fecha.isocalendar().week

        # EJECUCION LUNES (demomento)
        semana -= 1

        # MOVER MOVIMIENTOS DE LA SEMANA ANTERIOR A HISTORICO
        conn.execute("""
            INSERT INTO movimientos_historico
            SELECT 
                ?, 
                EMISOR, 
                RECEPTOR, 
                NOMPRODUIT, 
                LIBCOLORIS, 
                CODEPRODUIT, 
                CODECOLORIS, 
                STOCK_ANTES, 
                APORTE, 
                STOCK_DESPUES, 
                COBERTURA_ANTES, 
                COBERTURA_DESPUES, 
                URL_FOTO
            FROM movimientos
        """, (semana,))

        # BORRAR DATOS DE 'movimientos'
        conn.execute("TRUNCATE movimientos")

        # AÑADIR LOS NUEVOS MOVIMIENTOS GENERADOS
        conn.append("movimientos",movimientos_df)

        conn.commit()
        
        return True

    except Exception as e:
        print(f"Error añadiendo stock_ventas_centro a BDD: {e}")
        return False
    