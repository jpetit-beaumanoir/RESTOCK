import pandas as pd
import duckdb
from duckdb import DuckDBPyConnection
from pathlib import Path
from datetime import date, timedelta
import os
import glob
import shutil
from django.http import JsonResponse

from backend.db.Storeland_BDD.get_storeland_data import run_query_to_df
from backend.db.update_db import actualitzar_ventes, actualitzar_productes_procesar, actualitzar_stocks, actualitzar_stock_ventas_centro, actualitzar_productos, actualitzar_moviments

#-------------------------------------------------------
#   2. OBTENIR LES VENTES ENTRE DUES DATES
#-------------------------------------------------------
def obtenir_ventes(
        conn:DuckDBPyConnection,
        fecha_inicial_str:str,
        fecha_hoy_str:str,
        centres:list = [],
        eans_procesar:list = []
    ) -> pd.DataFrame:

    def format_hora(h):
        if pd.isna(h):
            return ""
        h = int(h)
        horas = h // 100
        minutos = h % 100
        return f"{horas:02d}:{minutos:02d}"

    # --------------------------------------------------
    # 1. CONFIGURACION
    # --------------------------------------------------
    paths_a_buscar = [
        Path("C:/Users/jpetit/O365/Groupe Beaumanoir/Datos Ibérica-Morgan - Morgan/Ediwin/SLSRPT_csv"), 
        Path("C:/Users/jpetit/O365/Groupe Beaumanoir/Datos Ibérica-Morgan - Morgan/Ediwin/SLSRPT_csv 2024")
    ]

    # Minimo de columnas requeridas para poder realizar la transformacion
    columnas_requeridas = {"FECHA", "HORA", "TIENDA", "IMPORTE"} 

    fecha_inicial_str = ''.join(fecha_inicial_str.split("-"))
    fecha_hoy_str = ''.join(fecha_hoy_str.split("-"))

    # --------------------------------------------------
    # 2. DISCOVERY
    # --------------------------------------------------
    csvs = []
    for carpeta in paths_a_buscar:

        if not carpeta.exists():
            print(f"\tLa carpeta {carpeta} no existe. Saltando...")
            continue

        archivos = []
        
        for f in carpeta.glob(f"*.csv"):
            nombre_sin_extension = f.stem

            if nombre_sin_extension.isdigit():
                if fecha_inicial_str < nombre_sin_extension[:8] <= fecha_hoy_str:
                    archivos.append(f)

        for f in archivos:

            try:
                # 1. FILTRAR PER DATA
                muestra = pd.read_csv(f, sep=";", nrows=0)

                # 2. COMPROABR QUE ESTAN LES COLUMNES CORRECTES
                if columnas_requeridas.issubset(muestra.columns):
                    csvs.append(f)                

            except (ValueError, pd.errors.EmptyDataError) as e:
                # todo: MOSTRAR MISSATGE O ALERTA QUE S'HA SALTAT UN ARXIU PER X MOTIU
                continue

    if not csvs:
        return False

    # --------------------------------------------------
    # 4. PROCESSING
    # --------------------------------------------------
    dfs = []

    for csv in csvs:

        # DETERMINAR PAIS EN FUNCIO DE L'ULTIM DIGIT (1 - PT, 2 - ES)
        pais = "ES" if csv.name.endswith("1.csv") else "PT" if csv.name.endswith("2.csv") else None
        
        try:
            df = pd.read_csv(csv, sep=";")

            df['pais'] = pais
            dfs.append(df)

        except Exception as e:
           # todo: MOSTRAR MISSATGE O ALERTA QUE S'HA SALTAT UN ARXIU PER X MOTIU
           pass

    merged_csv_actualizado:pd.DataFrame = pd.concat(dfs, ignore_index=True)
    merged_csv_actualizado.columns = merged_csv_actualizado.columns.str.lower()

    # --------------------------------------------------
    # 5. HORAS
    # --------------------------------------------------
    merged_csv_actualizado["HORA"] = merged_csv_actualizado["HORA"].apply(format_hora)
    merged_csv_actualizado["HORA_ORIG"] = merged_csv_actualizado["HORA_ORIG"].apply(format_hora)

    merged_csv_actualizado[["HORA", "MINUTO"]] = merged_csv_actualizado["HORA"].str.split(":", expand=True)
    merged_csv_actualizado[["HORA_ORIG", "MINUTO_ORIG"]] = merged_csv_actualizado["HORA_ORIG"].str.split(":", expand=True)

    # --------------------------------------------------
    # 6. FECHAS
    # --------------------------------------------------

    # Date Parsing
    merged_csv_actualizado["FECHA"] = pd.to_datetime(merged_csv_actualizado["FECHA"], format="%d/%m/%Y", errors="coerce")
    merged_csv_actualizado["FECHA_ORIG"] = pd.to_datetime(merged_csv_actualizado["FECHA_ORIG"], format="%d/%m/%Y", errors="coerce")

    # Create FECHA_HORA
    merged_csv_actualizado["FECHA_HORA"] = pd.to_datetime(
        merged_csv_actualizado["FECHA"].dt.strftime("%d/%m/%Y") + " " + 
        merged_csv_actualizado["HORA"] + ":" + 
        merged_csv_actualizado["MINUTO"].fillna("00"),
        format="%d/%m/%Y %H:%M", 
        errors="coerce"
    )

    merged_csv_actualizado["FECHA_HORA_ORIG"] = pd.to_datetime(
        merged_csv_actualizado["FECHA_ORIG"].dt.strftime("%d/%m/%Y") + " " + 
        merged_csv_actualizado["HORA_ORIG"] + ":" + 
        merged_csv_actualizado["MINUTO"].fillna("00"),
        format="%d/%m/%Y %H:%M", 
        errors="coerce"
    )

    # CONVERTIR A int64 o NULL 
    for col in ["HORA", "MINUTO", "HORA_ORIG", "MINUTO_ORIG"]:
        merged_csv_actualizado[col] = (
            merged_csv_actualizado[col]
            .replace("", None)
            .astype("Int64")
        )

    # --------------------------------------------------
    # 7. ENRIQUECIMIENTO
    # --------------------------------------------------
    def normalize_tienda(x):
        import re
        s = str(x).strip()
        m = re.search(r"(\d{3,5})$", s)
        if m:
            return int(m.group(1))
        return None   

    mapa_dias = {1:"Lunes", 2:"Martes", 3:"Miércoles", 4:"Jueves", 5:"Viernes", 6:"Sábado", 7:"Domingo"}

    merged_csv_actualizado["DIA_SEMANA"] = merged_csv_actualizado["FEHCA_HORA"].dt.isocalendar().day
    merged_csv_actualizado["DIA_SEMANA_NOMBRE"] = merged_csv_actualizado["DIA_SEMANA"].map(mapa_dias)
    merged_csv_actualizado["FIN_DE_SEMANA"] = merged_csv_actualizado["DIA_SEMANA"].isin([6, 7]).map({True: "SI", False: "NO"})

    merged_csv_actualizado["DIA_SEMANA_ORIG"] = merged_csv_actualizado["FECHA_HORA_ORIG"].dt.isocalendar().day
    merged_csv_actualizado["DIA_SEMANA_ORIG_NOMBRE"] = merged_csv_actualizado["DIA_SEMANA_ORIG"].map(mapa_dias)
    merged_csv_actualizado["FIN_DE_SEMANA_ORIG"] = merged_csv_actualizado["DIA_SEMANA_ORIG"].isin([6, 7]).map({True: "SI", False: "NO"})

    merged_csv_actualizado["TIENDA"] = merged_csv_actualizado["TIENDA"].apply(normalize_tienda)

    nombres_centros = conn.execute("SELECT CODIGO_TIENDA, NOMBRE_TIENDA FROM centros").fetchdf()
    nombres_centros['CODIGO_TIENDA'] = nombres_centros['CODIGO_TIENDA'].astype(str)

    merged_csv_actualizado["TIENDA"] = merged_csv_actualizado["TIENDA"].astype(str)

    # Enrich with store names
    merged_csv_actualizado = merged_csv_actualizado.merge(
        nombres_centros, 
        left_on="TIENDA", 
        right_on="CODIGO_TIENDA", 
        how="left"
    )
    merged_csv_actualizado = merged_csv_actualizado.drop(columns=["TIENDA"])
    merged_csv_actualizado["NOMBRE_TIENDA"] = merged_csv_actualizado["NOMBRE_TIENDA"].fillna("OTROS CENTROS")

    merged_csv_actualizado["IMPORTE"] = (merged_csv_actualizado["IMPORTE"] / 100).round(2)
    merged_csv_actualizado["FECHA"] = merged_csv_actualizado["FECHA"].dt.strftime("%Y-%m-%d")

    # --------------------------------------------------
    # 8. REORDENAR Y TIPAR COLUMNAS
    # --------------------------------------------------
    columnas_ventas = [
        'PAIS','CODIGO_TIENDA','NOMBRE_TIENDA','NUM_VENDEDOR','TALON',
        'FECHA_HORA','FECHA','HORA','MINUTO','DIA_SEMANA','DIA_SEMANA_NOMBRE',
        'FIN_DE_SEMANA','CODIGO_OPERACION','TALON_ORIGINAL','TIENDA_ORIG',
        'FECHA_HORA_ORIG','FECHA_ORIG','HORA_ORIG','MINUTO_ORIG','DIA_SEMANA_ORIG',
        'DIA_SEMANA_ORIG_NOMBRE','FIN_DE_SEMANA_ORIG','CODIGO_OPERACION_ORIG','EAN',
        'VENTA_DIRECTA','DEVOLUCION','CONFIRMACION','PEDIDO','ANULACION','IMPORTE'
    ]

    # Crear copia explícita para evitar SettingWithCopyWarning
    ventas_df = merged_csv_actualizado[columnas_ventas].copy()

    # --- Tipar columnas de texto ---
    text_cols = [
        "PAIS", "CODIGO_TIENDA", "NOMBRE_TIENDA",
        "NUM_VENDEDOR", "TALON",
        "FECHA_HORA", "FECHA",
        "DIA_SEMANA_NOMBRE", "FIN_DE_SEMANA",
        "CODIGO_OPERACION",
        "FECHA_HORA_ORIG", "FECHA_ORIG",
        "DIA_SEMANA_ORIG_NOMBRE", "FIN_DE_SEMANA_ORIG",
        "CODIGO_OPERACION_ORIG",
        "EAN"
    ]

    for c in text_cols:
        ventas_df.loc[:, c] = ventas_df[c].astype("string")

    # --- Tipar columnas enteras ---
    int_cols = [
        "HORA", "MINUTO",
        "DIA_SEMANA",
        "TALON_ORIGINAL", "TIENDA_ORIG",
        "HORA_ORIG", "MINUTO_ORIG",
        "DIA_SEMANA_ORIG",
        "VENTA_DIRECTA", "DEVOLUCION", "CONFIRMACION",
        "PEDIDO", "ANULACION"
    ]

    for c in int_cols:
        ventas_df.loc[:, c] = (
            ventas_df[c]
            .replace("", None)
            .astype("Int64")  # Int64 permite NaN compatible con DuckDB
        )

    # --- Tipado de float ---
    ventas_df.loc[:, "IMPORTE"] = ventas_df["IMPORTE"].astype("float64")

    conn.register("ventas_tmp", ventas_df)
    conn.register("centros_tmp", pd.DataFrame({'CODIGO_TIENDA': centres}))
    conn.register("eans_tmp", pd.DataFrame({'EAN': eans_procesar}))

    # FILTRAR PER BOTIGUES DE LA DEMO
    ventas_filtradas_df = conn.execute("""
        SELECT v.* 
        FROM ventas_tmp v
        JOIN centros_tmp c ON v.CODIGO_TIENDA = c.CODIGO_TIENDA
        JOIN eans_tmp e ON v.EAN = e.EAN           
    """).fetch_df()

    conn.unregister("ventas_tmp")
    conn.unregister("centros_tmp")
    conn.unregister("eans_tmp")

    ventas_df.to_csv("backend/db/exports/export_ventas.csv", sep=";", index=False)
    ventas_filtradas_df.to_csv("backend/db/exports/export_ventas_filtradas.csv", sep=";", index=False)

    return ventas_filtradas_df

