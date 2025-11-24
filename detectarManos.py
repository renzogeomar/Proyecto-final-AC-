import cv2
import mediapipe as mp
import numpy as np
import random

# --- CONFIGURACIÓN DEL JUEGO ---
ancho_ventana = 640
alto_ventana = 480

# Física del Pájaro
pajaro_x = 100           # Posición fija horizontal
pajaro_y = alto_ventana // 2 # Posición vertical inicial
velocidad_y = 0          # Velocidad actual (caída o subida)
gravedad = 1.5           # Qué tan rápido cae
fuerza_salto = -18       # Qué tan fuerte salta (negativo es hacia arriba)

# Tubos
ancho_tubo = 70
velocidad_tubos = 6
apertura_tubo = 180      # Espacio para pasar
tubos = []               # Lista de tubos [[x, altura_inferior_tubo_arriba]]
frecuencia_tubos = 60    # Cada cuántos frames sale un tubo nuevo
contador_frames = 0

# Estado del juego
juego_activo = False
score = 0
game_over = False

# Variables de la mano
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
estado_anterior_pinch = False # Para detectar solo el "momento" del click

dispositivoCaptura = cv2.VideoCapture(1)
dispositivoCaptura.set(3, ancho_ventana)
dispositivoCaptura.set(4, alto_ventana)

# Función para reiniciar el juego
def reiniciar_juego():
    global pajaro_y, velocidad_y, tubos, score, game_over, juego_activo, contador_frames
    pajaro_y = alto_ventana // 2
    velocidad_y = 0
    tubos = []
    score = 0
    game_over = False
    juego_activo = True
    contador_frames = 0

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7) as hands:

    while True:
        ret, frame = dispositivoCaptura.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        
        # --- PROCESAMIENTO DE MANO (CONTROLADOR) ---
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        salto_detectado = False

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Coordenadas Pulgar e Índice
                h, w, _ = frame.shape
                ind_x = int(hand_landmarks.landmark[8].x * w)
                ind_y = int(hand_landmarks.landmark[8].y * h)
                pul_x = int(hand_landmarks.landmark[4].x * w)
                pul_y = int(hand_landmarks.landmark[4].y * h)

                # Calcular distancia (Pinch)
                distancia = np.hypot(ind_x - pul_x, ind_y - pul_y)
                
                # Visualización del control
                color = (0, 0, 255) # Rojo (no salto)
                estado_actual_pinch = False
                
                if distancia < 30: # UMBRAL DE SALTO
                    color = (0, 255, 0) # Verde (salto activo)
                    estado_actual_pinch = True
                
                # Lógica de detección de FLANCO (Solo salta cuando recién juntas los dedos)
                if estado_actual_pinch and not estado_anterior_pinch:
                    salto_detectado = True
                
                estado_anterior_pinch = estado_actual_pinch
                
                # Dibujar línea entre dedos
                cv2.circle(frame, ((ind_x + pul_x)//2, (ind_y + pul_y)//2), 15, color, cv2.FILLED)

        # --- LÓGICA DEL JUEGO ---
        
        if juego_activo:
            # 1. Aplicar Salto
            if salto_detectado:
                velocidad_y = fuerza_salto
            
            # 2. Aplicar Gravedad
            velocidad_y += gravedad
            pajaro_y += int(velocidad_y)

            # 3. Mover Tubos
            contador_frames += 1
            if contador_frames >= frecuencia_tubos:
                contador_frames = 0
                altura_random = random.randint(100, alto_ventana - 100 - apertura_tubo)
                tubos.append([ancho_ventana, altura_random])

            for tubo in tubos:
                tubo[0] -= velocidad_tubos

            # Eliminar tubos que salen de pantalla
            if len(tubos) > 0 and tubos[0][0] < -ancho_tubo:
                tubos.pop(0)
                score += 1

            # 4. Detectar Colisiones
            # Suelo y Techo
            if pajaro_y >= alto_ventana or pajaro_y <= 0:
                juego_activo = False
                game_over = True
            
            # Tubos
            pajaro_rect = cv2.boundingRect(np.array([[pajaro_x - 15, pajaro_y - 15], [pajaro_x + 15, pajaro_y + 15]]))
            
            for tubo in tubos:
                x_tubo, y_tubo = tubo
                # Rectángulo tubo superior
                rect_top = (x_tubo, 0, ancho_tubo, y_tubo)
                # Rectángulo tubo inferior
                rect_bot = (x_tubo, y_tubo + apertura_tubo, ancho_tubo, alto_ventana - (y_tubo + apertura_tubo))
                
                # Chequeo simple de colisión (Punto dentro de rectangulo)
                # (Para hacerlo perfecto usaríamos intersección de rectángulos, pero esto funciona bien visualmente)
                if (pajaro_x + 15 > x_tubo and pajaro_x - 15 < x_tubo + ancho_tubo):
                    if (pajaro_y - 15 < y_tubo) or (pajaro_y + 15 > y_tubo + apertura_tubo):
                        juego_activo = False
                        game_over = True

        # --- DIBUJADO DEL JUEGO (RENDER) ---
        
        # Dibujar Tubos
        for tubo in tubos:
            x, y = tubo
            # Tubo Arriba (Verde)
            cv2.rectangle(frame, (x, 0), (x + ancho_tubo, y), (0, 200, 0), cv2.FILLED)
            cv2.rectangle(frame, (x, 0), (x + ancho_tubo, y), (0, 100, 0), 2) # Borde
            # Tubo Abajo (Verde)
            cv2.rectangle(frame, (x, y + apertura_tubo), (x + ancho_tubo, alto_ventana), (0, 200, 0), cv2.FILLED)
            cv2.rectangle(frame, (x, y + apertura_tubo), (x + ancho_tubo, alto_ventana), (0, 100, 0), 2) # Borde

        # Dibujar Pájaro (Amarillo)
        cv2.circle(frame, (pajaro_x, pajaro_y), 20, (0, 255, 255), cv2.FILLED)
        cv2.circle(frame, (pajaro_x, pajaro_y), 20, (0, 0, 0), 2) # Borde
        # Ojo del pájaro
        cv2.circle(frame, (pajaro_x + 8, pajaro_y - 5), 5, (255, 255, 255), cv2.FILLED)
        cv2.circle(frame, (pajaro_x + 10, pajaro_y - 5), 2, (0, 0, 0), cv2.FILLED)

        # UI (Interfaz de Usuario)
        cv2.putText(frame, str(score), (ancho_ventana // 2, 80), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)

        if not juego_activo:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (ancho_ventana, alto_ventana), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0) # Oscurecer fondo
            
            if game_over:
                cv2.putText(frame, "GAME OVER", (140, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
                cv2.putText(frame, f"Score: {score}", (220, 280), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            cv2.putText(frame, "Junta dedos para JUGAR", (80, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

            if salto_detectado:
                reiniciar_juego()

        cv2.imshow('Flappy Hand', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

dispositivoCaptura.release()
cv2.destroyAllWindows()