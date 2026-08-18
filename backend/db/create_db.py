import duckdb
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"
BDD_DIR = BACKEND_DIR / "db"
BDD_DEFAULT_DATA = BDD_DIR / "default_data"
BDD_EXPORTS_DIR = BDD_DIR / "exports"

def create_db():
    conn = duckdb.connect(f"{BDD_DIR}/restock.duckdb")

    conn.execute("""
        CREATE TABLE centros (
            CODIGO_TIENDA TEXT PRIMARY KEY,
            NOMBRE_TIENDA TEXT NOT NULL,
            CLUSTER TEXT NOT NULL,
            CATEGORIA TEXT NOT NULL,
            TIENE_PERSONAL BOOLEAN NOT NULL,
            LAT TEXT,
            LON TEXT
        );
                 
        CREATE TABLE distancias (
            CODIGO_ORIGEN TEXT,
            CODIGO_DESTINO TEXT,
            DISTANCIA_MINUTOS INT
        );
                 
        CREATE TABLE productos (
            TEMPORADA TEXT,
            FAMILIA TEXT,
            CODEPRODUIT INTEGER, 
            CODECOLORIS INTEGER,
            NOMPRODUIT TEXT,
            LIBCOLORIS TEXT,
            CODEBARRES TEXT,
            CODEINTERNEARTICLE TEXT
        );
                 
        CREATE TABLE stock (
            CODEMAGASIN TEXT,                     
            NOMPRODUIT TEXT, 
            CODEINTERNEARTICLE TEXT, 
            CODEPRODUIT INTEGER,
            LIBCOLORISMODIFIE TEXT,   
            CODECOLORISSEL TEXT,                
            TAILLE TEXT ,                                
            CODEBARRES TEXT ,                                 
            DISPONIBLE INTEGER, 
            TRANSITO INTEGER, 
            PREPARACION INTEGER, 
            TOTAL INTEGER,

            PRIMARY KEY (CODEMAGASIN, CODEINTERNEARTICLE)     
        );
                 
        CREATE TABLE fotos_productos (
            EAN TEXT,
            CODEPRODUIT INTEGER,
            CODECOLORIS INTEGER,
            URL_FOTO TEXT
        );
                 
        CREATE TABLE productos_procesar (
            TEMPORADA TEXT,
            COLLECTION TEXT,
            FAMILIA TEXT, 
            CODEPRODUIT INTEGER, 
            CODECOLORIS INTEGER, 
            NOMPRODUIT TEXT,
            LIBCOLORIS TEXT,
            CODEBARRES TEXT,
            CODEINTERNEARTICLE TEXT,
            
            PRIMARY KEY(CODEPRODUIT, CODECOLORIS)
        );

        CREATE TABLE ventas (
            PAIS TEXT,
            CODIGO_TIENDA TEXT,
            NOMBRE_TIENDA TEXT,
            NUM_VENDEDOR TEXT,
            TALON TEXT,

            FECHA_HORA TEXT,
            FECHA TEXT,
            HORA INTEGER,
            MINUTO INTEGER,
            DIA_SEMANA INTEGER,
            DIA_SEMANA_NOMBRE TEXT,
            FIN_DE_SEMANA TEXT,

            CODIGO_OPERACION TEXT,

            TALON_ORIGINAL INTEGER,
            TIENDA_ORIG INTEGER,
            FECHA_HORA_ORIG TEXT,
            FECHA_ORIG TEXT,
            HORA_ORIG INTEGER,
            MINUTO_ORIG INTEGER,
            DIA_SEMANA_ORIG INTEGER,
            DIA_SEMANA_ORIG_NOMBRE TEXT,
            FIN_DE_SEMANA_ORIG TEXT,
            CODIGO_OPERACION_ORIG TEXT,

            EAN TEXT,

            VENTA_DIRECTA INTEGER,
            DEVOLUCION INTEGER,
            CONFIRMACION INTEGER,
            PEDIDO INTEGER,
            ANULACION INTEGER,

            IMPORTE REAL
        );
                 
        CREATE TABLE stock_ventas_centro (
            CODEMAGASIN        TEXT,
            CATEGORIA          TEXT,
            NOMPRODUIT         TEXT,
            LIBCOLORISMODIFIE  TEXT,

            STOCK_DISPONIBLE   INTEGER,
            STOCK_TRANSITO     INTEGER,
            STOCK_PREPARACION  INTEGER,
            STOCK_TOTAL        INTEGER,

            VENTA_4SEMANAS         INTEGER,
            VELOCIDAD_SEMANAL_REAL DOUBLE,
            VELOCIDAD_OPERATIVA    INTEGER,
            SEMANAS_ROTACION       INTEGER,

            TIENE_REPOSICION   BOOLEAN,
            PERFIL             TEXT
        );

                 
        CREATE TABLE estancados (
            CODEINTERNEARTICLE TEXT,
            CODEMAGASIN TEXT,
            QTEENSTOCK INTEGER,
            TIEMPO_ESTANCADO INTEGER
        );
                 
        CREATE TABLE movimientos (
            EMISOR TEXT,
            RECEPTOR TEXT,
                 
            NOMPRODUIT TEXT, 
            LIBCOLORIS TEXT,
                 
            CODEPRODUIT INTEGER,
            CODECOLORIS INTEGER,
                 
            STOCK_ANTES INTEGER,
            APORTE INTEGER,
            STOCK_DESPUES INTEGER,
                 
            COBERTURA_ANTES INTEGER,
            COBERTURA_DESPUES INTEGER,
            
            URL_FOTO TEXT
        );
                 
        CREATE TABLE movimientos_historico (
            SEMANA INTEGER,
            
            EMISOR TEXT,
            RECEPTOR TEXT,
                 
            NOMPRODUIT TEXT, 
            LIBCOLORIS TEXT,
                 
            CODEPRODUIT INTEGER,
            CODECOLORIS INTEGER,
                 
            STOCK_ANTES INTEGER,
            APORTE INTEGER,
            STOCK_DESPUES INTEGER,
                 
            COBERTURA_ANTES INTEGER,
            COBERTURA_DESPUES INTEGER,
            
            URL_FOTO TEXT
        );
    """)

    conn.close()