#-------------------------------------------------------
#   1. OBTENIR PRODUCTES A PROCESSAR
#-------------------------------------------------------
def obtenir_productes_procesar() -> tuple[pd.DataFrame, pd.DataFrame, list, list]:
    
    def clean_palmares(df:pd.DataFrame):
        df.columns = df.columns.str.strip()
        df = df.dropna(how="all")
        df = df[df["ESP - Couv"] != "#DIV/0"]
        
        columnas_necesarias = [
            "Saison de gestion",
            "Collection",
            "Libellé famille",
            "Code produit",
            "Code coloris",
            "Libellé produit",
            "Libellé coloris",
            "Nbre semaines implant (MC/Zone)",
            "ESP - Qté vendue",
            "ESP - Couv",
            "ESP - Stk dispo mag",
            "Stk dispo dépôt",
            "Situation de Stock dépôt"
        ]

        
        faltantes = [c for c in columnas_necesarias if c not in df.columns]

        if faltantes:
            print("Error: Columnas faltantes:", faltantes)
            quit()

        return df

    def carregar_palmares() -> pd.DataFrame:     
        
        # 1. Crear carpeta si no existe
        if not PALMARES_DIR.exists():
            print("Error: no se ha encontrado la carpeta 'backend/palmares'")
            quit()

        # 2. Buscar archivos .xlsx
        archivos_xlsx = list(PALMARES_DIR.glob("*.xlsx"))

        if not archivos_xlsx:
            print("Error: No se ha encontrado ningun archivo en la carpeta 'backend/palmares'")
            quit()

        # 3. Leer todos los archivos y concatenarlos
        lista_df = []
        for archivo in archivos_xlsx:
            try:
                df = pd.read_excel(archivo, sheet_name="ECI", skiprows=3)
                lista_df.append(df)
            except Exception as e:
                print(f"Error leyendo {archivo}: {e}")

        if not lista_df:
            print("Error: No se ha podido leer ningun archivo válido")
            quit()
        
        df_total:pd.DataFrame = pd.concat(lista_df, ignore_index=True)

        #df_total.to_excel(PALMARES_DIR / "palmares_total.xlsx", index=False)
        
        return clean_palmares(df_total)
  

    palmares_df = carregar_palmares()    

    productes_procesar_df = duckdb.query("""
        SELECT
            "Saison de gestion" AS TEMPORADA,
            Collection AS COLLECTION,
            "Libellé famille" AS FAMILIA, 
            "Code produit" AS CODEPRODUIT, 
            "Code coloris" AS CODECOLORIS, 
            "Libellé produit" AS NOMPRODUIT,
            "Libellé coloris" AS LIBCOLORIS,
            CAST("Nbre semaines implant (MC/Zone)" AS INTEGER) AS SEMANAS_IMPLANTACION,
            CAST("ESP - Qté vendue" AS INTEGER) AS CANTIDAD_VENDIDA,
            CAST("ESP - Couv" AS INTEGER) AS SEMANAS_COBERTURA,
            CAST("ESP - Stk dispo mag" AS INTEGER) AS CANTIDAD_DISPONIBLE_CENTROS,
            CAST("Stk dispo dépôt" AS INTEGER) AS CANTIDAD_DISPONIBLE_ALMACENES
        FROM palmares_df
        WHERE 
            "Situation de Stock dépôt" IN ('Gestion de pénurie', 'Rupture')
            AND CAST("Nbre semaines implant (MC/Zone)" AS INTEGER) >= 3
            AND CAST("ESP - Stk dispo mag" AS INTEGER) > 10
            AND CAST("ESP - Couv" AS INTEGER) < 13
            AND CAST("ESP - Qté vendue" AS INTEGER) > 10
    """).fetchdf()

    if productes_procesar_df.empty:
        return pd.DataFrame(), pd.DataFrame(), [], []

    codeproduit_procesar = productes_procesar_df["CODEPRODUIT"].dropna().unique().tolist()

    eans_procesar_df = run_query_to_df(
        f"""
        SELECT 
            CODEPRODUIT, 
            CODECOLORIS, 
            CODEBARRES, 
            CODEINTERNEARTICLE 
        FROM STORELAND.ARTICLES
        WHERE CODEPRODUIT IN ({', '.join(map(str, codeproduit_procesar))})
        """,
        "eans_procesar.csv"
    )

    productos_ean_df = productes_procesar_df.merge(
        eans_procesar_df,
        on=["CODEPRODUIT", "CODECOLORIS"],
        how="inner"
    )

    productos_df = productos_ean_df[['TEMPORADA','COLLECTION','FAMILIA','CODEPRODUIT','CODECOLORIS','NOMPRODUIT','LIBCOLORIS','CODEBARRES','CODEINTERNEARTICLE']]

    return (
        productes_procesar_df,
        productos_df,
        productos_ean_df["CODEBARRES"].dropna().tolist(),
        productos_ean_df["CODEINTERNEARTICLE"].dropna().tolist()
    )

