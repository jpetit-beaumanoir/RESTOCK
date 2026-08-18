from django.shortcuts import render
from django.http import JsonResponse
from pathlib import Path
import sys
import json
import pandas as pd

# añadir backend al path
BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = BASE_DIR / "backend"
LOGS_DIR = BACKEND_DIR / "logs"
BDD_DIR = BACKEND_DIR / "db"
BDD_EXPORTS_DIR = BDD_DIR / "exports"
PALMARES_DIR = BACKEND_DIR / "palmares"
RESULTADOS_DIR = BASE_DIR / "resultados"
HISTORIAL_RESULTADOS_DIR = RESULTADOS_DIR / "historial"
sys.path.append(str(BASE_DIR))

from backend.db.db_api import get_temporadas, get_colecciones, get_familias, get_colores, get_categorias, get_personal, get_clusters

def home(request):
    
    #productos = get_productos()
    temporadas = get_temporadas()
    colecciones = get_colecciones()
    familias = get_familias()
    colores = get_colores()

    #centros = get_centros()
    clusters = get_clusters()
    categorias = get_categorias()
    tipos_personal = get_personal()

    return render(request, 'core/home.html', {
        'temporadas': temporadas,
        'colecciones': colecciones,
        'familias': familias,
        'colores': colores,

        'clusters': clusters,
        'categorias': categorias,
        'tipos_personal': tipos_personal
    })

def filtrar(request):
    filtros = json.loads(request.body)

    temporadas = filtros.get("temporadas", [])
    colecciones = filtros.get("colecciones", [])
    familias = filtros.get("familias", [])
    colores = filtros.get("colores", [])

    clusters = filtros.get("clusters", [])
    categorias = filtros.get("categorias", [])
    personal = filtros.get("personal", [])

    from backend.db.db_api import filtrar_productos, filtrar_centros

    productos_filtrados = filtrar_productos(temporadas, colecciones, familias, colores)
    centros_filtrados = filtrar_centros(clusters, categorias, personal)

    resultado = {
        "productos_filtrados": productos_filtrados['productos'],
        "centros_filtrados": centros_filtrados['centros'],
        "productos": f"{productos_filtrados['qty']} Productos",
        "centros": f"{centros_filtrados['qty']} Centros"
    }

    return JsonResponse(resultado)

def movimientos(request):
    try:
        body = json.loads(request.body)

        parametros = body['parametros']
        productos = pd.DataFrame(body['productos'])
        centros = pd.DataFrame(body['centros'])

        cobertura_maxima = int(parametros['cobertura_maxima']) 
        cubrimiento_tallas = float(parametros['cubrimiento_tallas']) / 100
        productos_maximos = int(parametros['productos_maximos'])

        from main import ejecutar_restock

        resultado = ejecutar_restock(
            productos,
            centros,
            cobertura_maxima,
            cubrimiento_tallas,
            productos_maximos
        )

        print(JsonResponse(resultado))

        return JsonResponse(resultado)
    
    except Exception as e:
        print("ERROR MOVIMIENTOS:", e)
        return JsonResponse({
            "error": str(e)
        }, status=500)
