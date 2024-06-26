import socket
import random
import time
def send_cube(x, y, z, r, s):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("localhost", 12345))
        message = f"{x},{y},{z},{r},{s}"
        client_socket.sendall(message.encode('ascii'))
        client_socket.close()
    except Exception as e:
        print(f"An error occurred: {e}")

while True:
    try:
        x = float(input("Enter x coordinate: "))
        y = float(input("Enter y coordinate: "))
        z = -24
        # r = random.randint(0,7)*45
        r = int(input("Enter rotation (0(0), 1(45), 2(90), 3(135), 4(180), 5(225), 6(270), 7(315): "))
        r = r*45
        s = int(input("Enter speed: "))
        time.sleep(1)
        print("sent")
        send_cube(x, y, z, r, s)
    except ValueError:
        print("Invalid input. Please enter numeric values for the coordinates.")
    except KeyboardInterrupt:
        print("Exiting...")
        break