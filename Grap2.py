import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Archivo a leer
CSV_FILE = "Prueba_4.csv"


def analizar():
    try:
        print(f"Leyendo {CSV_FILE}...")
        df = pd.read_csv(CSV_FILE)
        
        # Convertir texto a fecha real
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        
        # Configurar gráfica
        plt.figure(figsize=(14, 7))
        
        # Graficar el Índice de Alteración
        plt.plot(df['Timestamp'], df['Indice_Alteracion'], 
                 color='#d62728', linewidth=2, label='Índice de Alteración (Global)')
        
        # (Opcional) Graficar canales específicos para ver detalles
        # Por ejemplo, el canal UV (410nm) suele reaccionar a detergentes
        if '410' in df.columns:
             # Normalizamos dividiendo por el máximo para que quepa en la gráfica
             max_uv = df['410'].max()
             plt.plot(df['Timestamp'], df['410'] * (df['Indice_Alteracion'].max() / max_uv), 
                      color='blue', alpha=0.3, label='Canal UV (Escalado)')

        # Formato de la gráfica
        plt.title('Historial de Contaminación en Tubería', fontsize=16)
        plt.ylabel('Nivel de Alteración (Desviación)', fontsize=12)
        plt.xlabel('Tiempo', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Formato de hora en el eje X
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.gcf().autofmt_xdate() # Rotar fechas
        
        # Línea de umbral de peligro
        plt.axhline(y=15, color='orange', linestyle=':', label='Umbral de Alerta')
        
        plt.legend()
        plt.tight_layout()
        plt.show()
        
    except FileNotFoundError:
        print("No se encontró el archivo CSV. Ejecuta primero el monitor.")
    except Exception as e:
        print(f"Error analizando datos: {e}")

if __name__ == "__main__":
    analizar()