#-------------------------------------------------------
#   4. OBTENIR STOCK PER CENTRE I PRODUCTE (STORELAND)
#-------------------------------------------------------
def obtenir_stock(
        conn:DuckDBPyConnection, 
        centros:list = [],
        codigos_internos:list = [],
    ) -> pd.DataFrame | None:

    # Separar codigos de articulos de 1000 en 1000 (limitació bdd STORELAND)
    def chunked(lst, chunk_size=999):
        """Genera bloques de lst sin crear todas las sublistas de golpe."""
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]
    
    query = """
        SELECT
            CODEMAGASIN,
            CODEINTERNEARTICLE,

            SUM(CASE WHEN CODECPTSTOCKMAG = 1  THEN QTEENSTOCK ELSE 0 END) AS DISPONIBLE,
            SUM(CASE WHEN CODECPTSTOCKMAG = 2  THEN QTEENSTOCK ELSE 0 END) AS TRANSITO,
            SUM(CASE WHEN CODECPTSTOCKMAG = 10 THEN QTEENSTOCK ELSE 0 END) AS PREPARACION,

            MAX(DATEMODIFICATION) AS DATEMODIFICATION,
            MAX(DATECREATION)     AS DATECREATION

        FROM STORELAND.STOCKS_ARTICLES_MAGASINS
        WHERE CODECPTSTOCKMAG IN (1,2,10)
    """

    if len(centros) > 0:
        query += f" AND CODEMAGASIN IN ({', '.join(centros)})"
    
    if len(codigos_internos) > 0:
        chunks_codebarres = []
        for chunk in chunked(codigos_internos, 999):
            csv_vals = ", ".join(map(str, chunk))
            chunks_codebarres.append(f"CODEINTERNEARTICLE IN ({csv_vals})")

        query += " AND (" + " OR ".join(chunks_codebarres) + ")"

    query += """
        GROUP BY CODEMAGASIN, CODEINTERNEARTICLE
    """

    stock_df = run_query_to_df(query, "stock_df.csv")

    codigos_internos_articulos = stock_df['CODEINTERNEARTICLE'].drop_duplicates().tolist()
    
    conds = []
    for chunk in chunked(codigos_internos_articulos, 999):
        csv_vals = ", ".join(str(x) for x in chunk)
        conds.append(f"a.CODEINTERNEARTICLE IN ({csv_vals})")

    where_clause = "(" + " OR ".join(conds) + ")"

    # INFORMACION COMPLETA DE LOS ARTICULOS
    full_info_articulos_df = run_query_to_df(
        f"""
            SELECT 
                p.NOMPRODUIT, 
                c.LIBCOLORIS,
                t.TAILLE, 

                a.CODEINTERNEARTICLE, 
                a.CODEPRODUIT, 
                 
                a.CODEBARRES,

                C.CODECOLORIS,

                t.CODEGRILLETAILLE, 
                t.INDICE

            FROM STORELAND.ARTICLES a 
                                            
            JOIN STORELAND.PRODUITS p
                ON a.CODEPRODUIT = p.CODEPRODUIT
                                            
            LEFT JOIN STORELAND.LIGNES_GRILLE_TAILLE t
                ON t.CODEGRILLETAILLE = a.CODEGRILLETAILLE
                AND t.INDICE = a.INDICE
                                            
            LEFT JOIN STORELAND.COLORIS c
                ON c.CODECOLORIS = a.CODECOLORIS

            WHERE {where_clause}
        """,
        "full_info_articulos.csv"
    )

    full_stock_df = duckdb.query("""
        SELECT 
            s.CODEMAGASIN,
                                        
            a.NOMPRODUIT, 
            s.CODEINTERNEARTICLE, 
            a.CODEPRODUIT,

            a.LIBCOLORIS,   
            a.CODECOLORIS,                
            a.TAILLE, 
                                        
            a.CODEBARRES, 
                                        
            GREATEST(s.DISPONIBLE, 0) AS DISPONIBLE, 
            GREATEST(s.TRANSITO, 0) AS TRANSITO, 
            GREATEST(s.PREPARACION, 0) AS PREPARACION, 
            GREATEST(s.DISPONIBLE + s.TRANSITO + s.PREPARACION, 0) AS TOTAL
                                        
        FROM stock_df s 
        JOIN full_info_articulos_df a
            ON s.CODEINTERNEARTICLE = a.CODEINTERNEARTICLE
        ORDER BY s.CODEMAGASIN, a.CODEPRODUIT, a.CODEGRILLETAILLE, a.INDICE;
    """).fetchdf()

    return full_stock_df

