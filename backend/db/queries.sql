-- Ventas totales por tienda/EAN 
SELECT
    v.codigo_tienda,
    v.ean,
    SUM(COALESCE(v.venta_directa, 0)) AS venta_directa,
    SUM(COALESCE(v.devolucion, 0)) AS devolucion,
    SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)) AS venta_neta
FROM ventas v
GROUP BY
    v.codigo_tienda,
    v.ean
HAVING SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)) <> 0
ORDER BY
    v.codigo_tienda,
    v.ean;

-- Ventas que no encuentran match en stock
WITH ventas_4s AS (
    SELECT
        v.codigo_tienda,
        v.ean,
        SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)) AS total_ventas
    FROM ventas v
    GROUP BY
        v.codigo_tienda,
        v.ean
)
SELECT
    v.codigo_tienda,
    v.ean,
    v.total_ventas
FROM ventas_4s v
LEFT JOIN stock s
    ON s.CODEMAGASIN = v.codigo_tienda
    AND s.CODEBARRES = v.ean
WHERE s.CODEBARRES IS NULL
ORDER BY
    v.codigo_tienda,
    v.ean;


-- Comprobar posibles problemas de espacios
WITH ventas_4s AS (
    SELECT
        v.codigo_tienda,
        v.ean,
        SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)) AS total_ventas
    FROM ventas v
    GROUP BY
        v.codigo_tienda,
        v.ean
)
SELECT
    v.codigo_tienda,
    v.ean,
    s.CODEBARRES,
    v.total_ventas
FROM ventas_4s v
LEFT JOIN stock s
    ON TRIM(s.CODEMAGASIN) = TRIM(v.codigo_tienda)
    AND TRIM(s.CODEBARRES) = TRIM(v.ean)
WHERE s.CODEBARRES IS NOT NULL;

--------------------------------------------------------------------------------------------------

WITH ventas_4s AS (
            SELECT
                v.codigo_tienda,
                v.ean,
                GREATEST(SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)), 0) AS total_ventas_brutas
            FROM ventas v
            GROUP BY
                v.codigo_tienda,
                v.ean
        )
        SELECT
            s.CODEMAGASIN,
            c.categoria,
            s.NOMPRODUIT,
            s.LIBCOLORISMODIFIE,
                                          
            SUM(COALESCE(s.DISPONIBLE, 0)) AS stock_disponible,
            SUM(COALESCE(s.TRANSITO, 0)) AS stock_transito,
            SUM(COALESCE(s.PREPARACION, 0)) AS stock_preparacion,
            SUM(COALESCE(s.TOTAL, 0)) AS stock_total,

            CAST(SUM(COALESCE(v.total_ventas_brutas, 0)) AS INTEGER) AS venta_4semanas,
            
            SUM(COALESCE(v.total_ventas_brutas, 0)) / 4.0 AS velocidad_semanal_real,

            -- Velocidad semanal operativa
            CASE 
                WHEN venta_4semanas = 0
                THEN 0

                WHEN velocidad_semanal_real < 1
                THEN 1 

                ELSE ROUND(velocidad_semanal_real) 
            END AS velocidad_operativa, 

            -- Semanas de Rotación (Cobertura)
            -- Si no hay ventas, ponemos un valor alto (999) para indicar stock parado
            CASE
                WHEN stock_total = 0 THEN 0 
                WHEN venta_4semanas = 0 THEN 999
                WHEN velocidad_operativa = 0 THEN 999
                ELSE ROUND(stock_total / velocidad_operativa)
            END AS semanas_rotacion,

            CASE 
                WHEN SUM(COALESCE(s.TRANSITO, 0)) + SUM(COALESCE(s.PREPARACION, 0)) > 0 THEN TRUE
                ELSE FALSE
            END AS tiene_reposicion,

            CASE
                WHEN venta_4semanas = 0 -- No ha vendido en 4 semanas
                    AND stock_disponible > 0 -- Tiene stock en tienda
                    AND tiene_reposicion = FALSE -- No tendra reposicion
                THEN 'EMISOR'

                WHEN venta_4semanas > 0 -- Ha vendido alguna prenda
                    AND semanas_rotacion < 10 -- Semanas de rotación inferior a 10
                THEN 'RECEPTOR'

                ELSE 'NEUTRO'
            END AS perfil
        
        FROM stock s
        JOIN centros c 
            ON s.CODEMAGASIN = c.codigo_tienda
        LEFT JOIN ventas_4s v
            ON s.CODEMAGASIN = v.codigo_tienda
            AND s.CODEBARRES = v.ean
                                          
        WHERE (s.NOMPRODUIT,s.LIBCOLORISMODIFIE) IN (SELECT NOMPRODUIT, LIBCOLORISMODIFIE FROM productos_procesar)
                                          
        GROUP BY
            s.CODEMAGASIN,
            c.categoria,
            s.NOMPRODUIT,
            s.LIBCOLORISMODIFIE
                                          
        HAVING (SUM(COALESCE(s.TOTAL, 0)) > 0 OR CAST(SUM(COALESCE(v.total_ventas_brutas, 0)) AS INTEGER) > 0)
                                          
        ORDER BY
            s.CODEMAGASIN,
            s.NOMPRODUIT;
