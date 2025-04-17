
import numpy as np
import socket
import time
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.metrics import mean_squared_error

# Load model and brainwave data
model = load_model(r"C:\Users\Sri_V\Downloads\best_combined_model_cleaned.h5", compile=False)
brainwave_df = pd.read_csv("C:\\Users\\Sri_V\\Desktop\\calculated_brain_wave_frequencies.csv")

# Extract just the brainwave features
features = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]
brainwave_data = brainwave_df[features].values

# Parameters
seq_length = 10
steps_per_sequence = 50
z_fixed = -24

# Define function to send cube parameters to Unity
def send_cube(x, y, z, r, t):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("localhost", 12345))
        message = f"{x},{y},{z},{r},{t}"
        client_socket.sendall(message.encode('ascii'))
        client_socket.close()
    except Exception as e:
        print(f"Socket Error: {e}")

# MCMC to minimize error between predicted and actual brainwave
def mcmc_optimize(predicted_next, actual_next, context_window, steps=50, T=1.0):
    current = np.array([1, 1, z_fixed, 0, 1])
    best = current
    best_score = -np.inf

    for _ in range(steps):
        # Generate proposal
        proposal = current + np.random.normal(scale=[1, 1, 0, 1, 1], size=5)

        # Normalize x (mirror logic from your data)
        x_raw = int(round(proposal[0]))
        if x_raw < 2:
            x = (0 - x_raw) + 2
        else:
            x = (3 - x_raw) - 2
        x = int(np.clip(x, 0, 3))

        # Normalize y
        y = int(np.clip(round(proposal[1]), 0, 2))

        # z is fixed
        z = z_fixed

        # Normalize r (rotation) as multiple of 45 in [0, 315]
        r = int((round(proposal[3]) % 8)) * 45

        # Normalize type (t)
        t = int(np.clip(round(proposal[4]), 0, 1))

        normalized_proposal = np.array([x, y, z, r, t])

        # Simulate effect
        image_seq_dummy = np.zeros((1, seq_length, 512))
        brainwave_seq = np.expand_dims(context_window, axis=0)
        predicted = model.predict([image_seq_dummy, brainwave_seq], verbose=0)[0]

        mse_error = mean_squared_error(predicted_next, actual_next)
        score = -mse_error

        if score > best_score or np.random.rand() < np.exp((score - best_score) / T):
            best = normalized_proposal
            best_score = score
            current = normalized_proposal

    return best

# Store results
results = []

# Main loop: slide through sequences
for i in range(len(brainwave_data) - seq_length - 1):
    context = brainwave_data[i:i+seq_length]
    predicted_next = model.predict([np.zeros((1, seq_length, 512)), np.expand_dims(context, 0)], verbose=0)[0]
    actual_next = brainwave_data[i + seq_length]

    best_cube = mcmc_optimize(predicted_next, actual_next, context)
    send_cube(*best_cube)

    results.append((*best_cube, *predicted_next, *actual_next))
    print(f"[{i}] Sent cube {best_cube} | Predicted vs Actual Δ: {np.round(np.array(predicted_next) - np.array(actual_next), 3)}")
    time.sleep(1.0)
