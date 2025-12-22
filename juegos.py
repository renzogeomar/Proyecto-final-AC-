import cv2
import numpy as np
import random
import math
import config # Importamos nuestro archivo de config

# --- VARIABLES GLOBALES DE ESTADO ---

# JUEGO 1: FLAPPY
flappy_vars = {
    'pajaro_y': config.ALTO // 2, 'vel_y': 0, 'tubos': [], 
    'score': 0, 'game_over': False, 'contador': 0
}

# JUEGO 2: PONG
pong_vars = {
    'pala_jug_y': config.ALTO // 2, 'pala_pc_y': config.ALTO // 2,
    'bola_x': config.ANCHO // 2, 'bola_y': config.ALTO // 2,
    'vel_x': 15, 'vel_y': 15, 'score_jug': 0, 'score_pc': 0
}

# JUEGO 3: SNAKE
snake_vars = {
    'cuerpo': [], 
    'dir': (0,0), 
    'comida': [0,0], 
    'score': 0, 
    'game_over': False, 
    'timer': 0,
    # --- NUEVAS VARIABLES ---
    'crecimiento_pendiente': 0, # Cuantos segmentos faltan por crecer
    'bonus_pos': [-1, -1],      # Posición del bonus (-1 = inactivo)
    'bonus_timer_vida': 0,      # Cuánto tiempo le queda al bonus en pantalla
    'bonus_timer_spawn': 0      # Cuánto falta para que aparezca el siguiente
}

# JUEGO 4: LADRILLOS (Arcade Version)
ladrillos_vars = {
    'lista': [],            # Ladrillos [x, y, color, activo, tipo_poder]
    'pala_x': config.ANCHO//2, 
    'bolas': [],            # Lista de dicts: [{'x':..., 'y':..., 'vx':..., 'vy':...}]
    'powerups_cayendo': [], # Lista: [{'x':..., 'y':..., 'tipo':...}]
    'score': 0, 
    'game_over': False, 
    'victoria': False,
    'modo_fuego': False,    # Si es True, la bola atraviesa bloques
    'timer_fuego': 0        # Cuanto tiempo dura el fuego
}

# JUEGO 5: NINJA (Física Ajustada + Variedad)
ninja_vars = {
    'frutas': [],     # Lista: [x, y, vx, vy, es_bomba, tipo_fruta, angulo]
    'score': 0, 
    'vidas': 3, 
    'game_over': False, 
    'rastro': [],
    # Configuración de Física (Ajustada para que sea más fácil)
    'gravedad': 0.35, # Antes era 0.6 (Ahora caen más lento)
    'impulso_min': -18, # Antes -16 (Ahora suben más)
    'impulso_max': -22  # Antes -22
}

def reset_ninja():
    ninja_vars['frutas'] = []
    ninja_vars['score'] = 0
    ninja_vars['vidas'] = 3
    ninja_vars['game_over'] = False
    ninja_vars['rastro'] = []

# JUEGO 6: PINTAR
pintar_vars = {
    'canvas': np.zeros((config.ALTO, config.ANCHO, 3), np.uint8),
    'xp': 0, 'yp': 0, 
    'color': (255, 0, 255), # Magenta por defecto
    'grosor': 15,
    'interactuando_ui': False # Para saber si estamos tocando el menú
}

# --- FUNCIONES DE REINICIO ---

def reset_flappy():
    flappy_vars['pajaro_y'] = config.ALTO // 2
    flappy_vars['vel_y'] = 0
    flappy_vars['tubos'] = []
    flappy_vars['score'] = 0
    flappy_vars['game_over'] = False
    flappy_vars['contador'] = 0

def reset_pong():
    pong_vars['bola_x'] = config.ANCHO // 2
    pong_vars['bola_y'] = config.ALTO // 2
    pong_vars['vel_x'] = 15 * random.choice([1, -1])
    pong_vars['vel_y'] = 15 * random.choice([1, -1])

def reset_pong_full():
    pong_vars['score_jug'] = 0
    pong_vars['score_pc'] = 0
    reset_pong()

def reset_snake():
    cols = config.ANCHO // 40
    filas = config.ALTO // 40
    cx, cy = cols // 2, filas // 2
    snake_vars['cuerpo'] = [[cx, cy], [cx, cy+1], [cx, cy+2]]
    snake_vars['dir'] = (0, -1)
    snake_vars['score'] = 0
    snake_vars['game_over'] = False
    
    # Reiniciar nuevas variables
    snake_vars['crecimiento_pendiente'] = 0
    snake_vars['bonus_pos'] = [-1, -1] 
    snake_vars['bonus_timer_vida'] = 0
    snake_vars['bonus_timer_spawn'] = random.randint(50, 100) # Primer bonus aparece pronto
    
    spawn_comida_snake()

def spawn_comida_snake():
    cols = config.ANCHO // 40
    filas = config.ALTO // 40
    while True:
        x = random.randint(1, cols - 2)
        y = random.randint(1, filas - 2)
        if [x, y] not in snake_vars['cuerpo']:
            snake_vars['comida'] = [x, y]
            break

def reset_ladrillos():
    v = ladrillos_vars
    v['lista'] = []
    v['bolas'] = []
    v['powerups_cayendo'] = []
    v['score'] = 0
    v['game_over'] = False
    v['victoria'] = False
    v['modo_fuego'] = False
    v['timer_fuego'] = 0

    # --- GENERACIÓN DE NIVEL (PIRÁMIDE) ---
    cols = 14  # Más columnas = Bloques más pequeños
    filas = 8
    ancho_lad = config.ANCHO // cols
    alto_lad = 25
    offset_x = (config.ANCHO - (cols * ancho_lad)) // 2
    
    colores = [(255,0,0), (255,100,0), (255,255,0), (0,255,0), (0,255,255), (0,0,255), (150,0,255)]

    for f in range(filas):
        # Hacemos una pirámide invertida o forma interesante
        # Saltamos bloques en los bordes según la fila para dar forma
        start_col = f 
        end_col = cols - f
        
        for c in range(start_col, end_col):
            x = offset_x + c * ancho_lad
            y = f * alto_lad + 60
            color = colores[f % len(colores)]
            
            # Asignar Poderes Aleatorios
            # 0 = Nada, 1 = Multibola (10%), 2 = Fuego (5%)
            rand = random.random()
            tipo_poder = 0
            if rand < 0.10: tipo_poder = 1    # Multi
            elif rand < 0.15: tipo_poder = 2  # Fuego
            
            # [x, y, color, activo, tipo_poder, ancho, alto]
            v['lista'].append([x, y, color, True, tipo_poder, ancho_lad, alto_lad])
    
    # Bola inicial
    v['bolas'].append({
        'x': config.ANCHO // 2, 
        'y': config.ALTO // 2 + 100, 
        'vx': 8 * random.choice([1, -1]), 
        'vy': -8
    })
    v['pala_x'] = config.ANCHO // 2

