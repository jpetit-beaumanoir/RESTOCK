import pandas as pd
import os
import random
import glob

def mails_productos_enviar():

    # Buscar archivos .xlsx dentro de la carpeta
    files = glob.glob(os.path.join("resultados", "*.xlsx"))

    # Tomar el primero encontrado
    if files:
        excel_path = files[0]
    else:
        raise FileNotFoundError("No se encontró ningún archivo .xlsx en la carpeta 'resultados'")


    # Carpeta de salida
    output_dir = "resultados/a_enviar"
    os.makedirs(output_dir, exist_ok=True)   


    # Leer el Excel completo
    xls = pd.ExcelFile(excel_path)

    # Iterar por cada hoja (cada emisor)
    for sheet_name in xls.sheet_names:

        df = pd.read_excel(xls, sheet_name=sheet_name)

        html_intro = f"""
            <div class="intro">
                <p>
                    <strong>Traspasos a realizar para optimizar la venta.</strong><br><br>

                    Se ha detectado que estos productos no han tenido una buena salida en este centro y se ha recomendado su traspaso.<br><br>

                    1. Entra a <strong>RemBo</strong> y genera un nuevo traspaso con el centro que marca en el campo <strong>'Destino'</strong>.<br>
                    2. Escanea todas las referencias que tengas en el centro de la prenda marcada, no solo una unidad.
                </p>
            </div>
        """

        html_content = ""

        for receptor, grupo in df.groupby('receptor'):

            html_content += f"""
            <div class="card">
                <p class="receptor">Destino: <span>{receptor} - {grupo['nombre_receptor'].iloc[0]}</span></p>
                <ul>
            """

            # recorrer los productos dentro de ese receptor
            for _, row in grupo.iterrows():

                
                if pd.notna(row['url_foto']) and row['url_foto'] != '#':
                    boton_foto = f"""
                        <a href="{row['url_foto']}" target="_blank" class="btn">Foto</a>
                    """
                else:
                    boton_foto = """
                        <button class="btn" style="background-color: gray; color:white;"
                                disabled title="Sin foto disponible">
                            Sin foto
                        </button>
                    """


                html_content += f"""
                    <li>
                        <strong>Producto:</strong> {row['producto']} 
                        <span class="codigo">({row['codigo_producto']})</span><br>

                        <strong>Color:</strong> {row['color']} 
                        <span class="codigo">({row['codigo_color']})</span><br>

                        <strong>Tallas:</strong> {row['tallas']}<br>

                        {boton_foto}
                    </li>
                """

            html_content += """
                </ul>
            </div>
            """



        # HTML completo
        html_final = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }}

                .intro {{
                    margin-bottom: 30px;
                    padding: 18px;
                    background-color: #f4f6f8;
                    border-left: 5px solid #0078D4;
                    border-radius: 8px;
                    font-size: 14px;
                    color: #333;
                    line-height: 1.5;
                }}


                .card {{
                    background: white;
                    border-radius: 10px;
                    padding: 15px 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                }}

                .receptor {{
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    color: #2c3e50;
                }}

                .receptor span {{
                    color: #0078D4;
                }}

                ul {{
                    list-style: none;
                    padding-left: 0;
                }}

                li {{
                    margin-bottom: 8px;
                    font-size: 14px;
                }}

                .codigo {{
                    color: #7f8c8d;
                    font-size: 13px;
                }}

                .btn {{
                    display: inline-block;
                    padding: 6px 10px;
                    margin-top: 5px;
                    margin-bottom: 15px;
                    background-color: #0078D4;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 13px;
                }}

                .btn:hover {{
                    background-color: #005a9e;
                }}
            </style>
        </head>

        <body>
            {html_intro}
            {html_content}
        </body>

        </html>
        """

        # Guardar archivo con nombre de la hoja (emisor)
        file_path = os.path.join(output_dir, f"{sheet_name}.html")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_final)


def mails_productos_recibir():
    # Buscar archivos .xlsx dentro de la carpeta
    files = glob.glob(os.path.join("resultados", "*.csv"))

    # Tomar el primero encontrado
    if files:
        csv_file = files[0]
        df = pd.read_csv(csv_file, sep=";")
    else:
        raise FileNotFoundError("No se encontró ningún archivo .xlsx en la carpeta 'resultados'")

    # Carpeta salida
    output_dir_rec = "resultados/a_recibir"
    os.makedirs(output_dir_rec, exist_ok=True)

    # Agrupar por receptor (cada uno tendrá su email)
    for receptor, df_receptor in df.groupby('receptor'):

        total_refs = len(df_receptor)
        total_unidades = int(df_receptor['aporte'].sum())

        html_intro = f"""
            <div class="intro">
                <p>
                    <strong>Productos que vas a recibir.</strong><br><br>

                    
                    Vas a recibir <strong>{total_refs} referencias</strong> con un total de <strong>{total_unidades} unidades.</strong><br><br>

                    1. Revisa los productos que vas a recibir.<br>
                    2. Valida el traspaso cuando llegue a tienda.<br><br>

                    Estos artículos serán enviados próximamente a tu centro para optimizar el stock.
                </p>
            </div>
        """

        html_content = ""

        # Agrupar por emisor (quién lo manda)
        for emisor, grupo in df_receptor.groupby('emisor'):

            html_content += f"""
            <div class="card">
                <p class="receptor">
                    Origen: <span>{emisor} - {grupo['nombre_emisor'].iloc[0]}</span>
                </p>
                <ul>
            """

            for _, row in grupo.iterrows():

                if pd.notna(row['url_foto']) and row['url_foto'] != '#':
                    boton_foto = f'<a href="{row["url_foto"]}" target="_blank" class="btn">Foto</a>'
                else:
                    boton_foto = """
                        <button class="btn" style="background-color: gray;" disabled>
                            Sin foto
                        </button>
                    """

                html_content += f"""
                    <li>
                        <strong>Producto:</strong> {row['producto']} 
                        <span class="codigo">({row['codigo_producto']})</span><br>

                        <strong>Color:</strong> {row['color']} 
                        <span class="codigo">({row['codigo_color']})</span><br>

                        <strong>Tallas:</strong> {row['tallas']}<br>

                        <strong>Aporte:</strong> {int(row['aporte'])} uds<br>

                        <strong>Stock tras recepción:</strong> {int(row['stock_despues'])}<br>

                        {boton_foto}
                    </li>
                """

            html_content += """
                </ul>
            </div>
            """

        # HTML final
        html_final = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; padding: 20px; }}

                .intro {{
                    margin-bottom: 30px;
                    padding: 18px;
                    background-color: #e8f5e9;
                    border-left: 5px solid #28a745;
                    border-radius: 8px;
                }}

                .card {{
                    background: white;
                    border-radius: 10px;
                    padding: 15px 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                }}

                .receptor {{
                    font-weight: bold;
                    margin-bottom: 10px;
                }}

                .receptor span {{ color: #28a745; }}

                ul {{ list-style: none; padding-left: 0; }}

                li {{ margin-bottom: 10px; }}

                .codigo {{ color: #777; font-size: 13px; }}

                .btn {{
                    display: inline-block;
                    margin-top: 5px;
                    padding: 6px 10px;
                    background-color: #28a745;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }}
            </style>
        </head>

        <body>
            {html_intro}
            {html_content}
        </body>
        </html>
        """

        # Nombre archivo con código + nombre tienda
        nombre = df_receptor['nombre_receptor'].iloc[0]
        file_path = os.path.join(output_dir_rec, f"{receptor}.html")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_final)

if __name__ == "__main__":
    mails_productos_enviar()
    mails_productos_recibir()