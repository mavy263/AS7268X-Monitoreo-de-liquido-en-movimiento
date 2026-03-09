import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import csv
from datetime import datetime
import os
import numpy as np
from collections import deque

# --- CONFIGURACIÓN ---
# En Linux suele ser /dev/ttyUSB0 o /dev/ttyACM0.
# Ejecuta 'ls /dev/ttyUSB*' en la terminal para confirmar.
PUERTO = 'COM3' 
BAUDIOS = 115200
NUM_CANALES = 18
CSV_NAME = "datos_tuberia.csv"
VENTANA_SUAVIZADO = 5  # Promediará las últimas 5 lecturas (filtro de burbujas)

# Nombres de las longitudes de onda del AS7265x
labels = ['410', '435', '460', '485', '510', '535', '560', '585', '610', 
          '645', '705', '760', '610b', '680', '730', '760b', '810', '860']

# Variables globales
referencia = np.zeros(NUM_CANALES)
# Buffer para el suavizado (filtro de media móvil)
buffer_lecturas = deque(maxlen=VENTANA_SUAVIZADO)
datos_suavizados = np.zeros(NUM_CANALES)

# Inicializar archivo CSV si no existe
if not os.path.exists(CSV_NAME):
    with open(CSV_NAME, 'w', newline='') as f:
        writer = csv.writer(f)
        header = ['Timestamp'] + labels + ['Indice_Alteracion']
        writer.writerow(header)

# Conexión Serial
try:
    ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)
    ser.flushInput()
    print(f"--- CONECTADO AL SENSOR EN {PUERTO} ---")
    print("Presiona 'R' para calibrar con agua limpia.")
except Exception as e:
    print(f"ERROR DE CONEXIÓN: {e}")
    print(f"Tips para Linux: \n1. Revisa si es ttyUSB0 o ttyACM0.\n2. ¿Usaste 'sudo chmod 666 {PUERTO}'?")
    exit()

# Configuración de Gráficas
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))
plt.subplots_adjust(hspace=0.4)

# Panel 1: Espectro Absoluto
bar_actual = ax1.bar(labels, [0]*NUM_CANALES, color='#007acc', alpha=0.8, label='Lectura Actual (Suavizada)')
bar_ref = ax1.bar(labels, [0]*NUM_CANALES, color='gray', alpha=0.3, label='Referencia (Agua Limpia)')
text_info = ax1.text(0.02, 0.90, 'Esperando datos...', transform=ax1.transAxes, fontsize=10)
ax1.set_title("Espectro de Luz (Tiempo Real)")
ax1.set_ylim(0, 1000) # Ajusta esto según la potencia de tus LEDs
ax1.legend()

# Panel 2: Diferencia (Alteración)
bar_diff = ax2.bar(labels, [0]*NUM_CANALES, color='salmon')
ax2.set_title("Desviación por Canal (Detectando Contaminantes)")
ax2.axhline(0, color='black', linewidth=0.8)
text_indice = ax2.text(0.95, 0.90, 'Índice: 0.0', transform=ax2.transAxes, ha='right', fontsize=14, fontweight='bold')

def on_key(event):
    global referencia
    if event.key.lower() == 'r':
        # Guardamos el promedio actual como la "verdad absoluta" del agua limpia
        referencia = np.array(datos_suavizados)
        print(f">>> CALIBRADO: Referencia establecida a las {datetime.now().strftime('%H:%M:%S')}")

fig.canvas.mpl_connect('key_press_event', on_key)

def update(frame):
    global datos_suavizados
    
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            # Limpieza extra por si acaso
            line = line.replace("OK", "").replace("\x00", "").strip()
            
            if "," in line:
                partes = line.split(',')
                # Convertimos a floats, ignorando vacíos
                raw_data = [float(x.strip()) for x in partes if x.strip()]
                
                if len(raw_data) == NUM_CANALES:
                    # 1. FILTRO: Añadir al buffer y calcular promedio
                    buffer_lecturas.append(raw_data)
                    datos_suavizados = np.mean(buffer_lecturas, axis=0)
                    
                    # 2. CÁLCULOS: Diferencia e Índice
                    diferencia = datos_suavizados - referencia
                    # Índice = Promedio de cuánto se desvía cada canal (en valor absoluto)
                    indice_alteracion = np.mean(np.abs(diferencia))
                    
                    # 3. GUARDADO: Escribir en CSV
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(CSV_NAME, 'a', newline='') as f:
                        writer = csv.writer(f)
                        # Guardamos datos suavizados + el índice
                        fila = [timestamp] + list(np.around(datos_suavizados, 2)) + [round(indice_alteracion, 2)]
                        writer.writerow(fila)
                    
                    # 4. VISUALIZACIÓN
                    # Actualizar barras superiores
                    for b, v in zip(bar_actual, datos_suavizados): b.set_height(v)
                    for b, v in zip(bar_ref, referencia): b.set_height(v)
                    
                    # Actualizar barras inferiores (Diferencia)
                    for b, v in zip(bar_diff, diferencia): 
                        b.set_height(v)
                        # Cambiar color: Rojo si sube (reflejo), Azul si baja (absorción)
                        b.set_color('red' if v > 0 else 'blue')

                    # Escalas dinámicas (para que no se salga de la gráfica)
                    max_val = max(np.max(datos_suavizados), np.max(referencia), 10)
                    ax1.set_ylim(0, max_val * 1.2)
                    
                    max_diff = max(np.max(np.abs(diferencia)), 5)
                    ax2.set_ylim(-max_diff * 1.2, max_diff * 1.2)
                    
                    # Semáforo de Alerta
                    estado = "NORMAL"
                    color_txt = "green"
                    if indice_alteracion > 15: # Umbral de sensibilidad (ajústalo)
                        estado = "ALERTA: CONTAMINACIÓN"
                        color_txt = "red"
                    elif indice_alteracion > 5:
                        estado = "ADVERTENCIA"
                        color_txt = "orange"
                        
                    text_indice.set_text(f"Índice de Alteración: {indice_alteracion:.1f}")
                    text_indice.set_color(color_txt)
                    text_info.set_text(f"Estado: {estado}")
                    
        except ValueError:
            pass # Ignorar líneas corruptas parciales
        except Exception as e:
            print(f"Error en loop: {e}")

    return bar_actual, bar_ref, bar_diff

ani = animation.FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)
plt.show()