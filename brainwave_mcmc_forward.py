
import numpy as np
import socket
import time
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.metrics import mean_squared_error

# Load model and brainwave data
model = load_model("/Users/pragnasrivellanki/Desktop/best_combined_model.h5")
brainwave_df = pd.read_csv("/Users/pragnasrivellanki/Desktop/Game_Data/grohith/g1/calculated_brain_wave_frequencies.csv")

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
        proposal = current + np.random.normal(scale=[1, 1, 0, 45, 1], size=5)
        proposal[2] = z_fixed
        proposal[3] = int((proposal[3] // 45) % 8) * 45
        proposal[4] = int(np.clip(round(proposal[4]), 0, 2))

        # Simulate effect: input to model with current sequence + dummy image features (zeros)
        image_seq_dummy = np.zeros((1, seq_length, 512))
        brainwave_seq = np.expand_dims(context_window, axis=0)

        predicted = model.predict([image_seq_dummy, brainwave_seq], verbose=0)[0]

        mse_error = mean_squared_error(predicted_next, actual_next)
        score = -mse_error

        if score > best_score or np.random.rand() < np.exp((score - best_score) / T):
            best = proposal
            best_score = score
            current = proposal

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