#-------------------------------------------------------
#   5. GENERAR stock_ventas_centro
#-------------------------------------------------------
def generar_stock_ventas_centro(conn:DuckDBPyConnection):

    # print(f"Obteniendo ventas del {fecha_inicial_str} hasta {fecha_hoy_str}")

    stock_ventas_centro_df = conn.execute("""
        WITH ventas_4s AS (
            SELECT
                v.CODIGO_TIENDA,
                CAST(v.EAN AS TEXT) AS EAN,
                GREATEST(
                    SUM(COALESCE(v.VENTA_DIRECTA, 0) + COALESCE(v.DEVOLUCION, 0)), 
                    0
                ) AS TOTAL_VENTAS_BRUTAS
            FROM ventas v
            GROUP BY
                v.CODIGO_TIENDA,
                CAST(v.EAN AS TEXT)
        ),

        stock_agg AS (
            SELECT
                s.CODEMAGASIN,
                c.CATEGORIA,
                p.CODEPRODUIT,
                p.CODECOLORIS,
                p.NOMPRODUIT,
                p.LIBCOLORIS,

                SUM(COALESCE(s.DISPONIBLE, 0)) AS STOCK_DISPONIBLE,
                SUM(COALESCE(s.TRANSITO, 0)) AS STOCK_TRANSITO,
                SUM(COALESCE(s.PREPARACION, 0)) AS STOCK_PREPARACION,
                SUM(COALESCE(s.TOTAL, 0)) AS STOCK_TOTAL

            FROM stock s
            JOIN centros c 
                ON s.CODEMAGASIN = c.CODIGO_TIENDA

            JOIN productos p
                ON CAST(s.CODEBARRES AS TEXT) = CAST(p.CODEBARRES AS TEXT)

            GROUP BY
                s.CODEMAGASIN,
                c.CATEGORIA,
                p.CODEPRODUIT,
                p.CODECOLORIS,
                p.NOMPRODUIT,
                p.LIBCOLORIS
        ),

        ventas_agg AS (
            SELECT
                v.CODIGO_TIENDA AS CODEMAGASIN,
                c.CATEGORIA,
                p.CODEPRODUIT,
                p.CODECOLORIS,
                p.NOMPRODUIT,
                p.LIBCOLORIS,

                SUM(COALESCE(v.TOTAL_VENTAS_BRUTAS, 0)) AS VENTA_4SEMANAS

            FROM ventas_4s v
            JOIN productos p
                ON CAST(v.EAN AS TEXT) = CAST(p.CODEBARRES AS TEXT)

            JOIN centros c
                ON v.CODIGO_TIENDA = c.CODIGO_TIENDA

            GROUP BY
                v.CODIGO_TIENDA,
                c.CATEGORIA,
                p.CODEPRODUIT,
                p.CODECOLORIS,
                p.NOMPRODUIT,
                p.LIBCOLORIS
        ),

        base AS (
            SELECT
                CODEMAGASIN,
                CATEGORIA,
                CODEPRODUIT,
                CODECOLORIS,
                NOMPRODUIT,
                LIBCOLORIS
            FROM stock_agg

            UNION

            SELECT
                CODEMAGASIN,
                CATEGORIA,
                CODEPRODUIT,
                CODECOLORIS,
                NOMPRODUIT,
                LIBCOLORIS
            FROM ventas_agg
        ),

        stock_ventas_centro AS (
            SELECT
                b.CODEMAGASIN,
                b.CATEGORIA,
                b.CODEPRODUIT,
                b.CODECOLORIS,
                b.NOMPRODUIT,
                b.LIBCOLORIS,

                COALESCE(s.STOCK_DISPONIBLE, 0) AS STOCK_DISPONIBLE,
                COALESCE(s.STOCK_TRANSITO, 0) AS STOCK_TRANSITO,
                COALESCE(s.STOCK_PREPARACION, 0) AS STOCK_PREPARACION,
                COALESCE(s.STOCK_TOTAL, 0) AS STOCK_TOTAL,

                CAST(COALESCE(v.VENTA_4SEMANAS, 0) AS INTEGER) AS VENTA_4SEMANAS,

                COALESCE(v.VENTA_4SEMANAS, 0) / 4.0 AS VELOCIDAD_SEMANAL_REAL,

                CASE 
                    WHEN COALESCE(v.VENTA_4SEMANAS, 0) = 0 THEN 0
                    WHEN COALESCE(v.VENTA_4SEMANAS, 0) / 4.0 < 1 THEN 1
                    ELSE ROUND(COALESCE(v.VENTA_4SEMANAS, 0) / 4.0)
                END AS VELOCIDAD_OPERATIVA,

                CASE
                    WHEN COALESCE(s.STOCK_TOTAL, 0) = 0 THEN 0
                    WHEN COALESCE(v.VENTA_4SEMANAS, 0) = 0 THEN 999
                    ELSE ROUND(
                        COALESCE(s.STOCK_TOTAL, 0) /
                        CASE 
                            WHEN COALESCE(v.VENTA_4SEMANAS, 0) / 4.0 < 1 THEN 1
                            ELSE ROUND(COALESCE(v.VENTA_4SEMANAS, 0) / 4.0)
                        END
                    )
                END AS SEMANAS_ROTACION,

                CASE 
                    WHEN COALESCE(s.STOCK_TRANSITO, 0) + COALESCE(s.STOCK_PREPARACION, 0) > 0 THEN TRUE
                    ELSE FALSE
                END AS TIENE_REPOSICION

            FROM base b

            LEFT JOIN stock_agg s
                ON b.CODEMAGASIN = s.CODEMAGASIN
                AND b.CODEPRODUIT = s.CODEPRODUIT
                AND b.CODECOLORIS = s.CODECOLORIS

            LEFT JOIN ventas_agg v
                ON b.CODEMAGASIN = v.CODEMAGASIN
                AND b.CODEPRODUIT = v.CODEPRODUIT
                AND b.CODECOLORIS = v.CODECOLORIS
        )

        SELECT
            CODEMAGASIN,
            CATEGORIA,
            NOMPRODUIT,
            LIBCOLORIS,

            STOCK_DISPONIBLE,
            STOCK_TRANSITO,
            STOCK_PREPARACION,
            STOCK_TOTAL,

            VENTA_4SEMANAS,
            VELOCIDAD_SEMANAL_REAL,
            VELOCIDAD_OPERATIVA,
            SEMANAS_ROTACION,
                                          
            TIENE_REPOSICION,

            CASE
                WHEN VENTA_4SEMANAS = 0
                    AND STOCK_DISPONIBLE > 0
                    AND TIENE_REPOSICION = FALSE
                THEN 'EMISOR'

                WHEN VENTA_4SEMANAS > 0
                    AND SEMANAS_ROTACION < 10
                THEN 'RECEPTOR'

                ELSE 'NEUTRO'
            END AS perfil

        FROM stock_ventas_centro

        WHERE STOCK_TOTAL > 0
        OR VENTA_4SEMANAS > 0

        ORDER BY
            CODEMAGASIN,
            NOMPRODUIT,
            LIBCOLORIS;
    """).fetchdf()

    return stock_ventas_centro_df

