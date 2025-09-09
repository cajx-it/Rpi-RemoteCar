from flask import Flask, Response, request, render_template
from picamera2 import Picamera2
import cv2
from libcamera import Transform
from gpiozero import Motor, Servo
from gpiozero.pins.pigpio import PiGPIOFactory
import os
import pygame
import time
import threading
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"

app = Flask(__name__)

# ---------------- Car Controller ---------------- #
class CarController:
    def __init__(self, forleftmotor, backleftmotor, forrightmotor, backrightmotor, servoX, servoY, factory):
        self.servoValueX = 0
        self.servoValueY = 0
        self.motorLeft = Motor(forleftmotor, backleftmotor, pin_factory=factory)
        self.motorRight = Motor(forrightmotor, backrightmotor, pin_factory=factory)
        self.servoX = Servo(servoX, pin_factory=factory)
        self.servoY = Servo(servoY, pin_factory=factory)
        self.motorspeed = 0.4
        self.servoXValue = 0
        self.servoYValue = 0

    def movement(self, direction):
        if direction == "forward":
            print("forward")
            self.motorLeft.forward(self.motorspeed)
            self.motorRight.forward(self.motorspeed)
        elif direction == "backward":
            print("backward")
            self.motorLeft.backward(self.motorspeed)
            self.motorRight.backward(self.motorspeed)
        elif direction == "left":
            print("left")
            self.motorRight.backward(self.motorspeed)
            self.motorLeft.forward(self.motorspeed)
        elif direction == "right":
            print("right")
            self.motorLeft.backward(self.motorspeed)
            self.motorRight.forward(self.motorspeed)
        elif direction == "stop":
            self.motorLeft.stop()
            self.motorRight.stop()

    def servomovement(self, direction):
        if direction == "left":
            self.servoValueX += 0.1
            self.servoValueX = max(-1, min(1, self.servoValueX))  # Clamp the value
            self.servoX.value = round(self.servoValueX, 1)
            print(round(self.servoValueX, 1))
        elif direction == "right":
            self.servoValueX -= 0.1
            self.servoValueX = max(-1, min(1, self.servoValueX))  # Clamp the value
            self.servoX.value = round(self.servoValueX, 1)
            print(round(self.servoValueX, 1))
        elif direction == "up":
            self.servoValueY += 0.1
            self.servoValueY = max(-1, min(1, self.servoValueY))  # Clamp the value
            self.servoY.value = round(self.servoValueY, 1)
            print(round(self.servoValueY, 1))
        elif direction == "down":
            self.servoValueY -= 0.1
            self.servoValueY = max(-1, min(1, self.servoValueY))  # Clamp the value
            self.servoY.value = round(self.servoValueY, 1)
            print(round(self.servoValueY, 1))
        elif direction == "reset":
            self.servoValueX = 0
            self.servoValueY = 0
            self.servoYValue = max(-1, min(1, self.servoYValue))
            self.servoXValue = max(-1, min(1, self.servoXValue))
            self.servoY.value = round(self.servoYValue, 1)
            self.servoX.value = round(self.servoXValue, 1)




# ---------------- Video Stream ---------------- #
class RaspberryPiWebStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        self.video_config = self.picam2.create_video_configuration(
            main={"size": (320, 240), "format": "RGB888"},
            controls={"FrameDurationLimits": (66666, 66666)},
            transform=Transform(hflip=True, vflip=True)
        )
        self.picam2.configure(self.video_config)
        self.picam2.start()

        self.toggle_count = 0
        self.use_grayscale = False


    def toggle_stream_mode(self):
        self.toggle_count += 1
        self.use_grayscale = (self.toggle_count % 2 == 1)
        print(f"Button pressed: {self.toggle_count} times — "
              f"{'Grayscale' if self.use_grayscale else 'Color'} mode")

    def generate_frames(self):
        while True:
            frame = self.picam2.capture_array()

            if self.use_grayscale:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ---------------- Bluetooth Gamepad ---------------- #
class BluetoothController:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            print("No joystick found.")
            sys.exit(1)

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print("Controller connected:", self.joystick.get_name())

    def Mget_direction(self, x, y, threshold=0.5):
        if y < -threshold:
            return "up"
        elif y > threshold:
            return "down"
        elif x < -threshold:
            return "left"
        elif x > threshold:
            return "right"
        return None

    def Sget_direction(self, x, y, threshold=0.5):
        if y < -threshold:
            return "up"
        elif y > threshold:
            return "down"
        elif x < -threshold:
            return "left"
        elif x > threshold:
            return "right"
        return None

    def fun(self, car, stream):

        while True:
            pygame.event.pump()

            # MOTORS
            left_x = self.joystick.get_axis(0)
            left_y = self.joystick.get_axis(1)

            direction = self.Mget_direction(left_x, left_y)

            if self.joystick.get_button(11):
                car.servomovement("reset")
            car.servomovement(direction)

            if self.joystick.get_button(12):
                stream.toggle_stream_mode()

            # MOTOR

            if self.joystick.get_button(2):
                car.movement("forward")
            elif self.joystick.get_button(3):
                car.movement("left")
            elif self.joystick.get_button(1):
                car.movement("right")
            elif self.joystick.get_button(0):
                car.movement("backward")
            else:
                car.movement("stop")

            time.sleep(0.1)


# ---------------- Flask Routes ---------------- #
@app.route('/')
def home():
    return render_template('index2.html')

@app.route('/video_feed')
def video_feed():
    return Response(stream.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# ---------------- Main Program ---------------- #
if __name__ == "__main__":
    factory = PiGPIOFactory()
    car = CarController(18, 19, 13, 12, 21, 20, factory)
    stream = RaspberryPiWebStreamer()
    blue = BluetoothController()

    controller_thread = threading.Thread(target=blue.fun, args=(car, stream), daemon=True)
    controller_thread.start()

    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
