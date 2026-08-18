import duckdb
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "restock.duckdb")

# -------------------- REQUESTS -------------------- #
def filtrar_productos(temporadas, colecciones, familias, colores):
    conn = get_connection()

    where = []
    params = []

    if temporadas:
        placeholders = ",".join(["?"] * len(temporadas))
        where.append(f"TEMPORADA IN ({placeholders})")
        params.extend(temporadas)

    if colecciones:
        placeholders = ",".join(["?"] * len(colecciones))
        where.append(f"COLLECTION IN ({placeholders})")
        params.extend(colecciones)

    if familias:
        placeholders = ",".join(["?"] * len(familias))
        where.append(f"FAMILIA IN ({placeholders})")
        params.extend(familias)

    if colores:
        placeholders = ",".join(["?"] * len(colores))
        where.append(f"LIBCOLORIS IN ({placeholders})")
        params.extend(colores)

    where_clause = ""
    if where:
        where_clause = "WHERE " + " AND ".join(where)

    query = f"""
        SELECT
            TEMPORADA,
            COLLECTION,
            FAMILIA,
            CODEPRODUIT, 
            CODECOLORIS,
            NOMPRODUIT,
            LIBCOLORIS,
            CODEBARRES,
            CODEINTERNEARTICLE
        FROM productos
        {where_clause}
    """

    result_df = conn.execute(query, params).fetchdf()
    conn.close()

    result = {
        "productos": result_df.to_dict(orient="records"),
        "qty":len(result_df)
    }

    #print(f"Filtro productos:\n{result}")

    return result


def filtrar_centros(clusters, categorias, personal):
    conn = get_connection()

    where = []
    params = []

    if clusters:
        placeholders = ",".join(["?"] * len(clusters))
        where.append(f"cluster IN ({placeholders})")
        params.extend(clusters)

    if categorias:
        placeholders = ",".join(["?"] * len(categorias))
        where.append(f"categoria IN ({placeholders})")
        params.extend(categorias)

    if personal:
        placeholders = ",".join(["?"] * len(personal))
        where.append(f"tiene_personal IN ({placeholders})")

        for p in personal:
            if 'No' in p:
                personal.remove('No Tiene')
                personal.append("false")
            else:
                personal.remove("Tiene")
                personal.append("true")

        params.extend(personal)

    where_clause = ""
    if where:
        where_clause = "WHERE " + " AND ".join(where)

    query = f"""
        SELECT
            codigo_tienda,
            nombre_tienda,
            cluster,
            categoria,
            tiene_personal,
            lat,
            lon,
            capacidad_total,
            capacidad_restante
        FROM centros
        {where_clause}
    """

    result_df = conn.execute(query, params).fetchdf()
    conn.close()

    result = {
        "centros": result_df.to_dict(orient="records"),
        "qty":len(result_df)
    }

    #print(f"Filtro centros:\n{result}")

    return result

# -------------------- PRODUCTOS -------------------- #
def get_connection():
    return duckdb.connect(DB_PATH)

def get_temporadas():
    conn = get_connection()

    query = "SELECT DISTINCT TEMPORADA FROM productos ORDER BY TEMPORADA"
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

def get_colecciones():
    conn = get_connection()

    query = "SELECT DISTINCT COLLECTION FROM productos ORDER BY COLLECTION"
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

def get_familias():
    conn = get_connection()

    query = "SELECT DISTINCT FAMILIA FROM productos ORDER BY FAMILIA"
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

def get_colores():
    conn = get_connection()

    query = "SELECT DISTINCT LIBCOLORIS FROM productos ORDER BY LIBCOLORIS"
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

# -------------------- CENTROS -------------------- #

def get_clusters():
    conn = get_connection()

    query = "SELECT DISTINCT cluster FROM centros ORDER BY cluster"
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

def get_categorias():
    conn = get_connection()

    query = "SELECT DISTINCT categoria FROM centros ORDER BY categoria"
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

def get_personal():
    conn = get_connection()

    query = """
    SELECT DISTINCT
        CASE
            WHEN tiene_personal THEN 'Tiene'
            ELSE 'No Tiene'
        END AS tiene_personal_texto
    FROM centros
    ORDER BY tiene_personal_texto DESC"""
    result = conn.execute(query).fetchall()

    conn.close()

    return [row[0] for row in result]

# -------------------- GENERAR MOVIMIENTOS -------------------- #