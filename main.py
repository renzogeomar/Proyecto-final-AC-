import cv2
import mediapipe as mp
import math
import config
import juegos 

# Configuración Inicial
cap = cv2.VideoCapture(1)
cap.set(3, config.ANCHO)
cap.set(4, config.ALTO)

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

estado_actual = "MENU"
pinch_anterior = False

with mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7) as hands:
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        
        # Valores por defecto (si no hay mano)
        ind_x, ind_y = -1, -1
        pul_x, pul_y = -1, -1
        click_realizado = False
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Opcional: Dibujar esqueleto (puedes comentarlo si molesta en los juegos)
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                h, w, _ = frame.shape
                ind_x = int(hand_landmarks.landmark[8].x * w)
                ind_y = int(hand_landmarks.landmark[8].y * h)
                pul_x = int(hand_landmarks.landmark[4].x * w)
                pul_y = int(hand_landmarks.landmark[4].y * h)
                
                # Detectar Click (Pinch)
                distancia = math.hypot(ind_x - pul_x, ind_y - pul_y)
                pinch_actual = distancia < 40
                
                # Visualización del Pinch
                color = (0, 255, 0) if pinch_actual else (0, 0, 255)
                cv2.circle(frame, ((ind_x + pul_x)//2, (ind_y + pul_y)//2), 10, color, -1)
                
                if pinch_actual and not pinch_anterior:
                    click_realizado = True
                pinch_anterior = pinch_actual

        # Llamamos a nuestro módulo de juegos
        frame, estado_actual = juegos.gestionar_flujo(
            estado_actual, frame, ind_x, ind_y, pul_x, pul_y, click_realizado
        )

        # ---DETECTAR CIERRE ---
        if estado_actual == "SALIR":
            print("Cerrando aplicación...")
            break # Rompe el bucle while True y cierra el programa

        cv2.imshow("Proyecto AR Multijuego", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()