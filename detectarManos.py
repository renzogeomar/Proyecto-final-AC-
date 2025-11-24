import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import math

# --- CONFIGURACIÓN ---
anchura_pantalla, altura_pantalla = pyautogui.size()

# 1. CAMBIO: Reducimos el margen para que el recuadro sea MÁS GRANDE
# Antes era 100, ahora con 20 aprovecharás casi toda la cámara.
cuadro_reduccion = 10
suavizado = 5

# Variables para el suavizado
prev_x, prev_y = 0, 0
curr_x, curr_y = 0, 0

# 2. CAMBIO: Variable para saber si estamos manteniendo el click presionado
clic_presionado = False 

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

dispositivoCaptura = cv2.VideoCapture(0)
dispositivoCaptura.set(3, 640)
dispositivoCaptura.set(4, 480)

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5) as hands:

    while True:
        ret, frame = dispositivoCaptura.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h_cam, w_cam, _ = frame.shape 
        
        # Dibujar el recuadro (Ahora será más grande)
        cv2.rectangle(frame, (cuadro_reduccion, cuadro_reduccion), 
                      (w_cam - cuadro_reduccion, h_cam - cuadro_reduccion), (255, 0, 255), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                
                ind_x = int(hand_landmarks.landmark[8].x * w_cam)
                ind_y = int(hand_landmarks.landmark[8].y * h_cam)
                pul_x = int(hand_landmarks.landmark[4].x * w_cam)
                pul_y = int(hand_landmarks.landmark[4].y * h_cam)

                # Círculo guía en el índice
                cv2.circle(frame, (ind_x, ind_y), 10, (0, 255, 255), cv2.FILLED)

                # --- MOVIMIENTO DEL MOUSE ---
                if ind_x > cuadro_reduccion and ind_x < w_cam - cuadro_reduccion and \
                   ind_y > cuadro_reduccion and ind_y < h_cam - cuadro_reduccion:
                    
                    x3 = np.interp(ind_x, (cuadro_reduccion, w_cam - cuadro_reduccion), (0, anchura_pantalla))
                    y3 = np.interp(ind_y, (cuadro_reduccion, h_cam - cuadro_reduccion), (0, altura_pantalla))

                    curr_x = prev_x + (x3 - prev_x) / suavizado
                    curr_y = prev_y + (y3 - prev_y) / suavizado

                    pyautogui.moveTo(curr_x, curr_y)
                    prev_x, prev_y = curr_x, curr_y

                # --- LÓGICA DE CLICK SOSTENIDO ---
                distancia = math.hypot(ind_x - pul_x, ind_y - pul_y)
                
                # Si la distancia es menor a 30 (dedos juntos)
                if distancia < 30:
                    # Dibujamos un círculo VERDE para indicar que está "agarrando"
                    cv2.circle(frame, (ind_x, ind_y), 15, (0, 255, 0), cv2.FILLED)
                    
                    # Si NO estaba presionado antes, lo presionamos ahora
                    if not clic_presionado:
                        pyautogui.mouseDown() # Mantiene el botón abajo
                        clic_presionado = True
                
                # Si la distancia es mayor a 30 (dedos separados)
                else:
                    # Si ESTABA presionado, lo soltamos ahora
                    if clic_presionado:
                        pyautogui.mouseUp()   # Suelta el botón
                        clic_presionado = False

                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        cv2.imshow('Mouse Virtual - Drag & Drop', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

dispositivoCaptura.release()
cv2.destroyAllWindows()