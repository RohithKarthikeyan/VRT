import socket
import time
import json

# Explicit mapping for Beat Saber vertical layers
LAYER0_Y = 0.0      # fine as-is
LAYER1_Y = 1.0      # fine as-is
LAYER2_Y = 1.5      # lower than 2.0 so blocks aren't too high

LAYER_Y_MAP = {
    0: LAYER0_Y,
    1: LAYER1_Y,
    2: LAYER2_Y,
}

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
        type_ = note.get('c')

        # Mirror x as before
        if lineIndex < 2:
            lineIndex = (0 - lineIndex) + 2
        if lineIndex > 1:
            lineIndex = (3 - lineIndex) - 2

        # Map Beat Saber layer -> VR height
        vr_y = LAYER_Y_MAP.get(lineLayer, LAYER1_Y)  # default to middle if weird value

        # Timing
        current_time = time.time()
        wait_time = start_time + elapsed_time - current_time
        if wait_time > 0:
            time.sleep(wait_time)
        
        send_cube(lineIndex, vr_y, -24, cutDirection * 45, type_)

# Example usage
# read_beat_saber_data(r'C:\Users\Sri_V\Desktop\VRT\Level\NormalStandard.dat')