--------------------------------------------------------------------------------------------------

CREATE OR REPLACE VIEW "main"."test_stock_ventas_centros" AS
WITH ventas_4s_ean AS (
    SELECT
        v.codigo_tienda,
        v.ean,
        GREATEST(
            SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)),
            0
        ) AS total_ventas_brutas
    FROM ventas v
    GROUP BY
        v.codigo_tienda,
        v.ean
),

mapa_producto AS (
    SELECT DISTINCT
        s.CODEBARRES AS ean,
        s.NOMPRODUIT,
        s.LIBCOLORISMODIFIE
    FROM stock s
    WHERE s.CODEBARRES IS NOT NULL
),

ventas_4s_producto AS (
    SELECT
        v.codigo_tienda,
        mp.NOMPRODUIT,
        mp.LIBCOLORISMODIFIE,
        SUM(v.total_ventas_brutas) AS total_ventas_brutas
    FROM ventas_4s_ean v
    JOIN mapa_producto mp
        ON v.ean = mp.ean
    GROUP BY
        v.codigo_tienda,
        mp.NOMPRODUIT,
        mp.LIBCOLORISMODIFIE
),

stock_producto AS (
    SELECT
        s.CODEMAGASIN,
        s.NOMPRODUIT,
        s.LIBCOLORISMODIFIE,

        SUM(COALESCE(s.DISPONIBLE, 0)) AS stock_disponible,
        SUM(COALESCE(s.TRANSITO, 0)) AS stock_transito,
        SUM(COALESCE(s.PREPARACION, 0)) AS stock_preparacion,
        SUM(COALESCE(s.TOTAL, 0)) AS stock_total
    FROM stock s
    GROUP BY
        s.CODEMAGASIN,
        s.NOMPRODUIT,
        s.LIBCOLORISMODIFIE
),

base AS (
    SELECT
        COALESCE(s.CODEMAGASIN, v.codigo_tienda) AS CODEMAGASIN,
        COALESCE(s.NOMPRODUIT, v.NOMPRODUIT) AS NOMPRODUIT,
        COALESCE(s.LIBCOLORISMODIFIE, v.LIBCOLORISMODIFIE) AS LIBCOLORISMODIFIE,

        COALESCE(s.stock_disponible, 0) AS stock_disponible,
        COALESCE(s.stock_transito, 0) AS stock_transito,
        COALESCE(s.stock_preparacion, 0) AS stock_preparacion,
        COALESCE(s.stock_total, 0) AS stock_total,

        CAST(COALESCE(v.total_ventas_brutas, 0) AS INTEGER) AS venta_4semanas
    FROM stock_producto s
    FULL OUTER JOIN ventas_4s_producto v
        ON s.CODEMAGASIN = v.codigo_tienda
        AND s.NOMPRODUIT = v.NOMPRODUIT
        AND s.LIBCOLORISMODIFIE = v.LIBCOLORISMODIFIE
),

base_filtrada AS (
    SELECT
        b.*
    FROM base b
    JOIN productos_procesar p
        ON b.NOMPRODUIT = p.NOMPRODUIT
        AND b.LIBCOLORISMODIFIE = p.LIBCOLORISMODIFIE
),

calculo_1 AS (
    SELECT
        b.CODEMAGASIN,
        c.categoria,
        b.NOMPRODUIT,
        b.LIBCOLORISMODIFIE,

        b.stock_disponible,
        b.stock_transito,
        b.stock_preparacion,
        b.stock_total,

        b.venta_4semanas,

        b.venta_4semanas / 4.0 AS velocidad_semanal_real,

        CASE 
            WHEN b.venta_4semanas = 0 THEN 0
            WHEN b.venta_4semanas / 4.0 < 1 THEN 1
            ELSE CAST(ROUND(b.venta_4semanas / 4.0) AS INTEGER)
        END AS velocidad_operativa,

        CASE 
            WHEN b.stock_transito + b.stock_preparacion > 0 THEN TRUE
            ELSE FALSE
        END AS tiene_reposicion
    FROM base_filtrada b
    JOIN centros c
        ON b.CODEMAGASIN = c.codigo_tienda
    WHERE b.stock_total > 0
       OR b.venta_4semanas > 0
),

calculo_2 AS (
    SELECT
        c1.*,

        CASE
            WHEN c1.stock_total = 0 THEN 0
            WHEN c1.venta_4semanas = 0 THEN 999
            WHEN c1.velocidad_operativa = 0 THEN 999
            ELSE CAST(ROUND(c1.stock_total / c1.velocidad_operativa) AS INTEGER)
        END AS semanas_rotacion
    FROM calculo_1 c1
)

