import cv2
import mediapipe as mp
import numpy as np
import random
import math

# --- CONFIGURACIÓN GENERAL ---
ANCHO_VENTANA = 1280  # Aumentamos resolución para que quepan 6 botones
ALTO_VENTANA = 720
ESTADO_ACTUAL = "MENU" # Estados: "MENU", "JUEGO_1", "JUEGO_2", etc.

# Inicialización MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(1)
cap.set(3, ANCHO_VENTANA)
cap.set(4, ALTO_VENTANA)

# Variables globales de control de mano
click_detectado = False
estado_anterior_pinch = False

# --- VARIABLES JUEGO 1 (FLAPPY) ---
flappy_iniciado = False
pajaro_y = ALTO_VENTANA // 2
velocidad_y = 0
gravedad = 0.8  # Ajustado para resolución 720p
fuerza_salto = -14
tubos = []
score = 0
game_over = False
# Configuración tubos
ancho_tubo = 80
velocidad_tubos = 8
apertura_tubo = 250
frecuencia_tubos = 40
contador_frames = 0

# --- VARIABLES JUEGO 2 (PONG) ---
pong_iniciado = False
# Dimensiones
pala_ancho = 25
pala_alto = 120
bola_radio = 15
# Posiciones
pala_jugador_y = ALTO_VENTANA // 2
pala_pc_y = ALTO_VENTANA // 2
bola_x = ANCHO_VENTANA // 2
bola_y = ALTO_VENTANA // 2
# Velocidades
vel_bola_x = 15
vel_bola_y = 15
vel_pc = 10 # Velocidad de la IA 
# Puntuación
score_jugador = 0
score_pc = 0

def reset_pong():
    """Reinicia la bola al centro"""
    global bola_x, bola_y, vel_bola_x, vel_bola_y
    bola_x = ANCHO_VENTANA // 2
    bola_y = ALTO_VENTANA // 2
    # La bola sale en dirección aleatoria
    vel_bola_x = 15 * random.choice([1, -1])
    vel_bola_y = 15 * random.choice([1, -1])

def reset_pong_full():
    """Reinicia todo el juego (scores incluidos)"""
    global score_jugador, score_pc
    score_jugador = 0
    score_pc = 0
    reset_pong()

# --- VARIABLES JUEGO 3 (SNAKE) ---
snake_cuerpo = []  # Lista de segmentos [x, y]
snake_dir = (0, 0) # Dirección actual (dx, dy)
comida_pos = [0, 0]
tamano_celda = 40  # Tamaño de cada cuadrito
# Calculamos cuántas celdas caben en pantalla
cols_snake = ANCHO_VENTANA // tamano_celda
filas_snake = ALTO_VENTANA // tamano_celda
timer_snake = 0
velocidad_snake = 8 # Frames que espera para moverse (Menor = Más rápido)
score_snake = 0
game_over_snake = False

def spawn_comida():
    """Genera comida en una posición aleatoria libre"""
    global comida_pos
    while True:
        x = random.randint(1, cols_snake - 2)
        y = random.randint(1, filas_snake - 2)
        if [x, y] not in snake_cuerpo:
            comida_pos = [x, y]
            break

def reset_snake():
    global snake_cuerpo, snake_dir, score_snake, game_over_snake, timer_snake
    # La serpiente empieza en el centro
    cx, cy = cols_snake // 2, filas_snake // 2
    snake_cuerpo = [[cx, cy], [cx, cy+1], [cx, cy+2]] # Cabeza, cuerpo, cola
    snake_dir = (0, -1) # Empieza moviéndose hacia ARRIBA
    score_snake = 0
    game_over_snake = False
    timer_snake = 0
    spawn_comida()

# --- VARIABLES JUEGO 4 (LADRILLOS / BREAKOUT) ---
ladrillos_lista = []
ladrillos_filas = 5
ladrillos_cols = 10
ladrillo_ancho = ANCHO_VENTANA // ladrillos_cols
ladrillo_alto = 30
ladrillo_colores = [(255, 0, 0), (255, 100, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255)]

# Pala y Bola
pala_ladrillo_x = ANCHO_VENTANA // 2
pala_ladrillo_ancho = 150
pala_ladrillo_alto = 20
bola_ladrillo_x = ANCHO_VENTANA // 2
bola_ladrillo_y = ALTO_VENTANA // 2
vel_ladrillo_x = 10
vel_ladrillo_y = -10 # Empieza subiendo
bola_ladrillo_radio = 12

score_ladrillos = 0
game_over_ladrillos = False
victoria_ladrillos = False

def crear_nivel_ladrillos():
    """Genera la lista de ladrillos"""
    global ladrillos_lista
    ladrillos_lista = []
    for fila in range(ladrillos_filas):
        for col in range(ladrillos_cols):
            # Guardamos [x, y, color_rgb, activo(True/False)]
            x = col * ladrillo_ancho
            y = fila * ladrillo_alto + 80 # +80 de margen superior
            color = ladrillo_colores[fila % len(ladrillo_colores)]
            ladrillos_lista.append([x, y, color, True])