def reset_ninja():
    ninja_vars['frutas'] = []
    ninja_vars['score'] = 0
    ninja_vars['vidas'] = 3
    ninja_vars['game_over'] = False
    ninja_vars['rastro'] = []

def reset_pintar():
    pintar_vars['canvas'] = np.zeros((config.ALTO, config.ANCHO, 3), np.uint8)

# --- MOTORES DE JUEGO (LÓGICA) ---

def dibujar_boton_salida(frame, ind_x, ind_y, click):
    """Dibuja el botón MENU y retorna True si se presiona"""
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    if click and 20 < ind_x < 150 and 20 < ind_y < 70:
        return True
    return False

def jugar_menu(frame, ind_x, ind_y, click):
    cv2.putText(frame, "SELECCIONA UN JUEGO", (config.ANCHO//2 - 200, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, config.COLOR_TEXTO, 3)

    # --- BOTONES DE JUEGOS (GRID 2x3) ---
    nombres = ["1. Flappy", "2. Pong", "3. Snake", "4. Ladrillos", "5. Ninja", "6. Pintar"]
    ancho, alto = 300, 150
    margen_x, margen_y = 100, 150
    
    nuevo_estado = "MENU"
    
    idx = 0
    for f in range(2):
        for c in range(3):
            x = margen_x + c * (ancho + 50)
            y = margen_y + f * (alto + 50)
            hover = x < ind_x < x + ancho and y < ind_y < y + alto
            
            color = config.COLOR_HOVER if hover else config.COLOR_FONDO_MENU
            overlay = frame.copy()
            cv2.rectangle(overlay, (x, y), (x + ancho, y + alto), color, -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
            cv2.rectangle(frame, (x, y), (x + ancho, y + alto), config.COLOR_BOTON, 3)
            cv2.putText(frame, nombres[idx], (x+20, y+alto//2+10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            
            if hover and click:
                if idx == 0: reset_flappy(); nuevo_estado = "JUEGO_1"
                elif idx == 1: reset_pong_full(); nuevo_estado = "JUEGO_2"
                elif idx == 2: reset_snake(); nuevo_estado = "JUEGO_3"
                elif idx == 3: reset_ladrillos(); nuevo_estado = "JUEGO_4"
                elif idx == 4: reset_ninja(); nuevo_estado = "JUEGO_5"
                elif idx == 5: reset_pintar(); nuevo_estado = "JUEGO_6"
            idx += 1

    # --- BOTÓN SALIR (NUEVO) ---
    # Lo colocamos abajo al centro
    btn_salir_w = 250
    btn_salir_h = 60
    btn_salir_x = config.ANCHO // 2 - btn_salir_w // 2
    btn_salir_y = config.ALTO - 100
    
    hover_salir = btn_salir_x < ind_x < btn_salir_x + btn_salir_w and btn_salir_y < ind_y < btn_salir_y + btn_salir_h
    
    # Color Rojo (oscuro normal, brillante si hover)
    color_salir = (0, 0, 255) if hover_salir else (0, 0, 150) 
    
    cv2.rectangle(frame, (btn_salir_x, btn_salir_y), (btn_salir_x + btn_salir_w, btn_salir_y + btn_salir_h), color_salir, -1)
    cv2.rectangle(frame, (btn_salir_x, btn_salir_y), (btn_salir_x + btn_salir_w, btn_salir_y + btn_salir_h), (255, 255, 255), 2)
    cv2.putText(frame, "SALIR DEL SISTEMA", (btn_salir_x + 20, btn_salir_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Lógica para cerrar
    if hover_salir and click:
        nuevo_estado = "SALIR" # Enviamos esta señal especial
            
    return frame, nuevo_estado

#################################################################################################
##ESTILIZAR EL JUEGO 1##
#################################################################################################

def dibujar_pajaro_estilizado(frame, x, y, angulo=0):
    """Dibuja un pájaro estilo cartoon usando primitivas de OpenCV"""
    # 1. Cuerpo (Amarillo con borde oscuro)
    cv2.circle(frame, (x, y), 22, (0, 200, 200), -1) # Sombra/Borde oscuro
    cv2.circle(frame, (x, y), 20, (0, 255, 255), -1) # Cuerpo Amarillo principal
    
    # 2. Ojo (Blanco grande + Pupila negra)
    cv2.circle(frame, (x + 8, y - 8), 10, (255, 255, 255), -1) # Esclerótica
    cv2.circle(frame, (x + 10, y - 8), 4, (0, 0, 0), -1)       # Pupila
    
    # 3. Pico (Naranja - Triángulo)
    # Definimos los 3 puntos del triángulo
    puntos_pico = np.array([
        [x + 12, y + 2],  # Arriba
        [x + 32, y + 10], # Punta
        [x + 12, y + 18]  # Abajo
    ])
    cv2.fillPoly(frame, [puntos_pico], (0, 140, 255)) # Naranja
    cv2.polylines(frame, [puntos_pico], True, (0, 0, 0), 1) # Borde negro fino

    # 4. Ala (Elipse blanca pequeña)
    cv2.ellipse(frame, (x - 12, y + 5), (10, 6), 0, 0, 360, (240, 240, 240), -1)
    cv2.ellipse(frame, (x - 12, y + 5), (10, 6), 0, 0, 360, (0, 0, 0), 1) # Borde

def dibujar_tubo_estilizado(frame, x, y, ancho, alto, es_superior):
    """Dibuja un tubo con efecto 3D y 'tapa'"""
    color_tubo = (0, 200, 0)       # Verde medio
    color_brillo = (50, 255, 50)   # Verde claro (luz)
    color_sombra = (0, 100, 0)     # Verde oscuro (sombra)
    color_borde = (0, 50, 0)       # Verde muy oscuro (borde)
    
    # Altura de la "tapa" del tubo
    alto_tapa = 30
    margen_tapa = 4 # Cuánto sobresale la tapa a los lados

    # 1. Cuerpo del tubo
    # Rectángulo principal
    cv2.rectangle(frame, (x, y), (x + ancho, y + alto), color_tubo, -1)
    # Brillo (lado izquierdo)
    cv2.rectangle(frame, (x + 5, y), (x + 15, y + alto), color_brillo, -1)
    # Sombra (lado derecho)
    cv2.rectangle(frame, (x + ancho - 10, y), (x + ancho - 2, y + alto), color_sombra, -1)
    # Borde
    cv2.rectangle(frame, (x, y), (x + ancho, y + alto), color_borde, 2)

    # 2. Tapa del tubo (La parte ancha)
    # Calculamos coordenadas de la tapa dependiendo si es el tubo de arriba o de abajo
    if es_superior:
        y_tapa = y + alto - alto_tapa
    else:
        y_tapa = y
        
    # Dibujar tapa (ligeramente más ancha que el tubo)
    x_tapa = x - margen_tapa
    ancho_tapa_total = ancho + (margen_tapa * 2)
    
    cv2.rectangle(frame, (x_tapa, y_tapa), (x_tapa + ancho_tapa_total, y_tapa + alto_tapa), color_tubo, -1)
    cv2.rectangle(frame, (x_tapa, y_tapa), (x_tapa + ancho_tapa_total, y_tapa + alto_tapa), color_borde, 2) # Borde tapa
    # Detalle brillo en tapa
    cv2.rectangle(frame, (x_tapa + 5, y_tapa + 2), (x_tapa + 15, y_tapa + alto_tapa - 2), color_brillo, -1)



#################################################################################################

#################################################################################################

#################################################################################################
###ESTILIZAR EL JUEGO 3##
#################################################################################################

def dibujar_manzana_estilizada(frame, x, y, size, es_dorada=False):
    """Dibuja una manzana roja o dorada con hoja"""
    cx = x + size // 2
    cy = y + size // 2
    radio = size // 2 - 2
    
    if es_dorada:
        color_cuerpo = (0, 215, 255) # Dorado (Gold en BGR)
        color_borde = (0, 140, 255)
        efecto_brillo = True
    else:
        color_cuerpo = (0, 0, 200)   # Rojo oscuro
        color_borde = (0, 0, 100)
        efecto_brillo = False

    # Cuerpo manzana
    cv2.circle(frame, (cx, cy + 2), radio, color_cuerpo, -1)
    cv2.circle(frame, (cx, cy + 2), radio, color_borde, 2)
    
    # Brillo (reflejo de luz)
    if efecto_brillo:
        cv2.circle(frame, (cx - 5, cy - 5), 4, (200, 255, 255), -1)
    else:
        cv2.circle(frame, (cx - 5, cy - 5), 3, (100, 100, 255), -1)

    # Tallo y Hoja
    cv2.line(frame, (cx, cy - radio + 5), (cx, cy - radio - 5), (50, 100, 50), 2) # Tallo
    # Hoja (elipse pequeña verde)
    cv2.ellipse(frame, (cx + 5, cy - radio - 2), (5, 3), 45, 0, 360, (0, 200, 0), -1)

def dibujar_serpiente_estilizada(frame, cuerpo, size):
    """Dibuja la serpiente con cabeza, ojos y cuerpo redondeado"""
    for i, segmento in enumerate(cuerpo):
        px = segmento[0] * size
        py = segmento[1] * size
        cx = px + size // 2
        cy = py + size // 2
        
        if i == 0: # --- CABEZA ---
            # Color verde más claro
            cv2.circle(frame, (cx, cy), size//2, (0, 200, 0), -1)
            
            # Ojos (blanco + pupila negra)
            # Calculamos posición de ojos según dirección sería ideal, 
            # pero por simplicidad los pondremos fijos arriba
            cv2.circle(frame, (cx - 6, cy - 6), 5, (255, 255, 255), -1)
            cv2.circle(frame, (cx + 6, cy - 6), 5, (255, 255, 255), -1)
            cv2.circle(frame, (cx - 6, cy - 6), 2, (0, 0, 0), -1)
            cv2.circle(frame, (cx + 6, cy - 6), 2, (0, 0, 0), -1)
            
            # Lengua (opcional)
            cv2.line(frame, (cx, cy+10), (cx, cy+18), (0, 0, 255), 2)
            
        else: # --- CUERPO ---
            # Color verde textura
            color = (0, 150, 0) if i % 2 == 0 else (0, 180, 0)
            cv2.circle(frame, (cx, cy), size//2 - 1, color, -1)

#################################################################################################
###ESTILIZAR EL JUEGO 4##
#################################################################################################
def dibujar_ladrillo_3d(frame, x, y, w, h, color):
    # Base
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
    # Borde "Luz" (Arriba e Izquierda)
    cv2.line(frame, (x, y+h), (x, y), (255,255,255), 2)
    cv2.line(frame, (x, y), (x+w, y), (255,255,255), 2)
    # Borde "Sombra" (Abajo y Derecha)
    cv2.line(frame, (x+w, y), (x+w, y+h), (0,0,0), 2)
    cv2.line(frame, (x, y+h), (x+w, y+h), (0,0,0), 2)
    # Centro hueco para efecto biselado
    cv2.rectangle(frame, (x+4, y+4), (x+w-4, y+h-4), color, -1)

def dibujar_powerup(frame, item):
    x, y = int(item['x']), int(item['y'])
    tipo = item['tipo']
    
    if tipo == 1: # Multibola (Azul)
        cv2.circle(frame, (x, y), 12, (255, 0, 0), -1)
        cv2.circle(frame, (x, y), 12, (255, 255, 255), 2)
        cv2.putText(frame, "x3", (x-8, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)
    elif tipo == 2: # Fuego (Rojo)
        cv2.circle(frame, (x, y), 12, (0, 0, 255), -1)
        cv2.circle(frame, (x, y), 12, (0, 255, 255), 2)
        cv2.putText(frame, "P", (x-5, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,255,255), 1)

#################################################################################################

#################################################################################################
##ESTILIZAR EL JUEGO 5##
#################################################################################################
def dibujar_fruta_detalle(frame, x, y, tipo, angulo=0):
    """Dibuja diferentes tipos de frutas proceduralmente"""
    # Tipos: 0=Sandía, 1=Naranja, 2=Manzana, 3=Coco, 4=Plátano
    radio = 35
    
    if tipo == 0: # SANDÍA (Verde con rayas)
        cv2.circle(frame, (x, y), radio, (0, 100, 0), -1) # Verde oscuro
        cv2.circle(frame, (x, y), radio-4, (0, 180, 0), -1) # Verde claro
        # Rayas (Simuladas con elipses)
        cv2.ellipse(frame, (x, y), (radio, radio), 0, 0, 360, (0, 100, 0), 2)
        cv2.ellipse(frame, (x-10, y), (5, 25), 20, 0, 360, (0, 80, 0), -1)
        cv2.ellipse(frame, (x+10, y), (5, 25), -20, 0, 360, (0, 80, 0), -1)
        
    elif tipo == 1: # NARANJA (Naranja con poros)
        cv2.circle(frame, (x, y), radio, (0, 100, 255), -1) # Naranja base (BGR)
        cv2.circle(frame, (x, y), radio, (0, 80, 200), 2)   # Borde
        # Poros (puntos pequeños)
        cv2.circle(frame, (x-10, y-10), 1, (0, 80, 200), -1)
        cv2.circle(frame, (x+15, y+5), 1, (0, 80, 200), -1)
        # Hoja pequeña
        cv2.ellipse(frame, (x, y-radio), (5, 3), 0, 0, 360, (0, 200, 0), -1)

    elif tipo == 2: # MANZANA (Roja clásica)
        cv2.circle(frame, (x, y), radio, (0, 0, 200), -1) # Roja
        # Brillo
        cv2.circle(frame, (x-10, y-10), 6, (100, 100, 255), -1)
        # Tallo
        cv2.line(frame, (x, y-radio+5), (x, y-radio-5), (50, 50, 50), 2)

    elif tipo == 3: # COCO (Marrón/Gris oscuro)
        cv2.circle(frame, (x, y), radio, (50, 70, 90), -1) # Marrón oscuro
        cv2.circle(frame, (x, y), radio-2, (70, 90, 110), -1) # Interior
        # Tres agujeros del coco
        cv2.circle(frame, (x-5, y), 3, (30, 50, 70), -1)
        cv2.circle(frame, (x+5, y), 3, (30, 50, 70), -1)
        cv2.circle(frame, (x, y-8), 3, (30, 50, 70), -1)

    elif tipo == 4: # PLÁTANO (Amarillo alargado)
        # Usamos elipse rotada para forma de banana
        cv2.ellipse(frame, (x, y), (radio+5, 15), 45, 0, 360, (0, 255, 255), -1) # Amarillo
        cv2.ellipse(frame, (x, y), (radio+5, 15), 45, 0, 360, (0, 200, 200), 2) # Borde
        # Puntas verdes/marrones
        pt1 = (int(x - 20), int(y + 20))
        pt2 = (int(x + 20), int(y - 20))
        cv2.circle(frame, pt1, 3, (0, 100, 0), -1)
        cv2.circle(frame, pt2, 3, (50, 50, 50), -1)

def dibujar_bomba_estilizada(frame, x, y):
    radio = 35
    # Cuerpo negro
    cv2.circle(frame, (x, y), radio, (20, 20, 20), -1)
    # Brillo metálico (Gris)
    cv2.circle(frame, (x-10, y-10), 8, (100, 100, 100), -1)
    
    # Símbolo de calavera o X simple
    cv2.line(frame, (x-10, y-10), (x+10, y+10), (255, 0, 0), 3) # X Roja
    cv2.line(frame, (x+10, y-10), (x-10, y+10), (255, 0, 0), 3)
    
    # Mecha
    cv2.line(frame, (x, y-radio), (x+10, y-radio-15), (150, 150, 150), 3)
    # Chispa (Color aleatorio para efecto fuego)
    color_chispa = (0, random.randint(100, 255), 255) # Naranja/Amarillo
    cv2.circle(frame, (x+10, y-radio-15), random.randint(3, 6), color_chispa, -1)

#################################################################################################

def jugar_flappy(frame, click):
    if dibujar_boton_salida(frame, -1, -1, False): pass 
    
    v = flappy_vars
    
    # --- LÓGICA (Sin cambios mayores) ---
    if not v['game_over']:
        if click: v['vel_y'] = -14
        v['vel_y'] += 0.8
        v['pajaro_y'] += int(v['vel_y'])
        
        v['contador'] += 1
        if v['contador'] >= 40:
            v['contador'] = 0
            # Ajustamos rango para que no queden tubos imposibles
            alt = random.randint(100, config.ALTO - 300)
            v['tubos'].append([config.ANCHO, alt])
            
        for t in v['tubos']: t[0] -= 8
        if v['tubos'] and v['tubos'][0][0] < -100: # Ajustado para dar margen al ancho del tubo
            v['tubos'].pop(0)
            v['score'] += 1
        
        # Colisiones
        if v['pajaro_y'] >= config.ALTO - 20 or v['pajaro_y'] <= 20: v['game_over'] = True
        
        ancho_tubo = 80
        apertura = 220 # Espacio entre tubos
        
        bird_rect_x = 100
        bird_rect_y = v['pajaro_y']
        bird_radio = 18 # Radio de colisión (un poco menor que el dibujo visual para ser justos)

        for t in v['tubos']:
             tubo_x = t[0]
             tubo_y_inf_arriba = t[1]
             
             # Verificar si el pájaro está horizontalmente dentro del tubo
             if (bird_rect_x + bird_radio > tubo_x and bird_rect_x - bird_radio < tubo_x + ancho_tubo):
                 # Verificar colisión vertical (Tocar tubo de arriba O tubo de abajo)
                 if (bird_rect_y - bird_radio < tubo_y_inf_arriba) or \
                    (bird_rect_y + bird_radio > tubo_y_inf_arriba + apertura):
                     v['game_over'] = True

    # --- DIBUJADO MEJORADO (Aquí está el cambio) ---
    
    ancho_tubo = 80
    apertura = 220

    for t in v['tubos']:
        # Tubo Arriba
        # (x, y, ancho, alto, es_superior)
        dibujar_tubo_estilizado(frame, t[0], 0, ancho_tubo, t[1], True)
        
        # Tubo Abajo
        # El tubo empieza en (y + apertura) y va hasta el final de la pantalla
        alto_tubo_abajo = config.ALTO - (t[1] + apertura)
        dibujar_tubo_estilizado(frame, t[0], t[1] + apertura, ancho_tubo, alto_tubo_abajo, False)

    # Dibujar Pájaro
    dibujar_pajaro_estilizado(frame, 100, v['pajaro_y'])

    # Score con Sombra (para que se lea mejor sobre cualquier fondo)
    texto_score = str(v['score'])
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 3
    thickness = 5
    pos_score = (config.ANCHO // 2, 100)
    
    # Sombra negra
    cv2.putText(frame, texto_score, (pos_score[0]+4, pos_score[1]+4), font, scale, (0,0,0), thickness+2)
    # Texto blanco
    cv2.putText(frame, texto_score, pos_score, font, scale, (255,255,255), thickness)

    # Mensaje Game Over
    if v['game_over']:
        overlay = frame.copy()
        cv2.rectangle(overlay, (config.ANCHO//2 - 250, config.ALTO//2 - 100), 
                               (config.ANCHO//2 + 250, config.ALTO//2 + 100), (0,0,0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        cv2.putText(frame, "GAME OVER", (config.ANCHO//2-200, config.ALTO//2-20), font, 2, (0,0,255), 5)
        cv2.putText(frame, "Click para reiniciar", (config.ANCHO//2-220, config.ALTO//2+60), font, 1.2, (255,255,255), 2)
        
        if click: reset_flappy()

    return frame

def jugar_pong(frame, ind_y):
    v = pong_vars
    if ind_y != -1: v['pala_jug_y'] = ind_y
    
    # IA
    if v['pala_pc_y'] < v['bola_y']: v['pala_pc_y'] += 10
    elif v['pala_pc_y'] > v['bola_y']: v['pala_pc_y'] -= 10
    
    # Bola
    v['bola_x'] += v['vel_x']
    v['bola_y'] += v['vel_y']
    
    if v['bola_y'] <= 0 or v['bola_y'] >= config.ALTO: v['vel_y'] *= -1
    
    # Rebote Palas
    pala_h = 120
    if (v['bola_x'] < 75 + 15 and v['bola_y'] > v['pala_jug_y'] - pala_h//2 and v['bola_y'] < v['pala_jug_y'] + pala_h//2):
        v['vel_x'] *= -1; v['bola_x'] = 95
    if (v['bola_x'] > config.ANCHO - 75 - 15 and v['bola_y'] > v['pala_pc_y'] - pala_h//2 and v['bola_y'] < v['pala_pc_y'] + pala_h//2):
        v['vel_x'] *= -1; v['bola_x'] = config.ANCHO - 95

    # Puntos
    if v['bola_x'] < 0: v['score_pc'] += 1; reset_pong()
    if v['bola_x'] > config.ANCHO: v['score_jug'] += 1; reset_pong()

    # Dibujo
    cv2.rectangle(frame, (50, v['pala_jug_y']-60), (75, v['pala_jug_y']+60), (255,0,0), -1)
    cv2.rectangle(frame, (config.ANCHO-75, v['pala_pc_y']-60), (config.ANCHO-50, v['pala_pc_y']+60), (0,0,255), -1)
    cv2.circle(frame, (v['bola_x'], v['bola_y']), 15, (255,255,255), -1)
    cv2.putText(frame, f"{v['score_jug']} - {v['score_pc']}", (config.ANCHO//2-100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 4)
    return frame

def jugar_snake(frame, ind_x, ind_y, click):
    v = snake_vars
    sz = 40 # Tamaño celda
    
    # --- GAME OVER ---
    if v['game_over']:
        overlay = frame.copy()
        cv2.rectangle(overlay, (config.ANCHO//2 - 250, config.ALTO//2 - 100), 
                               (config.ANCHO//2 + 250, config.ALTO//2 + 100), (0,0,0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.putText(frame, "GAME OVER", (config.ANCHO//2-200, config.ALTO//2-20), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 5)
        cv2.putText(frame, "Click para reiniciar", (config.ANCHO//2-220, config.ALTO//2+60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        if click: reset_snake()
        return frame

    # --- JOYSTICK VIRTUAL ---
    if ind_x != -1:
        dx = ind_x - config.ANCHO // 2
        dy = ind_y - config.ALTO // 2
        nd = v['dir']
        # Zona muerta de 50px
        if abs(dx) > 50 or abs(dy) > 50:
            if abs(dx) > abs(dy): nd = (1, 0) if dx > 0 else (-1, 0)
            else: nd = (0, 1) if dy > 0 else (0, -1)
        
        # Evitar giro de 180 grados
        if (nd[0]*-1 != v['dir'][0]) or (nd[1]*-1 != v['dir'][1]): v['dir'] = nd
        
        # Dibujar Flecha de Control
        cv2.arrowedLine(frame, (config.ANCHO//2, config.ALTO//2), (ind_x, ind_y), (100, 255, 255), 4)

    # --- LÓGICA DE JUEGO (TIMER) ---
    v['timer'] += 1
    
    # --- GESTIÓN DEL BONUS (MANZANA DORADA) ---
    # 1. Si NO hay bonus activo, bajamos el contador para que aparezca
    if v['bonus_pos'] == [-1, -1]:
        v['bonus_timer_spawn'] -= 1
        if v['bonus_timer_spawn'] <= 0:
            # Intentar generar bonus en lugar libre
            cols, filas = config.ANCHO // sz, config.ALTO // sz
            bx, by = random.randint(1, cols-2), random.randint(1, filas-2)
            if [bx, by] not in v['cuerpo'] and [bx, by] != v['comida']:
                v['bonus_pos'] = [bx, by]
                v['bonus_timer_vida'] = 150 # Dura 150 frames (aprox 5 segs)
    
    # 2. Si HAY bonus activo, bajamos su vida
    else:
        v['bonus_timer_vida'] -= 1
        if v['bonus_timer_vida'] <= 0:
            v['bonus_pos'] = [-1, -1] # Desaparece
            v['bonus_timer_spawn'] = random.randint(200, 400) # Reset timer spawn

    # --- MOVIMIENTO DE LA SERPIENTE ---
    if v['timer'] >= 6: # Velocidad (más bajo = más rápido)
        v['timer'] = 0
        cab = v['cuerpo'][0]
        nc = [cab[0] + v['dir'][0], cab[1] + v['dir'][1]]
        
        cols = config.ANCHO // sz
        filas = config.ALTO // sz
        
        # Colisiones
        if nc[0] < 0 or nc[0] >= cols or nc[1] < 0 or nc[1] >= filas or nc in v['cuerpo']:
            v['game_over'] = True
        else:
            v['cuerpo'].insert(0, nc) # Añadir nueva cabeza
            
            # --- COMER ---
            comio = False
            
            # 1. Comer Manzana Normal
            if nc == v['comida']:
                v['score'] += 1
                comio = True
                spawn_comida_snake()
            
            # 2. Comer Manzana Dorada (Bonus)
            elif nc == v['bonus_pos']:
                v['score'] += 5          # Más puntos
                v['crecimiento_pendiente'] += 2 # Crecerá 2 segmentos EXTRA
                v['bonus_pos'] = [-1, -1]
                v['bonus_timer_spawn'] = random.randint(200, 400)
                comio = True

            # --- GESTIÓN DE COLA (CRECIMIENTO) ---
            if comio:
                pass # Al comer, NO hacemos pop(), así que la serpiente crece 1
            else:
                # Si no comimos, chequeamos si hay crecimiento pendiente del bonus
                if v['crecimiento_pendiente'] > 0:
                    v['crecimiento_pendiente'] -= 1
                    # NO hacemos pop(), así crece otro segmento más
                else:
                    v['cuerpo'].pop() # Movimiento normal (borrar cola)

    # --- DIBUJADO VISUAL ---
    
    # 1. Dibujar Comida Normal
    dibujar_manzana_estilizada(frame, v['comida'][0]*sz, v['comida'][1]*sz, sz, es_dorada=False)
    
    # 2. Dibujar Bonus (Si existe)
    if v['bonus_pos'] != [-1, -1]:
        bx, by = v['bonus_pos']
        # Efecto parpadeo cuando queda poco tiempo
        if v['bonus_timer_vida'] > 30 or (v['bonus_timer_vida'] // 4) % 2 == 0:
            dibujar_manzana_estilizada(frame, bx*sz, by*sz, sz+5, es_dorada=True)
            
            # Barra de tiempo del bonus
            ancho_barra = int((v['bonus_timer_vida'] / 150) * sz)
            cv2.rectangle(frame, (bx*sz, by*sz - 5), (bx*sz + ancho_barra, by*sz - 2), (0, 255, 255), -1)

    # 3. Dibujar Serpiente
    dibujar_serpiente_estilizada(frame, v['cuerpo'], sz)

    # 4. HUD (Score)
    cv2.putText(frame, f"Score: {v['score']}", (config.ANCHO - 250, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    if dibujar_boton_salida(frame, -1, -1, False): pass 

    return frame

def jugar_ladrillos(frame, ind_x, click):
    v = ladrillos_vars
    
    # --- UI GAME OVER / WIN ---
    if v['game_over'] or v['victoria']:
        overlay = frame.copy()
        msg = "VICTORIA" if v['victoria'] else "GAME OVER"
        color_bg = (0, 200, 0) if v['victoria'] else (0, 0, 0)
        cv2.rectangle(overlay, (config.ANCHO//2 - 200, config.ALTO//2 - 100), (config.ANCHO//2 + 200, config.ALTO//2 + 100), color_bg, -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.putText(frame, msg, (config.ANCHO//2-180, config.ALTO//2+10), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 5)
        cv2.putText(frame, "Click para reiniciar", (config.ANCHO//2-150, config.ALTO//2+60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        if click: reset_ladrillos()
        return frame

    # --- MOVIMIENTO PALA ---
    pala_ancho = 150
    if ind_x != -1: v['pala_x'] = max(pala_ancho//2, min(config.ANCHO-pala_ancho//2, ind_x))
    
    # Timer Modo Fuego
    if v['modo_fuego']:
        v['timer_fuego'] -= 1
        if v['timer_fuego'] <= 0: v['modo_fuego'] = False

    # --- LÓGICA DE BOLAS (Iteramos sobre copia para poder borrar) ---
    for b in v['bolas'][:]:
        b['x'] += b['vx']
        b['y'] += b['vy']
        
        # Rebotes Paredes
        if b['x'] <= 10 or b['x'] >= config.ANCHO-10: b['vx'] *= -1
        if b['y'] <= 10: b['vy'] *= -1
        
        # Perder bola (Suelo)
        if b['y'] >= config.ALTO:
            v['bolas'].remove(b)
            continue # Siguiente bola

        # Colisión Pala
        pala_top = config.ALTO - 60
        if (pala_top - 10 < b['y'] < pala_top + 10) and (v['pala_x'] - pala_ancho//2 < b['x'] < v['pala_x'] + pala_ancho//2):
            b['vy'] = -abs(b['vy']) # Siempre hacia arriba
            # Efecto de ángulo según donde pegue en la pala
            diff = b['x'] - v['pala_x']
            b['vx'] = int(diff / 6)
            # Asegurar velocidad mínima X
            if abs(b['vx']) < 3: b['vx'] = 3 if b['vx'] >= 0 else -3

        # Colisión Ladrillos
        hit_block = False
        activos = 0
        for l in v['lista']:
            # l = [x, y, color, activo, tipo_poder, w, h]
            if l[3]: # Si está activo
                activos += 1
                lx, ly, w, h = l[0], l[1], l[5], l[6]
                
                # Check colisión simple
                if (lx < b['x'] < lx + w) and (ly < b['y'] < ly + h):
                    # Romper bloque
                    l[3] = False
                    v['score'] += 10
                    
                    # Soltar Powerup (Si tiene)
                    if l[4] > 0:
                        v['powerups_cayendo'].append({'x': lx + w//2, 'y': ly + h, 'tipo': l[4]})
                    
                    # Rebote (Solo si NO es modo fuego)
                    if not v['modo_fuego']:
                        # Determinar si pegó horizontal o verticalmente es complejo,
                        # simplificamos invirtiendo Y
                        b['vy'] *= -1
                    
                    hit_block = True
                    break # Solo romper uno por frame por bola
        
        if activos == 0: v['victoria'] = True

    if len(v['bolas']) == 0:
        v['game_over'] = True

    # --- LÓGICA POWERUPS ---
    for p in v['powerups_cayendo'][:]:
        p['y'] += 5 # Caída
        
        # Colisión con Pala
        if (config.ALTO - 70 < p['y'] < config.ALTO - 40) and (v['pala_x'] - pala_ancho//2 < p['x'] < v['pala_x'] + pala_ancho//2):
            # Activar Poder
            if p['tipo'] == 1: # Multibola
                # Añadir 2 bolas más desde la pala
                for _ in range(2):
                    v['bolas'].append({
                        'x': v['pala_x'], 'y': config.ALTO - 80, 
                        'vx': random.randint(-8, 8), 'vy': -8
                    })
            elif p['tipo'] == 2: # Fuego
                v['modo_fuego'] = True
                v['timer_fuego'] = 300 # 5 Segundos aprox
            
            v['powerups_cayendo'].remove(p)
        elif p['y'] > config.ALTO:
            v['powerups_cayendo'].remove(p)

    # --- DIBUJADO ---
    
    # 1. Ladrillos
    for l in v['lista']:
        if l[3]:
            dibujar_ladrillo_3d(frame, l[0], l[1], l[5], l[6], l[2])

    # 2. Powerups
    for p in v['powerups_cayendo']:
        dibujar_powerup(frame, p)

    # 3. Pala
    color_pala = (0, 0, 255) if v['modo_fuego'] else (0, 255, 255)
    cv2.rectangle(frame, (v['pala_x']-pala_ancho//2, config.ALTO-60), (v['pala_x']+pala_ancho//2, config.ALTO-40), color_pala, -1)
    # Barra de tiempo fuego
    if v['modo_fuego']:
        ancho_barra = int((v['timer_fuego'] / 300) * pala_ancho)
        cv2.rectangle(frame, (v['pala_x']-pala_ancho//2, config.ALTO-35), (v['pala_x']-pala_ancho//2 + ancho_barra, config.ALTO-30), (0,0,255), -1)

    # 4. Bolas
    for b in v['bolas']:
        color_bola = (0, 0, 255) if v['modo_fuego'] else (255, 255, 255)
        radio = 10 if v['modo_fuego'] else 8
        cv2.circle(frame, (int(b['x']), int(b['y'])), radio, color_bola, -1)
        if v['modo_fuego']: # Efecto fuego
             cv2.circle(frame, (int(b['x']), int(b['y'])), radio-4, (0, 255, 255), -1)

    cv2.putText(frame, f"Score: {v['score']}", (config.ANCHO-200, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    
    if dibujar_boton_salida(frame, -1, -1, False): pass 

    return frame

def jugar_ninja(frame, ind_x, ind_y, click):
    v = ninja_vars
    
    # --- GAME OVER ---
    if v['game_over']:
        overlay = frame.copy()
        cv2.rectangle(overlay, (config.ANCHO//2 - 250, config.ALTO//2 - 100), 
                               (config.ANCHO//2 + 250, config.ALTO//2 + 100), (0,0,0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.putText(frame, "GAME OVER", (config.ANCHO//2-200, config.ALTO//2-20), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 5)
        cv2.putText(frame, "Click para reiniciar", (config.ANCHO//2-220, config.ALTO//2+60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 2)
        if click: reset_ninja()
        return frame

    # --- GENERAR FRUTAS ---
    # Probabilidad ajustada: 4% por frame (un poco más frecuente ahora que caen lento)
    if random.randint(0, 100) < 4:
        # X aleatoria (evitando bordes extremos)
        x = random.randint(100, config.ANCHO-100)
        y = config.ALTO + 50 # Empiezan bien abajo
        
        # FÍSICA MEJORADA: Disparan más alto
        vy = random.randint(v['impulso_max'], v['impulso_min']) # Entre -28 y -23
        
        # VX calculada para que intenten ir hacia el centro (arco parabólico)
        if x < config.ANCHO // 2:
            vx = random.randint(3, 9)  # Hacia derecha
        else:
            vx = random.randint(-9, -3) # Hacia izquierda
            
        es_bomba = random.random() < 0.2
        tipo_fruta = random.randint(0, 4) # 0 a 4 (Variedad)
        
        # [x, y, vx, vy, es_bomba, tipo_fruta]
        v['frutas'].append([x, y, vx, vy, es_bomba, tipo_fruta])

    # --- RASTRO DE ESPADA ---
    if ind_x != -1: v['rastro'].append((ind_x, ind_y))
    if len(v['rastro']) > 8: v['rastro'].pop(0) # Rastro un poco más corto para rendimiento

    # --- ACTUALIZAR FRUTAS ---
    for f in v['frutas'][:]:
        f[0] += f[2] # X
        f[1] += f[3] # Y
        f[3] += v['gravedad'] # Gravedad reducida (0.35)
        
        # Detectar CORTE
        hit = False
        if ind_x != -1:
            dist = math.hypot(ind_x - f[0], ind_y - f[1])
            if dist < 45: # Radio de corte un poco más generoso
                hit = True
        
        if hit:
            if f[4]: # Bomba
                v['game_over'] = True
            else: # Fruta
                v['score'] += 1
                # Visual: Pequeño flash del color de la fruta al cortar (Opcional)
                # cv2.circle(frame, (int(f[0]), int(f[1])), 50, (255,255,255), -1) 
                v['frutas'].remove(f)
        
        # Caída fuera de pantalla
        elif f[1] > config.ALTO + 100:
            if not f[4]: # Si se cae una fruta buena
                v['vidas'] -= 1
                if v['vidas'] <= 0: v['game_over'] = True
            v['frutas'].remove(f)

    # --- DIBUJADO ---
    
    # 1. Rastro
    for i in range(1, len(v['rastro'])):
        # Color cian brillante para la espada
        thickness = int(np.sqrt(i * 3))
        cv2.line(frame, v['rastro'][i-1], v['rastro'][i], (255, 255, 200), thickness)

    # 2. Frutas y Bombas
    for f in v['frutas']:
        x, y = int(f[0]), int(f[1])
        if f[4]:
            dibujar_bomba_estilizada(frame, x, y)
        else:
            dibujar_fruta_detalle(frame, x, y, f[5]) # f[5] es el tipo

    # 3. Interfaz
    cv2.putText(frame, f"Score: {v['score']}", (config.ANCHO - 250, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Corazones (Vidas)
    for i in range(v['vidas']):
        cx = config.ANCHO - 250 + (i*40)
        cv2.circle(frame, (cx, 100), 12, (0, 0, 255), -1)
        # Brillo corazón
        cv2.circle(frame, (cx-4, 100-4), 4, (200, 200, 255), -1)

    if dibujar_boton_salida(frame, -1, -1, False): pass 

    return frame

def jugar_pintar(frame, ind_x, ind_y, pul_x, pul_y, click):
    """
    Juego de Pintar Mejorado:
    - Pinta solo con gesto de pinza (Pinch).
    - Incluye barra deslizadora de grosor.
    - Incluye color negro/borrador.
    - Cursor siempre visible.
    """
    v = pintar_vars
    
    # --- 1. DETECCIÓN DE GESTO (PINCH) ---
    # Calculamos si el usuario está haciendo "pinza" con los dedos
    distancia = math.hypot(ind_x - pul_x, ind_y - pul_y)
    pintando = distancia < 40  # Umbral para considerar que está "apretando" el lápiz
    
    # --- 2. DEFINICIÓN DE INTERFAZ (UI) ---
    # Definimos zonas para detectar colisiones antes de dibujar
    
    # Zona del Panel Derecho
    panel_w = 120 # Hacemos el panel un poco más estrecho y limpio
    panel_x = config.ANCHO - panel_w
    panel_y = 0
    panel_h = config.ALTO
    
    # Barra Deslizadora (Slider)
    slider_x = panel_x + 20
    slider_y = 50
    slider_w = 80
    slider_h = 200 # Barra vertical
    
    # Colores
    colores = [
        ((255, 0, 0), "Azul"),
        ((0, 255, 0), "Verde"),
        ((0, 0, 255), "Rojo"),
        ((0, 255, 255), "Amarillo"),
        ((255, 0, 255), "Magenta"),
        ((255, 255, 255), "Blanco"),
        ((0, 0, 0), "Borrar") # El negro actúa como goma en este modo de fusión
    ]
    
    # Botón Limpiar Todo
    btn_limpiar_rect = (panel_x + 10, config.ALTO - 80, panel_w - 20, 50) # x, y, w, h
    
    # --- 3. LÓGICA DE INTERACCIÓN CON UI ---
    v['interactuando_ui'] = False
    
    # Si la mano está sobre el panel derecho
    if ind_x > panel_x:
        v['interactuando_ui'] = True
        
        if pintando: # Solo interactuamos si hace el gesto de click/pinch
            
            # A) Lógica del Slider de Grosor
            if slider_x < ind_x < slider_x + slider_w and slider_y - 20 < ind_y < slider_y + slider_h + 20:
                # Calcular porcentaje de altura (0 a 1)
                porcentaje = (ind_y - slider_y) / slider_h
                porcentaje = max(0, min(1, porcentaje)) # Limitar entre 0 y 1
                v['grosor'] = int(porcentaje * 50) + 1 # Grosor entre 1 y 50
            
            # B) Lógica de Selección de Color
            inicio_colores_y = slider_y + slider_h + 30
            tam_btn = 40
            for i, (color, label) in enumerate(colores):
                cy = inicio_colores_y + (i * (tam_btn + 10))
                # Detectar click en el círculo del color
                if slider_x < ind_x < slider_x + slider_w and cy < ind_y < cy + tam_btn:
                    v['color'] = color
            
            # C) Lógica Botón Limpiar
            bx, by, bw, bh = btn_limpiar_rect
            if bx < ind_x < bx + bw and by < ind_y < by + bh:
                v['canvas'] = np.zeros((config.ALTO, config.ANCHO, 3), np.uint8)

    # --- 4. LÓGICA DE DIBUJO EN CANVAS ---
    # Solo pintamos si hace pinch, NO está tocando el menú, y tiene la mano en pantalla
    if pintando and not v['interactuando_ui'] and ind_x != -1:
        if v['xp'] == 0 and v['yp'] == 0:
            v['xp'], v['yp'] = ind_x, ind_y # Punto inicial
        
        # Dibujar línea
        cv2.line(v['canvas'], (v['xp'], v['yp']), (ind_x, ind_y), v['color'], v['grosor'])
        v['xp'], v['yp'] = ind_x, ind_y
    else:
        # Si suelta el pinch, reseteamos el punto previo para no arrastrar líneas
        v['xp'], v['yp'] = 0, 0

    # --- 5. FUSIÓN DE IMÁGENES (CANVAS + CÁMARA) ---
    # Técnica para que el negro borre y los colores se sumen
    img_gray = cv2.cvtColor(v['canvas'], cv2.COLOR_BGR2GRAY)
    _, img_inv = cv2.threshold(img_gray, 10, 255, cv2.THRESH_BINARY_INV)
    img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
    
    # Borramos del frame donde hay pintura
    frame = cv2.bitwise_and(frame, img_inv)
    # Sumamos la pintura al frame
    frame = cv2.bitwise_or(frame, v['canvas'])

    # --- 6. DIBUJAR LA INTERFAZ (VISUAL) ---
    
    # Fondo del panel (Gris oscuro semi-transparente)
    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, 0), (config.ANCHO, config.ALTO), (30, 30, 30), -1)
    frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
    
    # A) Dibujar Slider
    cv2.putText(frame, "GROSOR", (panel_x + 20, slider_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    # Línea central
    cv2.line(frame, (panel_x + panel_w//2, slider_y), (panel_x + panel_w//2, slider_y + slider_h), (100, 100, 100), 2)
    # Botón del slider (posición según grosor actual)
    pos_y_slider = slider_y + int((v['grosor'] / 51) * slider_h)
    cv2.circle(frame, (panel_x + panel_w//2, pos_y_slider), 15, (255, 255, 255), -1)
    cv2.putText(frame, str(v['grosor']), (panel_x + panel_w//2 + 20, pos_y_slider + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    # B) Dibujar Botones de Colores
    inicio_colores_y = slider_y + slider_h + 30
    tam_btn = 40
    for i, (color, label) in enumerate(colores):
        cy = inicio_colores_y + (i * (tam_btn + 10))
        cx = panel_x + panel_w // 2
        
        # Borde blanco si está seleccionado
        if v['color'] == color:
            cv2.circle(frame, (cx, cy + tam_btn//2), tam_btn//2 + 4, (255, 255, 255), 2)
        
        # Círculo del color (Si es negro/borrador, le ponemos borde blanco para verlo)
        c_visual = color
        if color == (0,0,0):
             cv2.circle(frame, (cx, cy + tam_btn//2), tam_btn//2, (0,0,0), -1)
             cv2.circle(frame, (cx, cy + tam_btn//2), tam_btn//2, (100,100,100), 1) # Borde gris
        else:
             cv2.circle(frame, (cx, cy + tam_btn//2), tam_btn//2, color, -1)

    # C) Dibujar Botón Limpiar
    bx, by, bw, bh = btn_limpiar_rect
    cv2.rectangle(frame, (bx, by), (bx+bw, by+bh), (50, 50, 200), -1) # Rojo oscuro
    cv2.putText(frame, "LIMPIAR", (bx + 15, by + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # --- 7. CURSOR DE LA MANO (POR ENCIMA DE TODO) ---
    # Esto soluciona que el dedo quede "detrás" del menú
    if ind_x != -1:
        # El cursor cambia de color según si estás pintando o no
        color_cursor = (0, 255, 0) if pintando else (200, 200, 200)
        
        # Si estamos sobre el menú, hacemos el cursor más evidente
        if v['interactuando_ui']:
            cv2.circle(frame, (ind_x, ind_y), 10, (255, 255, 255), -1) # Blanco solido
            cv2.circle(frame, (ind_x, ind_y), 10, (0, 0, 0), 1) # Borde negro
        else:
            # Cursor normal con el color que tenemos seleccionado
            cursor_fill = v['color'] if v['color'] != (0,0,0) else (150,150,150)
            cv2.circle(frame, (ind_x, ind_y), v['grosor']//2, cursor_fill, -1)
            cv2.circle(frame, (ind_x, ind_y), v['grosor']//2 + 2, color_cursor, 2) # Anillo de estado

    # --- BOTÓN SALIDA (MENÚ) ---
    if dibujar_boton_salida(frame, ind_x, ind_y, click):
        reset_pintar()
        return frame # Volver al menú

    return frame


# --- GESTOR PRINCIPAL ---

def gestionar_flujo(estado, frame, ind_x, ind_y, pul_x, pul_y, click):
    """Función maestra que decide qué juego ejecutar"""
    
    # Botón Salir Global (excepto en menú)
    if estado != "MENU":
        if dibujar_boton_salida(frame, ind_x, ind_y, click):
            return frame, "MENU"

    if estado == "MENU":
        return jugar_menu(frame, ind_x, ind_y, click)
    
    elif estado == "JUEGO_1": return jugar_flappy(frame, click), estado
    elif estado == "JUEGO_2": return jugar_pong(frame, ind_y), estado
    elif estado == "JUEGO_3": return jugar_snake(frame, ind_x, ind_y, click), estado
    elif estado == "JUEGO_4": return jugar_ladrillos(frame, ind_x, click), estado
    elif estado == "JUEGO_5": return jugar_ninja(frame, ind_x, ind_y, click), estado
    elif estado == "JUEGO_6": return jugar_pintar(frame, ind_x, ind_y, pul_x, pul_y, click), estado
    
    return frame, estado