SELECT
    c2.CODEMAGASIN,
    c2.categoria,
    c2.NOMPRODUIT,
    c2.LIBCOLORISMODIFIE,

    c2.stock_disponible,
    c2.stock_transito,
    c2.stock_preparacion,
    c2.stock_total,

    c2.venta_4semanas,
    c2.velocidad_semanal_real,
    c2.velocidad_operativa,
    c2.semanas_rotacion,

    c2.tiene_reposicion,

    CASE
        WHEN c2.venta_4semanas = 0
            AND c2.stock_disponible > 0
            AND c2.tiene_reposicion = FALSE
        THEN 'EMISOR'

        WHEN c2.venta_4semanas > 0
            AND c2.semanas_rotacion < 10
        THEN 'RECEPTOR'

        ELSE 'NEUTRO'
    END AS perfil

FROM calculo_2 c2

WHERE c2.CODEMAGASIN IN (801,803,805,806,832,840,845,857,869,1782,1933,2020,2094)

ORDER BY
    c2.CODEMAGASIN,
    c2.NOMPRODUIT,
    c2.LIBCOLORISMODIFIE;

----------------------------------------------------------------------------

-- VENTAS QUE NO SURTEN A STOCK VENTAS CENTROS
WITH ventas_4s_ean AS (
    SELECT
        v.codigo_tienda,
        v.ean,
        SUM(COALESCE(v.venta_directa, 0) + COALESCE(v.devolucion, 0)) AS total_ventas
    FROM ventas v
    GROUP BY
        v.codigo_tienda,
        v.ean
),

mapa_producto AS (
    SELECT DISTINCT
        s.CODEBARRES AS ean,
        s.NOMPRODUIT,
        s.LIBCOLORISMODIFIE
    FROM stock s
    WHERE s.CODEBARRES IS NOT NULL
),

ventas_producto AS (
    SELECT
        v.codigo_tienda,
        v.ean,
        mp.NOMPRODUIT,
        mp.LIBCOLORISMODIFIE,
        v.total_ventas
    FROM ventas_4s_ean v
    JOIN mapa_producto mp
        ON v.ean = mp.ean
    WHERE v.total_ventas <> 0
),

ventas_en_productos_procesar AS (
    SELECT
        vp.codigo_tienda,
        vp.ean,
        vp.NOMPRODUIT,
        vp.LIBCOLORISMODIFIE,
        vp.total_ventas
    FROM ventas_producto vp
    JOIN productos_procesar p
        ON vp.NOMPRODUIT = p.NOMPRODUIT
        AND vp.LIBCOLORISMODIFIE = p.LIBCOLORISMODIFIE
)

SELECT
    vpp.codigo_tienda,
    vpp.ean,
    vpp.NOMPRODUIT,
    vpp.LIBCOLORISMODIFIE,
    vpp.total_ventas
FROM ventas_en_productos_procesar vpp
LEFT JOIN test_stock_ventas_centros svc
    ON vpp.codigo_tienda = svc.CODEMAGASIN
    AND vpp.NOMPRODUIT = svc.NOMPRODUIT
    AND vpp.LIBCOLORISMODIFIE = svc.LIBCOLORISMODIFIE
WHERE svc.CODEMAGASIN IS NULL
ORDER BY
    vpp.codigo_tienda,
    vpp.NOMPRODUIT,
    vpp.LIBCOLORISMODIFIE,
    vpp.ean;
-------------------------------------------------------------------
SELECT *
FROM stock
WHERE NOMPRODUIT = '241-DAGA' AND LIBCOLORISMODIFIE = 'PALE BANANA' AND CODEMAGASIN = 1782;

SELECT *
FROM ventas
WHERE ean IN (
    SELECT DISTINCT CODEBARRES
    FROM stock
    WHERE NOMPRODUIT = '241-DAGA' AND LIBCOLORISMODIFIE = 'PALE BANANA'
) AND codigo_tienda = 1782;




----------------------------------------------------------------------------------------------------
-- TREURE LLISTAT DE COLORS QUE TENEN MES D'UN CODI DE COLOR
SELECT color
    FROM read_csv('../Datos Ibérica-RESTOCK - Documents/resultados/movimientos_2026-06-08.csv')
    GROUP BY color
    HAVING count(distinct codigo_color) > 1;

-- VEURE ELS COLORS QUE TENEN MES DE UNA ID A MOVIMIENTOS
SELECT DISTINCT color, codigo_color
FROM read_csv('../Datos Ibérica-RESTOCK - Documents/resultados/movimientos_2026-06-08.csv')
WHERE color in (
    SELECT color
    FROM read_csv('../Datos Ibérica-RESTOCK - Documents/resultados/movimientos_2026-06-08.csv')
    GROUP BY color
    HAVING count(distinct codigo_color) > 1
)
ORDER BY color; 

ALTER TABLE productos
RENAME COLUMN LIBCOLORISMODIFIE TO LIBCOLORIS;
