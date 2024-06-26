import socket

def send_cube(x, y, z):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("localhost", 12345))
        message = f"{x},{y},{z}"
        client_socket.sendall(message.encode('ascii'))
        client_socket.close()
    except Exception as e:
        print(f"An error occurred: {e}")

while True:
    try:
        x = float(input("Enter x coordinate: "))
        y = float(input("Enter y coordinate: "))
        z = -24
        send_cube(x, y, z)
    except ValueError:
        print("Invalid input. Please enter numeric values for the coordinates.")
    except KeyboardInterrupt:
        print("Exiting...")
        break