import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import csv
from datetime import datetime
import os
import numpy as np
from collections import deque

# --- CONFIGURACIÓN ---
PUERTO = 'COM3'  
BAUDIOS = 115200
NUM_CANALES = 18
CSV_NAME = "datos_tuberia.csv"

# Parámetros del Filtro
VENTANA_SUAVIZADO = 5  
TASA_ADAPTACION = 0.05      # Qué tan rápido perdona la deriva térmica (2% por ciclo)
UMBRAL_CONGELACION = 4.5    # Si el índice sube de 4.0 de golpe, DEJA de adaptarse (es contaminación real)
UMBRAL_ALERTA = 15.0        # Cuándo la gráfica se pone roja

labels = ['410', '435', '460', '485', '510', '535', '560', '585', '610', 
          '645', '705', '760', '610b', '680', '730', '760b', '810', '860']

referencia_dinamica = np.zeros(NUM_CANALES)
buffer_lecturas = deque(maxlen=VENTANA_SUAVIZADO)
calibrado = False

# Inicializar CSV
if not os.path.exists(CSV_NAME):
    with open(CSV_NAME, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp'] + labels + ['Indice_Alteracion'])

try:
    ser = serial.Serial(PUERTO, BAUDIOS, timeout=1)
    ser.flushInput()
    print("--- CONECTADO ---")
    print("Deja correr el agua limpia y presiona 'R' para la calibración inicial.")
except Exception as e:
    print(f"ERROR: {e}")
    exit()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))
plt.subplots_adjust(hspace=0.4)

bar_actual = ax1.bar(labels, [0]*NUM_CANALES, color='#007acc', alpha=0.8, label='Actual')
bar_ref = ax1.bar(labels, [0]*NUM_CANALES, color='gray', alpha=0.3, label='Referencia Dinámica')
text_info = ax1.text(0.02, 0.90, 'Esperando calibración...', transform=ax1.transAxes)
ax1.set_title("Espectro de Luz (Autocompensado)")
ax1.set_ylim(0, 1000)
ax1.legend()

bar_diff = ax2.bar(labels, [0]*NUM_CANALES, color='salmon')
ax2.set_title("Desviación (Eliminando Deriva Térmica)")
ax2.axhline(0, color='black')
text_indice = ax2.text(0.95, 0.90, 'Índice: 0.0', transform=ax2.transAxes, ha='right', fontsize=14, fontweight='bold')

def on_key(event):
    global referencia_dinamica, calibrado
    if event.key.lower() == 'r':
        if len(buffer_lecturas) > 0:
            referencia_dinamica = np.mean(buffer_lecturas, axis=0)
            calibrado = True
            print(">>> Calibración Inicial: Referencia Dinámica Activada")

fig.canvas.mpl_connect('key_press_event', on_key)

def update(frame):
    global referencia_dinamica
    
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').replace("OK", "").replace("\x00", "").strip()
            if "," in line:
                raw_data = [float(x.strip()) for x in line.split(',') if x.strip()]
                
                if len(raw_data) == NUM_CANALES:
                    buffer_lecturas.append(raw_data)
                    datos_suavizados = np.mean(buffer_lecturas, axis=0)
                    
                    if not calibrado:
                        return bar_actual, bar_ref, bar_diff
                    
                    # 1. Calcular Diferencia e Índice
                    diferencia = datos_suavizados - referencia_dinamica
                    indice_alteracion = np.mean(np.abs(diferencia))
                    
                    # 2. EL FILTRO MAGICO: Compensación Dinámica
                    # Si el índice es menor a UMBRAL_CONGELACION, asumimos que es calentamiento de LEDs o microburbujas
                    if indice_alteracion < UMBRAL_CONGELACION:
                        # Acercamos la referencia un 2% hacia los datos actuales
                        referencia_dinamica = (referencia_dinamica * (1 - TASA_ADAPTACION)) + (datos_suavizados * TASA_ADAPTACION)
                        
                        # Recalcular índice después de adaptar (tenderá a bajar a 0)
                        diferencia = datos_suavizados - referencia_dinamica
                        indice_alteracion = np.mean(np.abs(diferencia))

                    # 3. GUARDADO en CSV
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(CSV_NAME, 'a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp] + list(np.around(datos_suavizados, 2)) + [round(indice_alteracion, 2)])
                    
                    # 4. ACTUALIZACIÓN GRÁFICA
                    for b, v in zip(bar_actual, datos_suavizados): b.set_height(v)
                    for b, v in zip(bar_ref, referencia_dinamica): b.set_height(v)
                    for b, v in zip(bar_diff, diferencia): 
                        b.set_height(v)
                        b.set_color('red' if v > 0 else 'blue')

                    ax1.set_ylim(0, max(np.max(datos_suavizados), np.max(referencia_dinamica), 10) * 1.2)
                    max_d = max(np.max(np.abs(diferencia)), 5)
                    ax2.set_ylim(-max_d * 1.2, max_d * 1.2)
                    
        except Exception:
            pass

    return bar_actual, bar_ref, bar_diff

ani = animation.FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)

plt.show()