#-------------------------------------------------------
#   7. APLICAR EL ALGORITME RESTOCK
#-------------------------------------------------------
def restock(
        conn:DuckDBPyConnection,
        exportar_movimientos = True,
        exportar_estancados = False,
    ) -> pd.DataFrame:

    def obtener_pares(nombre_producto:str, color_producto:str):
        return conn.execute(f"""
            WITH posibles_emisores AS (
                SELECT svc.CODEMAGASIN, c.NOMBRE_TIENDA, svc.STOCK_TOTAL, svc.CATEGORIA
                FROM stock_ventas_centro svc
                JOIN centros c
                    ON svc.CODEMAGASIN = c.CODIGO_TIENDA
                WHERE svc.PERFIL = 'EMISOR'
                    AND svc.NOMPRODUIT = '{nombre_producto}'
                    AND svc.LIBCOLORISMODIFIE = '{color_producto}'
            ),
            posibles_receptores AS (
                SELECT svc.CODEMAGASIN, c.NOMBRE_TIENDA, svc.STOCK_TOTAL, svc.VELOCIDAD_SEMANAL_REAL, svc.VELOCIDAD_OPERATIVA, svc.semanas_rotacion, svc.CATEGORIA
                FROM stock_ventas_centro svc
                JOIN centros c
                    ON svc.CODEMAGASIN = c.CODIGO_TIENDA
                WHERE svc.PERFIL = 'RECEPTOR'
                    AND svc.NOMPRODUIT = '{nombre_producto}'
                    AND svc.LIBCOLORISMODIFIE = '{color_producto}'
            )
            SELECT 
                e.CODEMAGASIN AS EMISOR,
                e.NOMBRE_TIENDA AS NOMBRE_EMISOR,

                r.CODEMAGASIN AS RECEPTOR,
                r.NOMBRE_TIENDA AS NOMBRE_RECEPTOR,

                e.STOCK_TOTAL AS STOCK_EMISOR,
                r.STOCK_TOTAL AS STOCK_RECEPTOR,

                r.VELOCIDAD_SEMANAL_REAL AS VELOCIDAD_REAL_RECEPTOR,
                r.VELOCIDAD_OPERATIVA AS VELOCIDAD_OPERATIVA_RECEPTOR,

                r.SEMANAS_ROTACION AS COBERTURA_INICIAL,

                d.distancia_minutos
            FROM posibles_receptores r
            CROSS JOIN posibles_emisores e
            JOIN distancias d
                ON e.CODEMAGASIN = d.CODIGO_ORIGEN
            AND r.CODEMAGASIN = d.CODIGO_DESTINO
            ORDER BY
                r.VELOCIDAD_SEMANAL_REAL DESC,
                r.SEMANAS_ROTACION ASC,
                e.STOCK_TOTAL DESC,
                d.distancia_minutos ASC;
        """).fetchdf()

    def obtener_tallas_emisor(emisor, nombre_producto, color):
        return conn.execute(f"""
            SELECT 
                CODEBARRES,
                TAILLE,
                STOCK_DISPONIBLE AS STOCK_TOTAL
            FROM stock_disponible
            WHERE 
                EMISOR = {emisor}
                AND NOMBRE_PRODUCTO = '{nombre_producto}'
                AND COLOR = '{color}'
            ORDER BY TAILLE
        """).fetchdf()

    def obtener_url_foto(codigo_producto:str, codigo_color:str):

        result = conn.execute("SELECT URL_FOTO FROM fotos_productos WHERE CODEPRODUIT = ? AND CODECOLORIS = ?",(codigo_producto, codigo_color)).fetchone()

        url_foto = result[0] if result else '#'

        return url_foto

    def procesar_receptor(
            nombre_producto:str, 
            color:str, 

            codigo_producto,
            codigo_color,

            stock_tallas_receptor_df:pd.DataFrame, 
            cobertura_inicial_tallas_receptor, 
            pares_receptor
        ):
        
        # Stock y velocidad inicial
        stock_receptor = pares_receptor.iloc[0]["STOCK_RECEPTOR"]
        velocidad_real = pares_receptor.iloc[0]["VELOCIDAD_REAL_RECEPTOR"]
        velocidad_operativa = pares_receptor.iloc[0]["VELOCIDAD_OPERATIVA_RECEPTOR"]
        cobertura = pares_receptor.iloc[0]['COBERTURA_INICIAL'] 

        stock_acumulado = stock_receptor
        cobertura_acumulada = cobertura

        #DEBUG
        receptor_log = []

        movimientos:list[dict] = []
        pares_validos:list[tuple] = []
        pares_no_validos:list[tuple] = []
        stock_tallas_receptor_dict:dict = {}

        for idx, par in enumerate(pares_receptor.itertuples(index=False)):

            # ----- obtener tallas del emisor -----
            tallas_emisor_df = obtener_tallas_emisor(
                par.emisor,
                nombre_producto,
                color
            )

            aporte = tallas_emisor_df["STOCK_TOTAL"].sum()
            tallas = tallas_emisor_df["TAILLE"].unique().tolist()
            tallas_str = ', '.join(tallas)

            #DEBUG
            receptor_log.append({
                "producto": nombre_producto,
                "color": color,
                "msg":f"{aporte} productes de {par.emisor} a {par.receptor}"
            })


            if aporte == 0:
                continue

            # ----- calcular cobertura tentativa -----
            cobertura_tentativa = (stock_acumulado + aporte) / velocidad_operativa

            cantidad_producto = stock_acumulado + aporte

            if cobertura_tentativa > COBERTURA_MAXIMA:

                #DEBUG
                receptor_log.append({
                    "producto": nombre_producto,
                    "color": color,
                    "msg": f"Emisor {par.emisor} rebutjat. Supera cobertura máxima"
                })

                pares_no_validos.append((par.emisor, par.receptor, "Supera cobertura maxima"))

                continue  # rechazar emisor

            if cantidad_producto > CANTIDAD_MAXIMA_PRODUCTOS:

                #DEBUG
                receptor_log.append({
                    "producto": nombre_producto,
                    "color": color,
                    "msg": f"Emisor {par.emisor} rebutjat. Supera cantitat d'unitats màximes"
                })

                pares_no_validos.append((par.emisor, par.receptor, "Supera cantitat de producte"))

                continue  # rechazar emisor

            
            #DEBUG
            receptor_log.append({
                "producto": nombre_producto,
                "color": color,
                "msg":f"Emisor {par.emisor} acceptat"
            })

            url_foto = obtener_url_foto(codigo_producto, codigo_color)

            # ----- aceptar emisor -----
            movimientos.append({
                "EMISOR": par.emisor,
                "NOMBRE_EMISOR":par.nombre_emisor,
                
                "RECEPTOR": par.receptor,
                "NOMBRE_RECEPTOR": par.nombre_receptor,

                "NOMBRE_PRODUCTO": nombre_producto, 
                "COLOR": color,
                "TALLAS": tallas_str,

                "CODIGO_PRODUCTO": codigo_producto,
                "CODIGO_COLOR": codigo_color,

                "STOCK_INICIAL_RECEPTOR": stock_receptor,
                "STOCK_ANTES": stock_acumulado,
                "APORTE": aporte,
                "STOCK_DESPUES": stock_acumulado + aporte,

                "COBERTURA_ANTES": round(cobertura_acumulada),
                "COBERTURA_DESPUES": round(cobertura_tentativa),

                "URL_FOTO": url_foto
            })

            #----- registrar como valido -----
            pares_validos.append((par.emisor, par.receptor))
         
            conn.execute(f"""
                UPDATE stock_disponible
                SET STOCK_DISPONIBLE = 0
                WHERE
                    emisor = {par.emisor}
                    AND producto = '{nombre_producto}'
                    AND color = '{color}'
            """)


            stock_acumulado += aporte
            cobertura_acumulada = cobertura_tentativa

            #----- sumar stock per talles del emisor al receptor -----
            stock_tallas_receptor_df:pd.DataFrame = (
                pd.concat([stock_tallas_receptor_df, tallas_emisor_df])
                .groupby(["CODEBARRES", "TAILLE"], as_index=False)
                .agg({"STOCK_TOTAL": "sum"})
                .sort_values("TAILLE")
            )

            #----- comprobar que no es supera la cobertura maxima per la seguent iteracio-----
            if cobertura_acumulada >= COBERTURA_MAXIMA:
                #DEBUG
                receptor_log.append({
                    "producto": nombre_producto,
                    "color": color,
                    "msg": f"Cobertura máxima assolida per receptor {par.receptor}"
                })
                break

        
        if len(stock_tallas_receptor_df) > 0:
                cobertura_final_tallas_receptor = (
                    (stock_tallas_receptor_df["STOCK_TOTAL"] > 0).sum()
                    / len(stock_tallas_receptor_df)
                )
        else:
            cobertura_final_tallas_receptor = 0


        if len(movimientos) > 0:

            if cobertura_final_tallas_receptor < PORCENTAJE_TALLAS_CUBIERTAS and cobertura_final_tallas_receptor <= cobertura_inicial_tallas_receptor:
                receptor_log.append({
                    "producto": nombre_producto,
                    "color": color,
                    "msg": "Coberturas de tallas insuficiente"
                })

                pares_no_validos.append((par.emisor, par.receptor, "Coberturas de tallas insuficiente"))

            stock_tallas_receptor_dict = stock_tallas_receptor_df.to_dict()

        #DEBUG
        debug_log.extend(receptor_log)

        return movimientos, pares_validos, pares_no_validos, stock_tallas_receptor_dict
        
    debug_log = []

    propuestas = []
    productos_estancados = []

    # CREAR UN STOCK DISPONIBLE GLOBAL 
    conn.execute("""
        CREATE TEMP TABLE stock_disponible AS
        SELECT
            CODEMAGASIN AS EMISOR,
            NOMPRODUIT AS NOMBRE_PRODUCTO,
            LIBCOLORISMODIFIE AS COLOR,
            CODEBARRES,
            TAILLE,
            SUM(TOTAL) AS STOCK_DISPONIBLE
        FROM stock
        GROUP BY
            CODEMAGASIN,
            NOMPRODUIT,
            LIBCOLORISMODIFIE,
            CODEBARRES,
            TAILLE
    """)

    productos_a_procesar_df = conn.execute("SELECT NOMPRODUIT, LIBCOLORISMODIFIE FROM productos_procesar").fetch_df()

    for nombre_producto, color_producto in (productos_a_procesar_df[['NOMPRODUIT', 'LIBCOLORISMODIFIE']].drop_duplicates().itertuples(index=False, name=None)):

        codigo_producto, codigo_color = conn.execute(
            "SELECT CODEPRODUIT, CODECOLORISSEL FROM stock WHERE NOMPRODUIT=? AND LIBCOLORISMODIFIE=? LIMIT 1",
            [nombre_producto, color_producto]
        ).fetchone() or (None, None)

        #os.system("cls")

        #DEBUG
        debug_log.append({
            "producto":nombre_producto,
            "color":color_producto,
            'msg':"INICIO EVALUACIÓN"
        })

        pares_df = obtener_pares(nombre_producto, color_producto)

        if pares_df.empty:

            for emisor in pares_df.emisor:
                productos_estancados.append({
                    "producto": nombre_producto,
                    "color": color_producto,
                    "centro": emisor,
                    "motivo": "Sin venta en las ultimas 4 semanas"
                })

            debug_log.append({
                "producto":nombre_producto,
                "color":color_producto,
                'msg':"Producto estancado"
            })
            continue

        #DEBUG
        debug_log.append({
            "producto":nombre_producto,
            "color":color_producto,
            "msg":f"{len(pares_df)} pares generados"
        })      

        posibles_receptores = pares_df["RECEPTOR"].unique().tolist()

        full_pares_validos = []
        full_pares_no_validos = []
        stocks_finales_receptor = []

        for receptor in posibles_receptores:

            # ----- stock por talla receptor -----
            stock_inicial_tallas_receptor_df = conn.execute(f"""
                SELECT 
                    CODEBARRES,
                    TAILLE,
                    SUM(TOTAL) as STOCK_TOTAL
                FROM stock
                WHERE 
                    CODEMAGASIN = {receptor}
                    AND NOMPRODUIT = '{nombre_producto}'
                    AND LIBCOLORISMODIFIE = '{color_producto}'
                GROUP BY CODEBARRES,TAILLE 
                ORDER BY TAILLE
            """).fetchdf()

            conn.register("stock_inicial_tallas_receptor",stock_inicial_tallas_receptor_df)

            cobertura_inicial_tallas_receptor = float(conn.execute(f"""
                SELECT COUNT(*) FILTER (WHERE STOCK_TOTAL > 0) / COUNT(*) AS COBERTURA_TALLAS_RECEPTOR
                FROM stock_inicial_tallas_receptor
            """).fetchone()[0])

            conn.unregister("stock_inicial_tallas_receptor")

            # Filtrar pares solo para este receptor
            pares_receptor = pares_df[pares_df["RECEPTOR"] == receptor]

            movimientos, pares_validos, pares_no_validos, stock_tallas_receptor_final_dict = procesar_receptor(
                nombre_producto, 
                color_producto, 

                codigo_producto,
                codigo_color,

                stock_inicial_tallas_receptor_df, 
                cobertura_inicial_tallas_receptor, 
                pares_receptor
            )        
            
            full_pares_validos += pares_validos
            full_pares_no_validos += pares_no_validos 

            if not movimientos:
                debug_log.append({
                    "producto":nombre_producto,
                    "color":color_producto,
                    "msg":f"Receptor {receptor} sin posibilidad de enviarle stock"
                })
            else:
                propuestas.extend(movimientos)

        pares_validos = set(full_pares_validos)
        pares_no_validos = set(full_pares_no_validos)

        for emisor, _, msg in pares_no_validos:
            productos_estancados.append({
                "producto": nombre_producto,
                "color": color_producto,
                "emisor": emisor,
                "motivo": msg
            })
        
        stocks_finales_receptor.append(stock_tallas_receptor_final_dict)

    #DEBUG
    pd.DataFrame(debug_log).to_csv(
        LOGS_DIR / "log_restock.csv",
        sep=";",
        index=False
    )

    propuestas_df = pd.DataFrame(propuestas)
    productos_estancados_df = pd.DataFrame(productos_estancados)

    if exportar_movimientos:
                
        files_xlsx = glob.glob(os.path.join(RESULTADOS_DIR, "*.xlsx"))

        # Tomar el primero encontrado
        if files_xlsx:
            excel_path = files_xlsx[0]
            destino_path = os.path.join(HISTORIAL_RESULTADOS_DIR, os.path.basename(excel_path))
            shutil.move(excel_path, destino_path)

        files_csv = glob.glob(os.path.join(RESULTADOS_DIR, "*.csv"))
        if files_csv:
            csv_file_path = files_csv[0]
            Path(csv_file_path).unlink()

        
        # EXPORTAR A XLSX
        with pd.ExcelWriter(RESULTADOS_DIR / f"movimientos_{fecha_hoy_str}.xlsx", engine="xlsxwriter") as writer:
            for emisor, df_emisor in propuestas_df.groupby("EMISOR"):

                # Excel limita los nombres de hoja a 31 caracteres
                sheet_name = str(emisor)[:31]

                df_emisor.to_excel(writer, sheet_name=sheet_name, index=False)

                worksheet = writer.sheets[sheet_name]

                filas, columnas = df_emisor.shape

                columnas_tabla = [{"header": col} for col in df_emisor.columns]

                worksheet.add_table(0, 0, filas, columnas - 1, {
                    "name": "C_" + str(emisor),
                    "columns": columnas_tabla,
                    "style": "Table Style Medium 9"
                })

        propuestas_df.to_csv(RESULTADOS_DIR / f"movimientos_{fecha_hoy_str}.csv", sep=";", index=False)

    if exportar_estancados:
        productos_estancados_df.to_excel(RESULTADOS_DIR / "estancados.xlsx", index=False)


    return propuestas_df

