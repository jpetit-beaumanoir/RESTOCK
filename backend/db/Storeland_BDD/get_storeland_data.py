import os
import re
import glob
import ctypes
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
import  time
import pandas as pd
import duckdb


# ==========================
# Configuración de rutas
# ==========================
BASE_DIR = Path(__file__).resolve().parent

DEP_DIR = BASE_DIR / "Dependencies"
LIB_DIR = DEP_DIR / "lib"
SQLWB_DIR = LIB_DIR / "sql-workbench"
OJDBC_DIR = LIB_DIR / "oracle-jdbc"
CRED_DIR = DEP_DIR  # SET-PARAMS_XXX.cmd en Dependencies\

JAVA_EXE = r"C:\Program Files (x86)\Common Files\Oracle\Java\java8path\java.exe"
JAVA_ENCODING = "CP850"
DEFAULT_TIMEOUT = 120


# ==========================
# Utilidades
# ==========================
def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def find_first(pattern: str) -> Optional[str]:
    hits = glob.glob(pattern)
    return hits[0] if hits else None


def get_short_path_existing(path: str) -> str:
    """Devuelve 8.3 sólo si el path existe (archivo o carpeta)."""
    abspath = os.path.abspath(path)
    buf = ctypes.create_unicode_buffer(32768)
    res = ctypes.windll.kernel32.GetShortPathNameW(abspath, buf, len(buf))
    
    # Si res=0 => no hay short path (no existe o no disponible)
    return buf.value if res else abspath


def short_path_for_output_file(path: str) -> str:
    """
    Devuelve una ruta 8.3 válida para un fichero de salida aunque NO exista aún.
    Convierte el directorio padre (que existe o lo creamos) y añade el filename.
    """
    abspath = os.path.abspath(path)
    parent = os.path.dirname(abspath)
    leaf = os.path.basename(abspath)

    # Asegura que el directorio padre existe
    os.makedirs(parent, exist_ok=True)

    parent_short = get_short_path_existing(parent)
    return os.path.join(parent_short, leaf)



def get_short_path(path: str) -> str:
    """
    Convierte a ruta corta 8.3 en Windows.
    Si falla, devuelve la ruta original.
    """
    try:
        abspath = os.path.abspath(path)
        buf = ctypes.create_unicode_buffer(32768)
        res = ctypes.windll.kernel32.GetShortPathNameW(abspath, buf, len(buf))
        return buf.value if res else abspath
    except Exception:
        return path


def needs_short_path(path: str) -> bool:
    """
    En tu caso el problema es especialmente el patrón ' espacio + - '.
    También vale cualquier espacio en general si el parser es agresivo.
    """
    return (" - " in path) or (" " in path)


def safe_path(path: str) -> str:
    """
    Devuelve ruta corta 8.3 si hace falta.
    """
    p = str(path)
    return get_short_path(p) if needs_short_path(p) else p


def ensure_sql_script(sql_body: str) -> str:
    """
    Genera script robusto:
      - WbFeedback quiet OFF;
      - asegura ';' al final
      - añade EXIT; para terminar el proceso
    """
    sql = sql_body.strip()
    if not sql.endswith(";"):
        sql += ";"
    return "WbFeedback quiet OFF;\n" + sql + "\nEXIT;\n"


def sanitize_cmd_for_log(cmd_list) -> str:
    safe = []
    for a in cmd_list:
        if isinstance(a, str) and a.lower().startswith("-password="):
            safe.append("-password=***")
        else:
            safe.append(a)
    return " ".join(f'"{x}"' if (" " in x) else x for x in safe)


# ==========================
# Credenciales
# ==========================
def get_credentials(brand_code: str) -> Optional[Dict[str, str]]:
    cmd_file = CRED_DIR / f"SET-PARAMS_{brand_code}.cmd"
    if not cmd_file.exists():
        return None

    content = cmd_file.read_text(encoding="utf-8", errors="ignore")

    creds = {}
    for var in ["ORACLE_HOST", "ORACLE_PORT", "ORACLE_SRVC", "ORACLE_USER", "ORACLE_PASS"]:
        m = re.search(rf"(?im)^\s*set\s+{re.escape(var)}\s*=\s*(.+?)\s*$", content)
        if m:
            creds[var] = _strip_quotes(m.group(1).strip())

    required = {"ORACLE_HOST", "ORACLE_PORT", "ORACLE_SRVC", "ORACLE_USER", "ORACLE_PASS"}
    if not required.issubset(creds.keys()):
        return None

    return creds


def build_jdbc_url(creds: Dict[str, str]) -> str:
    return f"jdbc:oracle:thin:@{creds['ORACLE_HOST']}:{creds['ORACLE_PORT']}/{creds['ORACLE_SRVC']}"