def reset_ladrillos():
    global pala_ladrillo_x, bola_ladrillo_x, bola_ladrillo_y, vel_ladrillo_x, vel_ladrillo_y
    global score_ladrillos, game_over_ladrillos, victoria_ladrillos
    
    crear_nivel_ladrillos()
    pala_ladrillo_x = ANCHO_VENTANA // 2
    bola_ladrillo_x = ANCHO_VENTANA // 2
    bola_ladrillo_y = ALTO_VENTANA // 2 + 100
    vel_ladrillo_x = 10 * random.choice([1, -1])
    vel_ladrillo_y = -10
    score_ladrillos = 0
    game_over_ladrillos = False
    victoria_ladrillos = False

# --- VARIABLES JUEGO 5 (FRUIT NINJA) ---
frutas = [] # Cada elemento será: [x, y, vel_x, vel_y, es_bomba]
gravedad_fruta = 0.6
score_ninja = 0
vidas_ninja = 3
game_over_ninja = False
radio_fruta = 35
puntos_rastro = [] # Para dibujar la estela de la espada

def spawn_fruta():
    """Lanza una nueva fruta o bomba desde abajo"""
    # Posición X aleatoria, pero no muy pegada a los bordes
    x = random.randint(100, ANCHO_VENTANA - 100)
    y = ALTO_VENTANA # Empieza abajo
    
    # Velocidad hacia arriba (aleatoria para variar altura)
    vel_y = random.randint(-22, -16) 
    
    # Velocidad lateral (para que haga una curva hacia el centro o lados)
    if x < ANCHO_VENTANA // 2:
        vel_x = random.randint(2, 8) # Va a la derecha
    else:
        vel_x = random.randint(-8, -2) # Va a la izquierda
        
    # 20% de probabilidad de ser bomba
    es_bomba = True if random.random() < 0.2 else False
    
    frutas.append([x, y, vel_x, vel_y, es_bomba])

def reset_ninja():
    global frutas, score_ninja, vidas_ninja, game_over_ninja, puntos_rastro
    frutas = []
    score_ninja = 0
    vidas_ninja = 3
    game_over_ninja = False
    puntos_rastro = []

# --- VARIABLES JUEGO 6 (PINTAR) ---
canvas_pintar = np.zeros((ALTO_VENTANA, ANCHO_VENTANA, 3), np.uint8) # Lienzo negro
xp, yp = 0, 0 # Coordenadas previas (para conectar líneas)
color_pincel = (255, 0, 255) # Color inicial (Magenta)
grosor_pincel = 15
colores_ui = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (0, 0, 0)] # Azul, Verde, Rojo, Amarillo, Borrador
# Nota: OpenCV usa BGR, así que (255,0,0) es Azul. El último (0,0,0) es el Borrador.

def reset_pintar():
    global canvas_pintar
    canvas_pintar = np.zeros((ALTO_VENTANA, ANCHO_VENTANA, 3), np.uint8) # Limpiar lienzo

# --- FUNCIONES AUXILIARES ---

def detectar_pinch(ind_x, ind_y, pul_x, pul_y):
    """Devuelve True si los dedos están juntos (click)"""
    distancia = math.hypot(ind_x - pul_x, ind_y - pul_y)
    return distancia < 40

