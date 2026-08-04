# Arduino-Based-Air-Defense-System-
Automated Air Defense System Prototype (Arduino &amp; OpenCV)

Overview

The system captures live webcam video, locates a target using OpenCV (HSV color segmentation or skin-tone/contour detection for hand tracking), and calculates its offset from the frame center. That offset drives incremental pan/tilt servo corrections sent over serial to an Arduino, which also fires a laser pointer once the target is within a tolerance window and reads back distance from an ultrasonic sensor.

**Features**
Real-time object detection and tracking via OpenCV
Automatic two-axis (pan/tilt) servo alignment toward the tracked target
Laser-pointer trigger on target lock
Ultrasonic distance measurement with a configurable proximity threshold
Simple Tkinter GUI to start/stop tracking
Graceful fallback if no Arduino is connected (runs vision-only for testing)

**Hardware**
Arduino Uno (or compatible)
Pan-tilt servo bracket (2x servos)
USB webcam
HC-SR04 ultrasonic distance sensor
Laser pointer module
(Optional) LCD for status display, buzzer for proximity alert