def ejecutar_restock(
    productos:pd.DataFrame=pd.DataFrame(),
    centros:pd.DataFrame=pd.DataFrame(),
    cobertura_maxima=8,
    porcentaje_tallas=0.75,
    cantidad_maxima=17
):
    try:
        #-------------------------------------------------------
        #   PARAMETRES
        #-------------------------------------------------------
        global COBERTURA_MAXIMA
        global PORCENTAJE_TALLAS_CUBIERTAS
        global CANTIDAD_MAXIMA_PRODUCTOS

        COBERTURA_MAXIMA = cobertura_maxima
        PORCENTAJE_TALLAS_CUBIERTAS = porcentaje_tallas
        CANTIDAD_MAXIMA_PRODUCTOS = cantidad_maxima

        #-------------------------------------------------------
        #   PATHS
        #-------------------------------------------------------
        BASE_DIR = Path(__file__).resolve().parent
        BACKEND_DIR = BASE_DIR / "backend"
        LOGS_DIR = BACKEND_DIR / "logs"
        BDD_DIR = BACKEND_DIR / "db"
        BDD_EXPORTS_DIR = BDD_DIR / "exports"
        PALMARES_DIR = BACKEND_DIR / "palmares"
        RESULTADOS_DIR = BASE_DIR / "resultados"
        HISTORIAL_RESULTADOS_DIR = RESULTADOS_DIR / "historial"
        
        #-------------------------------------------------------
        #   CONNEXIÓN
        #-------------------------------------------------------
        conn = duckdb.connect(BDD_DIR / "restock.duckdb")

        #-------------------------------------------------------
        #   FECHAS
        #-------------------------------------------------------
        fecha_hoy = date.today()
        fecha_inicial = fecha_hoy - timedelta(weeks=4)

        fecha_hoy_str = fecha_hoy.strftime("%Y-%m-%d")
        fecha_inicial_str = fecha_inicial.strftime("%Y-%m-%d")

        #-------------------------------------------------------
        #   PIPELINE
        #-------------------------------------------------------
        # ACTUALITZAR TAULA DE PRODUCTES A PROCESAR AMB ELS PRODUCTES SELECCIONATS A LA WEB
        actualitzar_productes_procesar(conn, productos)

        # OBTENIR LES VENTES D'AQUESTS CENTRES
        ventes_df = obtenir_ventes(
            conn,
            fecha_inicial_str,
            fecha_hoy_str,
            centros,
            eans_procesar_list
        )
        actualitzar_ventes(conn,ventes_df)


        # OBTENIR STOCK DELS PRODUCTES A PROCESSAR
        stock_df = obtenir_stock(
            conn,
            centros,
            codigo_interno_procesar_list
        )
        actualitzar_stocks(conn, stock_df)


        # GENERAR STOCK VENTAS CENTROS AMB LES VENTES I ELS PRODUCTES A PROCESSAR
        stock_ventas_centro_df = generar_stock_ventas_centro(conn)
        actualitzar_stock_ventas_centro(conn, stock_ventas_centro_df)

        
        # APLICAR ALGORITME RESTOCK PER TREURE MOVIMENTS
        movimientos_df = restock(
            conn,
            exportar_movimientos=False,
            exportar_estancados=False
        )

        # GUARDAR MOVIMIENTS A LA BDD
        actualitzar_moviments(conn,movimientos_df)

        return {'result':'Movimientos generados y actualizados'}
    
    except Exception as e:
        return {'result': e}

