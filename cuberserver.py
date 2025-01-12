import socket
import random
import time
import json
def send_cube(x, y, z, r, t):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("localhost", 12345))
        message = f"{x},{y},{z},{r},{t}"
        client_socket.sendall(message.encode('ascii'))
        client_socket.close()
    except Exception as e:
        print(f"An error occurred: {e}")

def read_beat_saber_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    notes = data.get('colorNotes', [])
    
    start_time = time.time()
    
    for note in notes:
        elapsed_time = note.get('b')
        lineIndex = note.get('x')
        lineLayer = note.get('y')
        cutDirection = note.get('d')
        type = note.get('c')
        if lineIndex < 2:
            lineIndex = (0-lineIndex) + 2
        if lineIndex > 1:
            lineIndex = (3-lineIndex) - 2
            
        # Calculate the time to wait until the next beat should be processed
        current_time = time.time()
        wait_time = start_time + elapsed_time - current_time
        
        if wait_time > 0:
            time.sleep(wait_time)
        
        send_cube(lineIndex, lineLayer, -24, cutDirection*45, type)

# Example usage:
# Assuming the data is saved in a file named 'beat_saber_level.dat'
read_beat_saber_data(r'C:\Users\Sri_V\Desktop\VRT\Level\NormalStandard.dat')

# while True:
#     try:
#         x = float(input("Enter x coordinate: ")) # x coordinate
#         y = float(input("Enter y coordinate: ")) # y coordinate
#         z = -24 #keep this at -24 unless you want to change how far back the objects spawn.
#         r = int(input("Enter rotation (0(0), 1(45), 2(90), 3(135), 4(180), 5(225), 6(270), 7(315): ")) # rotation
#         r = r*45 #convert to degrees
#         t = int(input("Enter type (0=blue,1=red,2=bomb): ")) # type of object
#         time.sleep(1)
#         print("sent")
#         send_cube(x, y, z, r, t)
#     except ValueError:
#         print("Invalid input. Please enter numeric values for the coordinates.")
#     except KeyboardInterrupt:
#         print("Exiting...")
#         break