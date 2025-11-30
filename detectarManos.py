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

    nombres_juegos = ["1. Flappy Hand", "2. Pong", "3. Snake (Vacio)", 
                      "4. Ladrillos (Vacio)", "5. Ninja (Vacio)", "6. Pintar (Vacio)"]
    
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
                elif idx == 2: # Juego 3 (Snake) <--- NUEVO
                    reset_snake()
                    ESTADO_ACTUAL = "JUEGO_3"
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

        cv2.imshow("Proyecto Multijuego CV", frame)
        if cv2.waitKey(1) & 0xFF == 27: # ESC para salir
            break

cap.release()
cv2.destroyAllWindows()