if __name__ == "__main__":

    #-------------------------------------------------------
    #   cd django_app
    #   python manage.py runserver
    #-------------------------------------------------------


    #-------------------------------------------------------
    #   PARAMETRES
    #-------------------------------------------------------

    COBERTURA_MAXIMA = 8
    PORCENTAJE_TALLAS_CUBIERTAS = 0.75
    CANTIDAD_MAXIMA_PRODUCTOS = 17

    #-------------------------------------------------------
    #   PATHS
    #-------------------------------------------------------
    BASE_DIR = Path(__file__).resolve().parent
    BACKEND_DIR = BASE_DIR / "backend"
    LOGS_DIR = BACKEND_DIR / "logs"
    BDD_DIR = BACKEND_DIR / "db"
    BDD_EXPORTS_DIR = BDD_DIR / "exports"
    PALMARES_DIR = BACKEND_DIR / "palmares"
    RESULTADOS_DIR = BASE_DIR / "resultados"
    HISTORIAL_RESULTADOS_DIR = RESULTADOS_DIR / "historial"
    
    #-------------------------------------------------------
    #   CONNEXIÓN
    #-------------------------------------------------------
    conn = duckdb.connect(BDD_DIR / "restock.duckdb")

    #-------------------------------------------------------
    #   FECHAS
    #-------------------------------------------------------
    fecha_hoy = date.today()
    fecha_inicial = fecha_hoy - timedelta(weeks=4)

    fecha_hoy_str = fecha_hoy.strftime("%Y-%m-%d")
    fecha_inicial_str = fecha_inicial.strftime("%Y-%m-%d")

    #-------------------------------------------------------
    #   PIPELINE
    #-------------------------------------------------------
    # OBTENIR ELS CENTRES QUE TENEN PERSONAL
    centres = [row[0] for row in conn.execute(
        "SELECT codigo_tienda FROM centros WHERE tiene_personal = true"
    ).fetchall()]


    # OBTENIR PRODUCTES A PROCESAR DEL PALMARES
    productes_a_procesar_df, productos_df, eans_procesar_list, codigo_interno_procesar_list = obtenir_productes_procesar()
    if productes_a_procesar_df.empty:
        print("No hi ha productes a processar")
        quit()
    actualitzar_productes_procesar(conn, productes_a_procesar_df)
    actualitzar_productos(conn, productos_df)


    # OBTENIR LES VENTES D'AQUESTS CENTRES
    ventes_df = obtenir_ventes(
        conn,
        fecha_inicial_str,
        fecha_hoy_str,
        centres,
        eans_procesar_list
    )
    actualitzar_ventes(conn,ventes_df)


    # OBTENIR STOCK DELS PRODUCTES A PROCESSAR
    stock_df = obtenir_stock(
        conn,
        centres,
        codigo_interno_procesar_list
    )
    actualitzar_stocks(conn, stock_df)


    # GENERAR STOCK VENTAS CENTROS AMB LES VENTES I ELS PRODUCTES A PROCESSAR
    stock_ventas_centro_df = generar_stock_ventas_centro(conn)
    actualitzar_stock_ventas_centro(conn, stock_ventas_centro_df)

    
    # APLICAR ALGORITME RESTOCK PER TREURE MOVIMENTS
    restock(
        conn,
        exportar_movimientos=True,
        exportar_estancados=False
    )