def insertar_dades():
    conn = duckdb.connect(f"{BDD_DIR}/restock.duckdb")

    fotos_productos_df = pd.read_excel(f"{BDD_DEFAULT_DATA}/url_fotos_E26.xlsx")[['EAN','Code Produit','Code Coloris','additional_image.$.url_1']]
    centros_df = pd.read_csv(f"{BDD_DEFAULT_DATA}/centros.csv",sep=";")
    distancias_df = pd.read_csv(f"{BDD_DEFAULT_DATA}/distancias.csv",sep=";")

    conn.append("fotos_productos",fotos_productos_df)
    conn.append("centros",centros_df)
    conn.append("distancias",distancias_df)

    from Storeland_BDD.get_storeland_data import run_query_to_df

    productos_df = run_query_to_df(
        f"""
            SELECT 
                p.CODESAISON,
                cp3.LIBCLASSPROD3,
                a.CODEPRODUIT, 
                a.CODECOLORIS,
                p.NOMPRODUIT,
                c.LIBCOLORIS,
                a.CODEBARRES AS EAN,
                a.CODEINTERNEARTICLE

            FROM STORELAND.ARTICLES a 
                                            
            JOIN STORELAND.PRODUITS p
                ON a.CODEPRODUIT = p.CODEPRODUIT
            
            LEFT JOIN STORELAND.COLORIS c
                ON a.CODECOLORIS = c.CODECOLORIS
            
            LEFT JOIN STORELAND.CLASSPROD3 cp3
                ON p.CODECLASSPROD3 = cp3.CODECLASSPROD3

            LEFT JOIN STORELAND.CLASSPROD2 cp2
                ON cp3.CODECLASSPROD2 = cp2.CODECLASSPROD2

            LEFT JOIN STORELAND.CLASSPROD1 cp1
                ON cp2.CODECLASSPROD1 = cp1.CODECLASSPROD1

            WHERE p.CODESAISON IN ('E23','H23','E24','H24','E25','H25','E26','H26')
        """,
        "bdd/exports/productos.csv"
    )

    conn.close()

def exportar_taules():
    conn = duckdb.connect(f"{BDD_DIR}/restock.duckdb")

    tablas = conn.execute("SHOW TABLES").fetchall()

    lista_tablas = [t[0] for t in tablas]

    for tabla in lista_tablas:
        print(f"Exportando tabla {tabla}...")
        
        results = conn.execute(f'SELECT * FROM "{tabla}"').fetchdf()
        results.to_csv(f"{BDD_EXPORTS_DIR}{tabla}.csv", sep=";", index=False)

        print(f"Exportada a '{BDD_EXPORTS_DIR}{tabla}.csv'\n")

    conn.close()

if __name__ == "__main__":
    create_db()
    insertar_dades()