def dibujar_boton(frame, x, y, w, h, texto, color_borde, seleccionado=False):
    """Dibuja un botón en el menú"""
    color_fondo = (50, 50, 50) if not seleccionado else (0, 200, 0)
    # Fondo semi-transparente
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + w, y + h), color_fondo, -1)
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    
    # Borde y Texto
    cv2.rectangle(frame, (x, y), (x + w, y + h), color_borde, 3)
    cv2.putText(frame, texto, (x + 20, y + h // 2 + 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return frame

def reset_flappy():
    """Reinicia variables del juego 1"""
    global pajaro_y, velocidad_y, tubos, score, game_over, flappy_iniciado, contador_frames
    pajaro_y = ALTO_VENTANA // 2
    velocidad_y = 0
    tubos = []
    score = 0
    game_over = False
    flappy_iniciado = True
    contador_frames = 0

# --- LÓGICA DE ESCENAS ---

def mostrar_menu(frame, ind_x, ind_y, click_realizado):
    global ESTADO_ACTUAL
    
    cv2.putText(frame, "SELECCIONA UN JUEGO", (ANCHO_VENTANA//2 - 200, 80), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

    # Definir botones (Grid 2x3)
    ancho_btn = 300
    alto_btn = 150
    margen_x = 100
    margen_y = 150
    separacion_x = 50
    separacion_y = 50

    nombres_juegos = ["1. Flappy Hand", "2. Pong", "3. Snake", 
                      "4. Ladrillos", "5. Ninja", "6. Pintar"]
    
    # Dibujar los 6 botones
    idx = 0
    for fila in range(2):
        for col in range(3):
            x = margen_x + col * (ancho_btn + separacion_x)
            y = margen_y + fila * (alto_btn + separacion_y)
            
            # Detectar si el dedo está sobre el botón
            hover = x < ind_x < x + ancho_btn and y < ind_y < y + alto_btn
            
            frame = dibujar_boton(frame, x, y, ancho_btn, alto_btn, nombres_juegos[idx], (255, 255, 0), hover)
            
            # Si hace click sobre el botón
            if hover and click_realizado:
                if idx == 0: # Juego 1
                    reset_flappy()
                    ESTADO_ACTUAL = "JUEGO_1"
                elif idx == 1: # Juego 2 (PONG) 
                    reset_pong_full()
                    ESTADO_ACTUAL = "JUEGO_2"
                elif idx == 2: # Juego 3 (Snake) 
                    reset_snake()
                    ESTADO_ACTUAL = "JUEGO_3"
                elif idx == 3: # Ladrillos 
                    reset_ladrillos()
                    ESTADO_ACTUAL = "JUEGO_4"
                elif idx == 4: # Ninja 
                    reset_ninja()
                    ESTADO_ACTUAL = "JUEGO_5"
                elif idx == 5: # Pintar 
                    reset_pintar()
                    ESTADO_ACTUAL = "JUEGO_6"
                else:
                    print(f"Juego {idx+1} aún no implementado")
            
            idx += 1
            
    return frame

def jugar_flappy_bird(frame, ind_x, ind_y, click_realizado):
    global pajaro_y, velocidad_y, tubos, score, game_over, ESTADO_ACTUAL, contador_frames
    
    # --- BOTÓN SALIR (Siempre visible) ---
    # Dibujamos el botón de volver al menú
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Si hace click en el botón de menú (independiente de si ganó o perdió)
    if click_realizado and 20 < ind_x < 150 and 20 < ind_y < 70:
        ESTADO_ACTUAL = "MENU"
        return frame

    # --- LÓGICA DE JUEGO ACTIVO ---
    if not game_over:
        # 1. Física Salto
        if click_realizado:
            velocidad_y = fuerza_salto
        
        # 2. Gravedad
        velocidad_y += gravedad
        pajaro_y += int(velocidad_y)
        
        # 3. Generar Tubos
        contador_frames += 1
        if contador_frames >= frecuencia_tubos:
            contador_frames = 0
            altura = random.randint(100, ALTO_VENTANA - 100 - apertura_tubo)
            tubos.append([ANCHO_VENTANA, altura])
            
        # 4. Mover Tubos
        for tubo in tubos:
            tubo[0] -= velocidad_tubos
        
        # Eliminar tubos viejos
        if len(tubos) > 0 and tubos[0][0] < -ancho_tubo:
            tubos.pop(0)
            score += 1
            
        # 5. Colisiones (Suelo, Techo y Tubos)
        if pajaro_y >= ALTO_VENTANA or pajaro_y <= 0:
            game_over = True
        
        # Rectángulo del pájaro para colisiones
        for tubo in tubos:
            if (100 + 20 > tubo[0] and 100 - 20 < tubo[0] + ancho_tubo):
                if (pajaro_y - 20 < tubo[1]) or (pajaro_y + 20 > tubo[1] + apertura_tubo):
                    game_over = True

    # --- LÓGICA DE GAME OVER (NUEVO) ---
    else:
        # Si el juego terminó y el usuario hace el gesto de "click" (juntar dedos)
        if click_realizado:
            reset_flappy() # <--- ESTO REINICIA EL JUEGO INMEDIATAMENTE

    # --- DIBUJADO (RENDER) ---
    for tubo in tubos:
        cv2.rectangle(frame, (tubo[0], 0), (tubo[0] + ancho_tubo, tubo[1]), (0, 255, 0), -1)
        cv2.rectangle(frame, (tubo[0], tubo[1] + apertura_tubo), (tubo[0] + ancho_tubo, ALTO_VENTANA), (0, 255, 0), -1)
        
    cv2.circle(frame, (100, pajaro_y), 20, (0, 255, 255), -1)
    
    # Texto del Score
    cv2.putText(frame, str(score), (ANCHO_VENTANA//2, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
    
    # --- PANTALLA DE PERDEDOR ---
    if game_over:
        # Fondo oscuro para el texto
        overlay = frame.copy()
        cv2.rectangle(overlay, (ANCHO_VENTANA//2 - 300, ALTO_VENTANA//2 - 150), 
                               (ANCHO_VENTANA//2 + 300, ALTO_VENTANA//2 + 150), (0,0,0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Textos informativos
        cv2.putText(frame, "GAME OVER", (ANCHO_VENTANA//2 - 200, ALTO_VENTANA//2 - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 5)
        
        cv2.putText(frame, "Junta los dedos para REINICIAR", (ANCHO_VENTANA//2 - 280, ALTO_VENTANA//2 + 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.putText(frame, "o toca MENU para salir", (ANCHO_VENTANA//2 - 180, ALTO_VENTANA//2 + 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)

    return frame

def jugar_pong(frame, ind_y, click_realizado):
    global pala_jugador_y, pala_pc_y, bola_x, bola_y, vel_bola_x, vel_bola_y, score_jugador, score_pc, ESTADO_ACTUAL
    
    # --- BOTÓN SALIR ---
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Necesitamos ind_x para el botón de salir, asumimos que viene del tracking general
    # (Para simplificar, si hay click en esa zona, salimos. 
    #  Nota: En el bucle principal ya pasas ind_x, asegúrate de pasarlo a esta función si quieres precisión perfecta,
    #  pero aquí usaremos una detección genérica si click_realizado es True).
    if click_realizado:
         # Verificamos zona aproximada del botón (0 a 150 px en X)
         # Como en esta función solo recibimos ind_y por diseño limpio, 
         # asumimos que si clickea arriba a la izquierda es salir.
         # (Para hacerlo perfecto, añade ind_x a los argumentos de esta función).
         pass 

    # --- CONTROL JUGADOR (Paleta Izquierda) ---
    # Si detecta mano, la paleta sigue al dedo
    if ind_y != -1:
        pala_jugador_y = ind_y

    # Limites visuales pala jugador
    if pala_jugador_y < pala_alto//2: pala_jugador_y = pala_alto//2
    if pala_jugador_y > ALTO_VENTANA - pala_alto//2: pala_jugador_y = ALTO_VENTANA - pala_alto//2

    # --- IA COMPUTADORA (Paleta Derecha) ---
    # La IA intenta alinear su centro con la bola
    if pala_pc_y < bola_y:
        pala_pc_y += vel_pc
    elif pala_pc_y > bola_y:
        pala_pc_y -= vel_pc

    # --- MOVIMIENTO BOLA ---
    bola_x += vel_bola_x
    bola_y += vel_bola_y

    # Rebote arriba y abajo
    if bola_y <= 0 or bola_y >= ALTO_VENTANA:
        vel_bola_y *= -1

    # --- COLISIONES CON PALETAS ---
    # Paleta Jugador (Izquierda, X=50)
    if (bola_x - bola_radio < 50 + pala_ancho and bola_x - bola_radio > 50):
        if (pala_jugador_y - pala_alto//2 < bola_y < pala_jugador_y + pala_alto//2):
            vel_bola_x *= -1
            bola_x = 50 + pala_ancho + bola_radio + 5 # Evitar que se pegue
            
    # Paleta PC (Derecha, X=ANCHO-50)
    if (bola_x + bola_radio > ANCHO_VENTANA - 50 - pala_ancho and bola_x + bola_radio < ANCHO_VENTANA - 50):
        if (pala_pc_y - pala_alto//2 < bola_y < pala_pc_y + pala_alto//2):
            vel_bola_x *= -1
            bola_x = ANCHO_VENTANA - 50 - pala_ancho - bola_radio - 5

    # --- PUNTUACIÓN ---
    if bola_x < 0:
        score_pc += 1
        reset_pong()
    elif bola_x > ANCHO_VENTANA:
        score_jugador += 1
        reset_pong()

    # --- DIBUJADO ---
    # Línea central
    cv2.line(frame, (ANCHO_VENTANA//2, 0), (ANCHO_VENTANA//2, ALTO_VENTANA), (100, 100, 100), 2)
    
    # Paleta Jugador (Azul)
    cv2.rectangle(frame, (50, pala_jugador_y - pala_alto//2), (50 + pala_ancho, pala_jugador_y + pala_alto//2), (255, 0, 0), -1)
    
    # Paleta PC (Rojo)
    cv2.rectangle(frame, (ANCHO_VENTANA - 50 - pala_ancho, pala_pc_y - pala_alto//2), (ANCHO_VENTANA - 50, pala_pc_y + pala_alto//2), (0, 0, 255), -1)
    
    # Bola (Blanca)
    cv2.circle(frame, (bola_x, bola_y), bola_radio, (255, 255, 255), -1)
    
    # Marcador
    cv2.putText(frame, str(score_jugador), (ANCHO_VENTANA//4, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    cv2.putText(frame, str(score_pc), (3*ANCHO_VENTANA//4, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)

    return frame

def jugar_snake(frame, ind_x, ind_y, click_realizado):
    global snake_cuerpo, snake_dir, comida_pos, score_snake, game_over_snake, timer_snake, ESTADO_ACTUAL
    
    # --- BOTÓN SALIR ---
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    if click_realizado and 20 < ind_x < 150 and 20 < ind_y < 70:
        ESTADO_ACTUAL = "MENU"
        return frame

    if game_over_snake:
        # Pantalla de derrota
        overlay = frame.copy()
        cv2.rectangle(overlay, (ANCHO_VENTANA//2 - 300, ALTO_VENTANA//2 - 100), 
                               (ANCHO_VENTANA//2 + 300, ALTO_VENTANA//2 + 100), (0,0,0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.putText(frame, f"Score Final: {score_snake}", (ANCHO_VENTANA//2 - 180, ALTO_VENTANA//2 - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(frame, "Junta dedos para REINICIAR", (ANCHO_VENTANA//2 - 250, ALTO_VENTANA//2 + 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        if click_realizado:
            reset_snake()
        return frame

    # --- CONTROL DE DIRECCIÓN (JOYSTICK VIRTUAL) ---
    if ind_x != -1: # Si detecta mano
        cx, cy = ANCHO_VENTANA // 2, ALTO_VENTANA // 2
        dx = ind_x - cx
        dy = ind_y - cy
        
        # Determinar si el movimiento es más horizontal o vertical
        nueva_dir = snake_dir
        
        # Umbral para evitar cambios bruscos en el centro (Zona muerta)
        if abs(dx) > 50 or abs(dy) > 50: 
            if abs(dx) > abs(dy): # Movimiento Horizontal
                if dx > 0: nueva_dir = (1, 0)  # Derecha
                else:      nueva_dir = (-1, 0) # Izquierda
            else: # Movimiento Vertical
                if dy > 0: nueva_dir = (0, 1)  # Abajo
                else:      nueva_dir = (0, -1) # Arriba

        # Evitar que la serpiente regrese sobre sí misma (ej: ir derecha estando en izquierda)
        if (nueva_dir[0] * -1 != snake_dir[0]) or (nueva_dir[1] * -1 != snake_dir[1]):
            snake_dir = nueva_dir
        
        # Visualización de la flecha de dirección
        centro = (ANCHO_VENTANA//2, ALTO_VENTANA//2)
        punta = (ind_x, ind_y)
        cv2.arrowedLine(frame, centro, punta, (255, 255, 0), 5)

    # --- ACTUALIZACIÓN DEL JUEGO (Por Timer) ---
    timer_snake += 1
    if timer_snake >= velocidad_snake:
        timer_snake = 0
        
        # Mover cabeza
        cabeza_actual = snake_cuerpo[0]
        nueva_cabeza = [cabeza_actual[0] + snake_dir[0], cabeza_actual[1] + snake_dir[1]]
        
        # 1. Colisión con Bordes
        if (nueva_cabeza[0] < 0 or nueva_cabeza[0] >= cols_snake or 
            nueva_cabeza[1] < 0 or nueva_cabeza[1] >= filas_snake):
            game_over_snake = True
            
        # 2. Colisión con su cuerpo
        elif nueva_cabeza in snake_cuerpo:
            game_over_snake = True
            
        else:
            # Avanzar: Añadir nueva cabeza
            snake_cuerpo.insert(0, nueva_cabeza)
            
            # 3. Comer Manzana
            if nueva_cabeza == comida_pos:
                score_snake += 1
                spawn_comida()
            else:
                # Si no come, quitamos la cola (movimiento normal)
                snake_cuerpo.pop()

    # --- DIBUJADO ---
    # Dibujar Cuadrícula tenue (opcional, ayuda a visualizar)
    # for x in range(0, ANCHO_VENTANA, tamano_celda):
    #     cv2.line(frame, (x, 0), (x, ALTO_VENTANA), (50, 50, 50), 1)
    # for y in range(0, ALTO_VENTANA, tamano_celda):
    #     cv2.line(frame, (0, y), (ANCHO_VENTANA, y), (50, 50, 50), 1)

    # Dibujar Comida (Roja)
    cx_comida = comida_pos[0] * tamano_celda + tamano_celda//2
    cy_comida = comida_pos[1] * tamano_celda + tamano_celda//2
    cv2.circle(frame, (cx_comida, cy_comida), tamano_celda//2 - 2, (0, 0, 255), -1)

    # Dibujar Serpiente (Verde)
    for i, segmento in enumerate(snake_cuerpo):
        sx = segmento[0] * tamano_celda
        sy = segmento[1] * tamano_celda
        color = (0, 255, 0) if i == 0 else (0, 200, 0) # Cabeza más brillante
        cv2.rectangle(frame, (sx, sy), (sx + tamano_celda, sy + tamano_celda), color, -1)
        cv2.rectangle(frame, (sx, sy), (sx + tamano_celda, sy + tamano_celda), (0, 100, 0), 2) # Borde

    # Score
    cv2.putText(frame, f"Score: {score_snake}", (ANCHO_VENTANA - 250, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return frame

def jugar_ladrillos(frame, ind_x, click_realizado):
    global pala_ladrillo_x, bola_ladrillo_x, bola_ladrillo_y, vel_ladrillo_x, vel_ladrillo_y
    global score_ladrillos, game_over_ladrillos, victoria_ladrillos, ESTADO_ACTUAL, ladrillos_lista

    # --- BOTÓN SALIR ---
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Detección de click en botón Menú (ind_x necesitamos pasarlo, ind_y asumimos zona superior)
    # Nota: Para precisión total, pasa ind_y a la función. Aquí simplificamos.
    if click_realizado and 20 < ind_x < 150: 
         # Asumiendo que el usuario está apuntando arriba a la izq
         ESTADO_ACTUAL = "MENU"
         return frame

    # --- PANTALLAS DE FIN DE JUEGO ---
    if game_over_ladrillos or victoria_ladrillos:
        overlay = frame.copy()
        color_bg = (0, 0, 0) if game_over_ladrillos else (0, 200, 0)
        texto = "GAME OVER" if game_over_ladrillos else "¡VICTORIA!"
        
        cv2.rectangle(overlay, (ANCHO_VENTANA//2 - 300, ALTO_VENTANA//2 - 150), 
                               (ANCHO_VENTANA//2 + 300, ALTO_VENTANA//2 + 150), color_bg, -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        cv2.putText(frame, texto, (ANCHO_VENTANA//2 - 200, ALTO_VENTANA//2 - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 5)
        cv2.putText(frame, "Junta dedos para REINICIAR", (ANCHO_VENTANA//2 - 250, ALTO_VENTANA//2 + 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        if click_realizado:
            reset_ladrillos()
        return frame

    # --- CONTROL PALA (MOVIMIENTO HORIZONTAL) ---
    if ind_x != -1:
        pala_ladrillo_x = ind_x

    # Limites pala
    if pala_ladrillo_x < pala_ladrillo_ancho//2: pala_ladrillo_x = pala_ladrillo_ancho//2
    if pala_ladrillo_x > ANCHO_VENTANA - pala_ladrillo_ancho//2: pala_ladrillo_x = ANCHO_VENTANA - pala_ladrillo_ancho//2

    # --- FÍSICA BOLA ---
    bola_ladrillo_x += vel_ladrillo_x
    bola_ladrillo_y += vel_ladrillo_y

    # Rebote Paredes (Izquierda, Derecha, Techo)
    if bola_ladrillo_x <= bola_ladrillo_radio or bola_ladrillo_x >= ANCHO_VENTANA - bola_ladrillo_radio:
        vel_ladrillo_x *= -1
    if bola_ladrillo_y <= bola_ladrillo_radio:
        vel_ladrillo_y *= -1
    
    # Perder (Suelo)
    if bola_ladrillo_y >= ALTO_VENTANA:
        game_over_ladrillos = True

    # Colisión con Pala
    pala_y_pos = ALTO_VENTANA - 60
    # Verificamos si la bola está a la altura de la pala
    if (pala_y_pos - bola_ladrillo_radio < bola_ladrillo_y < pala_y_pos + pala_ladrillo_alto):
        # Verificamos si está dentro del ancho de la pala
        if (pala_ladrillo_x - pala_ladrillo_ancho//2 < bola_ladrillo_x < pala_ladrillo_x + pala_ladrillo_ancho//2):
            vel_ladrillo_y *= -1 # Rebote vertical
            # Ajuste para evitar que se quede pegada
            bola_ladrillo_y = pala_y_pos - bola_ladrillo_radio - 2 
            
            # Efecto: Si pega en los bordes de la pala, cambia velocidad X
            diferencia = bola_ladrillo_x - pala_ladrillo_x
            vel_ladrillo_x = int(diferencia / 5) # Da efecto a la bola

    # --- COLISIÓN CON LADRILLOS ---
    ladrillos_activos = 0
    hit = False
    for ladrillo in ladrillos_lista:
        # ladrillo = [x, y, color, activo]
        if ladrillo[3]: # Si está activo
            ladrillos_activos += 1
            lx, ly = ladrillo[0], ladrillo[1]
            
            # Chequeo simple de colisión Rectángulo-Círculo
            if (lx < bola_ladrillo_x < lx + ladrillo_ancho) and \
               (ly < bola_ladrillo_y < ly + ladrillo_alto) and not hit:
                
                ladrillo[3] = False # Desactivar ladrillo
                vel_ladrillo_y *= -1 # Rebotar bola
                score_ladrillos += 10
                hit = True # Solo romper uno por frame para evitar bugs
                
    if ladrillos_activos == 0:
        victoria_ladrillos = True

    # --- DIBUJADO ---
    
    # Dibujar Ladrillos
    for ladrillo in ladrillos_lista:
        if ladrillo[3]: # Solo dibujar activos
            cv2.rectangle(frame, (ladrillo[0] + 2, ladrillo[1] + 2), 
                          (ladrillo[0] + ladrillo_ancho - 2, ladrillo[1] + ladrillo_alto - 2), 
                          ladrillo[2], -1)

    # Dibujar Pala
    cv2.rectangle(frame, (pala_ladrillo_x - pala_ladrillo_ancho//2, ALTO_VENTANA - 60), 
                  (pala_ladrillo_x + pala_ladrillo_ancho//2, ALTO_VENTANA - 40), (0, 255, 255), -1)

    # Dibujar Bola
    cv2.circle(frame, (bola_ladrillo_x, int(bola_ladrillo_y)), bola_ladrillo_radio, (255, 255, 255), -1)
    
    # Score
    cv2.putText(frame, f"Score: {score_ladrillos}", (ANCHO_VENTANA - 250, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    return frame

def jugar_ninja(frame, ind_x, ind_y, click_realizado):
    global frutas, score_ninja, vidas_ninja, game_over_ninja, ESTADO_ACTUAL, puntos_rastro
    
    # --- BOTÓN SALIR ---
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    if click_realizado and 20 < ind_x < 150 and 20 < ind_y < 70:
        ESTADO_ACTUAL = "MENU"
        return frame

    # --- PANTALLA GAME OVER ---
    if game_over_ninja:
        overlay = frame.copy()
        cv2.rectangle(overlay, (ANCHO_VENTANA//2 - 300, ALTO_VENTANA//2 - 150), 
                               (ANCHO_VENTANA//2 + 300, ALTO_VENTANA//2 + 150), (0,0,0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        cv2.putText(frame, "GAME OVER", (ANCHO_VENTANA//2 - 200, ALTO_VENTANA//2 - 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
        cv2.putText(frame, f"Score Final: {score_ninja}", (ANCHO_VENTANA//2 - 150, ALTO_VENTANA//2 + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "Junta dedos para REINICIAR", (ANCHO_VENTANA//2 - 250, ALTO_VENTANA//2 + 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        if click_realizado:
            reset_ninja()
        return frame

    # --- LÓGICA DEL JUEGO ---
    
    # 1. Generar frutas aleatoriamente (aprox cada 30-40 frames)
    if random.randint(0, 100) < 3: # 3% de chance por frame
        spawn_fruta()

    # 2. Actualizar Rastro de Espada (Visual)
    if ind_x != -1:
        puntos_rastro.append((ind_x, ind_y))
    if len(puntos_rastro) > 10: # Mantener solo los últimos 10 puntos
        puntos_rastro.pop(0)

    # 3. Mover y gestionar frutas
    # Iteramos sobre una copia de la lista para poder borrar elementos seguramente
    for fruta in frutas[:]:
        # fruta = [x, y, vx, vy, es_bomba]
        
        # Movimiento (Física)
        fruta[0] += fruta[2] # X += Vx
        fruta[1] += fruta[3] # Y += Vy
        fruta[3] += gravedad_fruta # Gravedad afecta a Vy
        
        # Detectar CORTE con el dedo
        # Si la distancia entre el dedo y la fruta es menor al radio
        if ind_x != -1:
            distancia = math.hypot(ind_x - fruta[0], ind_y - fruta[1])
            if distancia < radio_fruta:
                if fruta[4]: # Es BOMBA
                    game_over_ninja = True
                else: # Es FRUTA
                    score_ninja += 1
                    frutas.remove(fruta)
                    continue # Saltamos al siguiente ciclo para no procesar más esta fruta borrada

        # Detectar si cae fuera de pantalla
        if fruta[1] > ALTO_VENTANA + 50:
            if not fruta[4]: # Si se cae una fruta (no bomba), pierdes vida
                vidas_ninja -= 1
                if vidas_ninja <= 0:
                    game_over_ninja = True
            frutas.remove(fruta)

    # --- DIBUJADO ---
    
    # 1. Dibujar Rastro Espada
    for i in range(1, len(puntos_rastro)):
        # Grosor variable (más fino al final)
        thickness = int(np.sqrt(i * 2))
        cv2.line(frame, puntos_rastro[i-1], puntos_rastro[i], (255, 255, 255), thickness)

    # 2. Dibujar Frutas
    for fruta in frutas:
        x, y = int(fruta[0]), int(fruta[1])
        if fruta[4]: # Bomba
            cv2.circle(frame, (x, y), radio_fruta, (0, 0, 0), -1) # Negro
            cv2.circle(frame, (x, y), radio_fruta, (0, 0, 255), 2) # Borde Rojo
            # Mecha de bomba (detalle visual simple)
            cv2.line(frame, (x, y-radio_fruta), (x+10, y-radio_fruta-10), (100,100,100), 2)
        else: # Fruta
            cv2.circle(frame, (x, y), radio_fruta, (0, 200, 0), -1) # Verde
            cv2.circle(frame, (x, y), radio_fruta-10, (100, 255, 100), -1) # Brillo interno

    # 3. Interfaz (Score y Vidas)
    cv2.putText(frame, f"Score: {score_ninja}", (ANCHO_VENTANA - 250, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Dibujar corazones (vidas)
    for i in range(vidas_ninja):
        cv2.circle(frame, (ANCHO_VENTANA - 250 + (i*40), 100), 15, (0, 0, 255), -1)

    return frame

def jugar_pintar(frame, ind_x, ind_y, pul_x, pul_y, click_realizado):
    global canvas_pintar, color_pincel, grosor_pincel, xp, yp, ESTADO_ACTUAL

    # --- BOTÓN SALIR ---
    cv2.rectangle(frame, (20, 20), (150, 70), (0, 0, 255), -1)
    cv2.putText(frame, "MENU", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    if click_realizado and 20 < ind_x < 150 and 20 < ind_y < 70:
        ESTADO_ACTUAL = "MENU"
        return frame

    # --- INTERFAZ DE COLORES (HEADER) ---
    # Dibujamos rectángulos en la parte superior
    ancho_color = 100
    inicio_x = ANCHO_VENTANA // 2 - (len(colores_ui) * ancho_color) // 2
    
    cv2.rectangle(frame, (inicio_x - 10, 10), (inicio_x + len(colores_ui)*ancho_color + 10, 90), (50,50,50), -1)
    
    for i, color in enumerate(colores_ui):
        x = inicio_x + i * ancho_color
        y = 20
        # Si es el borrador (negro), dibujamos un borde blanco para verlo
        borde = (255, 255, 255) if color == (0, 0, 0) else color
        cv2.rectangle(frame, (x, y), (x + ancho_color - 10, 80), color, -1)
        cv2.rectangle(frame, (x, y), (x + ancho_color - 10, 80), borde, 2)
        
        # Texto para el borrador
        if color == (0,0,0):
             cv2.putText(frame, "GOMA", (x+10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    # --- LÓGICA DE DIBUJO ---
    if ind_x != -1:
        # 1. Detectar si estamos "apretando" (Pinch continuo)
        distancia = math.hypot(ind_x - pul_x, ind_y - pul_y)
        modo_dibujo = distancia < 45 # Si están cerca, dibujamos

        # 2. Selección de color (Si estamos arriba y haciendo click)
        if ind_y < 90 and modo_dibujo:
            # Verificar en qué caja de color estamos
            if ind_x > inicio_x:
                index_col = (ind_x - inicio_x) // ancho_color
                if 0 <= index_col < len(colores_ui):
                    color_pincel = colores_ui[index_col]
                    # Si es goma, pincel más grande
                    grosor_pincel = 40 if color_pincel == (0,0,0) else 15

        # 3. Dibujar en el Lienzo (Si estamos abajo)
        if modo_dibujo and ind_y > 90:
            if xp == 0 and yp == 0: # Primer punto
                xp, yp = ind_x, ind_y
            
            # Dibujamos LÍNEAS entre el punto anterior y el actual para suavidad
            if color_pincel == (0, 0, 0):
                # Goma: Dibuja negro en el canvas
                cv2.line(canvas_pintar, (xp, yp), (ind_x, ind_y), (0, 0, 0), grosor_pincel)
            else:
                # Pincel: Dibuja color
                cv2.line(canvas_pintar, (xp, yp), (ind_x, ind_y), color_pincel, grosor_pincel)
            
            xp, yp = ind_x, ind_y # Actualizamos previo
            
        else:
            # Si soltamos los dedos, reseteamos el punto previo para no arrastrar líneas
            xp, yp = 0, 0

    # --- MEZCLAR IMÁGENES (FUSIÓN MÁGICA) ---
    # Convertimos el canvas a escala de grises para crear una máscara
    img_gray = cv2.cvtColor(canvas_pintar, cv2.COLOR_BGR2GRAY)
    _, img_inv = cv2.threshold(img_gray, 50, 255, cv2.THRESH_BINARY_INV)
    
    # "Borramos" del frame original el área donde hay dibujo (se vuelve negra)
    img_inv = cv2.cvtColor(img_inv, cv2.COLOR_GRAY2BGR)
    frame = cv2.bitwise_and(frame, img_inv)
    
    # "Sumamos" el dibujo coloreado al hueco negro que acabamos de hacer
    frame = cv2.bitwise_or(frame, canvas_pintar)

    # --- CURSOR VISUAL ---
    # Muestra qué color tienes seleccionado en la punta del dedo
    if ind_x != -1:
        color_cursor = (200, 200, 200) if color_pincel == (0,0,0) else color_pincel
        cv2.circle(frame, (ind_x, ind_y), grosor_pincel//2, color_cursor, -1)

    return frame

# --- BUCLE PRINCIPAL ---

with mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7) as hands:
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        # Variables de coordenadas por defecto (fuera de pantalla si no hay mano)
        ind_x, ind_y = -1, -1
        pul_x, pul_y = -1, -1
        click_realizado = False # Click de este frame (Flanco)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                h, w, _ = frame.shape
                ind_x = int(hand_landmarks.landmark[8].x * w)
                ind_y = int(hand_landmarks.landmark[8].y * h)
                pul_x = int(hand_landmarks.landmark[4].x * w)
                pul_y = int(hand_landmarks.landmark[4].y * h)
                
                # Detectar Click (Pinch)
                pinch_actual = detecting_pinch = detectar_pinch(ind_x, ind_y, pul_x, pul_y)
                
                # Visualización del Pinch
                color_pinch = (0, 255, 0) if pinch_actual else (0, 0, 255)
                cv2.circle(frame, ((ind_x + pul_x)//2, (ind_y + pul_y)//2), 10, color_pinch, -1)
                
                # Lógica de Flanco (Solo activar una vez al juntar)
                if pinch_actual and not estado_anterior_pinch:
                    click_realizado = True
                
                estado_anterior_pinch = pinch_actual

        # --- MÁQUINA DE ESTADOS ---
        
        if ESTADO_ACTUAL == "MENU":
            frame = mostrar_menu(frame, ind_x, ind_y, click_realizado)
            
        elif ESTADO_ACTUAL == "JUEGO_1":
            frame = jugar_flappy_bird(frame, ind_x, ind_y, click_realizado)
            
        # Aquí irán los elif para JUEGO_2, JUEGO_3, etc.######################################

        elif ESTADO_ACTUAL == "JUEGO_2": # <--- NUEVO BLOQUE
            # Pasamos ind_x también para poder programar bien el botón de salir
            # Nota: He actualizado la llamada para incluir ind_x abajo
            
            # Lógica rápida para salir (debes integrarla en la función o hacerlo aquí)
            if click_realizado and 20 < ind_x < 150 and 20 < ind_y < 70:
                ESTADO_ACTUAL = "MENU"
             
            frame = jugar_pong(frame, ind_y, click_realizado)
        
        elif ESTADO_ACTUAL == "JUEGO_3": # <--- NUEVO BLOQUE SNAKE
             frame = jugar_snake(frame, ind_x, ind_y, click_realizado)

        elif ESTADO_ACTUAL == "JUEGO_4": # <--- NUEVO BLOQUE
             # Pasamos ind_x (movimiento lateral) y click (para reiniciar/salir)
             frame = jugar_ladrillos(frame, ind_x, click_realizado)

        elif ESTADO_ACTUAL == "JUEGO_5": # <--- NUEVO BLOQUE
             # Pasamos coords para cortar y click para reiniciar/salir
             frame = jugar_ninja(frame, ind_x, ind_y, click_realizado)

        elif ESTADO_ACTUAL == "JUEGO_6": # <--- NUEVO BLOQUE
             # IMPORTANTE: Pasamos pul_x y pul_y también
             frame = jugar_pintar(frame, ind_x, ind_y, pul_x, pul_y, click_realizado)

        cv2.imshow("Proyecto Multijuego CV", frame)
        if cv2.waitKey(1) & 0xFF == 27: # ESC para salir
            break

cap.release()
cv2.destroyAllWindows()