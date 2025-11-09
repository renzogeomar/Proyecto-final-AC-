import cv2
import mediapipe as mp
## import pygame

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

dispositivoCaptura = cv2.VideoCapture(0)

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5) as hands:

    while True:
        ret, frame = dispositivoCaptura.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        cv2.imshow('Detección de Manos', frame)

        if cv2.waitKey(1) & 0xFF == 27:  # Presiona 'Esc' para salir
            break

dispositivoCaptura.release()
cv2.destroyAllWindows()