# ==========================
# Resolución de dependencias
# ==========================
def resolve_dependencies() -> Tuple[str, str]:
    sqlwb_jar = find_first(str(SQLWB_DIR / "sqlworkbench*.jar")) or str(SQLWB_DIR / "sqlworkbench.jar")
    ojdbc_jar = find_first(str(OJDBC_DIR / "ojdbc*.jar")) or str(OJDBC_DIR / "ojdbc6.jar")

    if not Path(sqlwb_jar).exists():
        raise FileNotFoundError(f"No encuentro sqlworkbench.jar en: {SQLWB_DIR}")

    if not Path(ojdbc_jar).exists():
        raise FileNotFoundError(f"No encuentro ojdbc*.jar en: {OJDBC_DIR}")

    # 👇 clave: convertir a 8.3 si la ruta tiene espacios / ' - '
    return safe_path(sqlwb_jar), safe_path(ojdbc_jar)


# ==========================
# Ejecución (csv)
# ==========================
def run_query_to_df(
    sql: str,
    csv_path: str,
    save_file: bool = True,
    brand_code: str = "MGN",
    delimiter: str = ";",
    header: bool = True,
    quotechar: str = '"',
    timeout: int = 600, # 10 minutos
    verbose: bool = False
) -> pd.DataFrame:
    """
    Ejecuta una consulta y exporta el resultado a CSV usando WbExport.
    Devuelve la ruta del CSV si todo va bien, o lanza excepción con detalles.
    """

    creds = get_credentials(brand_code)
    if not creds:
        raise RuntimeError(f"Credenciales no encontradas para {brand_code}")

    url = build_jdbc_url(creds)
    sqlwb_jar, ojdbc_jar = resolve_dependencies()  # ya devuelve paths "safe" (8.3 si hace falta)

    # Normaliza y asegura ';'
    sql_clean = sql.strip()
    if not sql_clean.endswith(";"):
        sql_clean += ";"

    # CSV absoluto (y si tiene ' - ' o espacios, lo pasamos a 8.3 también)
    csv_abs = str(Path(csv_path).resolve())
    csv_abs_safe = short_path_for_output_file(csv_abs)

    # print(f"csv_abs: {csv_abs}")
    # print(f"csv_abs_safe: {csv_abs_safe}")

    hdr = "true" if header else "false"

    # Script de exportación (incluye EXIT para terminar siempre)
    export_script = (
        "WbFeedback quiet OFF;\n"
        f"WbExport -file='{csv_abs_safe}' -type=text -delimiter='{delimiter}' "
        f"-header={hdr} -quoteChar='{quotechar}';\n"
        f"{sql_clean}\n"
        "EXIT;\n"
    )

    script_file = BASE_DIR / "temp_export.sql"
    script_file.write_text(export_script, encoding="cp850", errors="replace")
    script_safe = safe_path(str(script_file))

    cmd = [
        JAVA_EXE,
        "-Xmx256m",
        f"-Dfile.encoding={JAVA_ENCODING}",
        "-jar", sqlwb_jar,
        f"-url={url}",
        f"-username={creds['ORACLE_USER']}",
        f"-password={creds['ORACLE_PASS']}",
        "-driver=oracle.jdbc.OracleDriver",
        f"-driverJar={ojdbc_jar}",
        f"-script={script_safe}",
        "-feedback=false",
        "-showProgress=false",
        "-displayResult=false",
    ]

    # Ejecutar (DEVNULL + timeout para evitar cuelgues)
    try:
        initial_time = time.time()

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False
        )

        final_time = time.time()

        if verbose:
            print(f"Query executada en {round(final_time - initial_time,2)} segons")

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout tras {timeout}s ejecutando export. Comando: {sanitize_cmd_for_log(cmd)}")

    if result.returncode != 0:
        raise RuntimeError(
            f"Error exportando CSV (ExitCode={result.returncode}).\n"
            f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n"
        )
    
    if verbose:
        print(f"\nResultat:\n\t{result}")

    # Validación básica de que existe el fichero
    if not Path(csv_abs).exists():
        # Si usaste 8.3 para el path, el fichero existe igual en la ruta larga.
        raise RuntimeError(f"El proceso terminó OK pero no encuentro el CSV en: {csv_abs}")

    df = pd.read_csv(csv_abs, sep=";", encoding="cp850")

    if not save_file:
        Path(csv_abs).unlink()

    return df

# CODEMAGASIN IN (801,803,805,806,832,840,845,857,869,1782,1933,2020,2094)

# ==========================
# Ejemplo
# ==========================
if __name__ == "__main__":
    pass
    # csv_file = run_query_to_df(
    #     sql="""
    #         SELECT CODEBARRES
    #         FROM STORELAND.ARTICLES
    #         WHERE CODEINTERNEARTICLE IN (SELECT CODEINTERNEARTICLE FROM STORELAND.STOCKS_ARTICLES_MAGASINS WHERE CODEMAGASIN = 935)
    #     """,
    #     csv_path="test.csv",
    #     brand_code="MGN",
    #     delimiter=";"
    # )
    # print("CSV generado:", csv_file)
    # csv_file.to_csv("stock_fabra")