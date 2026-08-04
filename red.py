import cv2
import serial
import tkinter as tk
from threading import Thread
import numpy as np
import time

# === SERIAL SETUP ===
try:
    arduino = serial.Serial('COM3', 19200, timeout=1)
    time.sleep(2)
    print("✅ Arduino connected.")
except:
    arduino = None
    print("⚠️ Arduino not connected.")

# === GLOBALS ===
running = False
horizontal_angle = 130
vertical_angle = 70
FRAME_CENTER_TOLERANCE = 30  # pixels
DISTANCE_THRESHOLD_CM = 20

def move_servo(axis, angle):
    if arduino:
        angle = int(max(0, min(180, angle)))
        arduino.write(f"{axis}{angle}\n".encode())

def fire_laser():
    if arduino:
        arduino.write(b'L\n')

def read_distance():
    if arduino:
        arduino.reset_input_buffer()
        arduino.write(b'D\n')
        time.sleep(0.05)
        try:
            line = arduino.readline().decode().strip()
            if line.isdigit():
                return int(line)
        except:
            return None
    return None

def detect_red_object(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([179, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = cv2.bitwise_or(mask1, mask2)

    kernel = np.ones((5, 5), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    red_mask = cv2.dilate(red_mask, kernel, iterations=2)

    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center = None

    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > 1000:
            x, y, w, h = cv2.boundingRect(largest)
            center = (x + w // 2, y + h // 2)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, center, 5, (255, 0, 0), -1)
            cv2.putText(frame, "RED AREA", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    return frame, center, red_mask

def tracking_loop():
    global horizontal_angle, vertical_angle, running

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Webcam could not be opened.")
        return

    # Initial alignment
    move_servo('V', vertical_angle)
    move_servo('H', horizontal_angle)

    while running:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("⚠️ Frame not captured.")
            continue

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        frame_center = (w // 2, h // 2)

        processed, center, mask = detect_red_object(frame)

        # Draw center lines
        cv2.line(processed, (frame_center[0], 0), (frame_center[0], h), (255, 0, 0), 1)
        cv2.line(processed, (0, frame_center[1]), (w, frame_center[1]), (255, 0, 0), 1)
        cv2.imshow("Red Mask", mask)

        if center:
            dx = center[0] - frame_center[0]
            dy = center[1] - frame_center[1]

            if abs(dx) < FRAME_CENTER_TOLERANCE and abs(dy) < FRAME_CENTER_TOLERANCE:
                fire_laser()
                cv2.putText(processed, "FIRING", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                distance = read_distance()
                if distance is not None and distance < DISTANCE_THRESHOLD_CM:
                    cv2.putText(processed, "⚠️ THREAT NEARBY!", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                # Adjust angles
                if dx > FRAME_CENTER_TOLERANCE:
                    horizontal_angle = min(180, horizontal_angle + 1)
                elif dx < -FRAME_CENTER_TOLERANCE:
                    horizontal_angle = max(0, horizontal_angle - 1)

                if dy > FRAME_CENTER_TOLERANCE:
                    vertical_angle = max(0, vertical_angle - 1)
                elif dy < -FRAME_CENTER_TOLERANCE:
                    vertical_angle = min(180, vertical_angle + 1)

                # ✅ Apply new V first, then H
                move_servo('V', vertical_angle)
                move_servo('H', horizontal_angle)
        else:
            cv2.putText(processed, "Red Object not detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Red Tracker", processed)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def start_tracking():
    global running
    if not running:
        running = True
        Thread(target=tracking_loop).start()

def stop_tracking():
    global running
    running = False

# === GUI ===
root = tk.Tk()
root.title("Red Object Tracking Turret")

tk.Label(root, text="Red Tracker GUI", font=("Helvetica", 16)).pack(pady=10)
tk.Button(root, text="Start Tracking", width=20, command=start_tracking).pack(pady=5)
tk.Button(root, text="Stop Tracking", width=20, command=stop_tracking).pack(pady=5)
tk.Button(root, text="Exit", width=20, command=lambda: (stop_tracking(), root.destroy())).pack(pady=5)

root.mainloop()
