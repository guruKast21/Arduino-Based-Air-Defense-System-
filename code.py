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
horizontal_angle = 90
vertical_angle = 90
FRAME_CENTER_TOLERANCE = 30  # pixels

def move_servo(axis, angle):
    if arduino:
        angle = int(max(0, min(180, angle)))
        command = f"{axis}{angle}\n"
        arduino.write(command.encode())
        print("Sent:", command.strip())

def fire_laser():
    if arduino:
        arduino.write(b'L\n')
        print("Sent: L")

def process_hand(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_skin = np.array([0, 30, 60], dtype=np.uint8)
    upper_skin = np.array([20, 150, 255], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower_skin, upper_skin)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    center = None

    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > 1000:
            M = cv2.moments(largest)
            if M['m00'] != 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                center = (cx, cy)
                cv2.circle(frame, center, 10, (0, 255, 0), -1)

    return frame, center, mask

def tracking_loop():
    global horizontal_angle, vertical_angle, running

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Webcam could not be opened.")
        return

    move_servo('H', horizontal_angle)
    move_servo('V', vertical_angle)

    while running:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("⚠️ Frame not captured.")
            continue

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        frame_center = (w // 2, h // 2)

        processed, center, mask = process_hand(frame)

        cv2.line(processed, (frame_center[0], 0), (frame_center[0], h), (255, 0, 0), 1)
        cv2.line(processed, (0, frame_center[1]), (w, frame_center[1]), (255, 0, 0), 1)
        cv2.imshow("Mask", mask)

        if center:
            dx = center[0] - frame_center[0]
            dy = center[1] - frame_center[1]

            if abs(dx) < FRAME_CENTER_TOLERANCE and abs(dy) < FRAME_CENTER_TOLERANCE:
                fire_laser()
                cv2.putText(processed, "FIRING", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                # ✅ Fixed inverted X-axis
                if dx > FRAME_CENTER_TOLERANCE:
                    horizontal_angle = min(180, horizontal_angle + 1)
                elif dx < -FRAME_CENTER_TOLERANCE:
                    horizontal_angle = max(0, horizontal_angle - 1)

                # ✅ Y-direction (normal)
                if dy > FRAME_CENTER_TOLERANCE:
                    vertical_angle = max(0, vertical_angle - 1)
                elif dy < -FRAME_CENTER_TOLERANCE:
                    vertical_angle = min(180, vertical_angle + 1)

                move_servo('H', horizontal_angle)
                move_servo('V', vertical_angle)
        else:
            cv2.putText(processed, "Hand not detected", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Hand Tracker", processed)

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
root.title("Hand Tracking Turret")

tk.Label(root, text="Hand Tracker GUI", font=("Helvetica", 16)).pack(pady=10)
tk.Button(root, text="Start Tracking", width=20, command=start_tracking).pack(pady=5)
tk.Button(root, text="Stop Tracking", width=20, command=stop_tracking).pack(pady=5)
tk.Button(root, text="Exit", width=20, command=lambda: (stop_tracking(), root.destroy())).pack(pady=5)

root.mainloop()
