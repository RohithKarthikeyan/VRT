import socket
import threading
import time
import numpy as np
import mne
from io import BytesIO
from PIL import Image
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.layers import GlobalAveragePooling2D
from pylsl import StreamInlet, resolve_byprop
import tkinter as tk
from tkinter import ttk

# -------- Load model --------
model = load_model("/Users/pragnasrivellanki/Desktop/Game_Data/best_concentration_model.h5", compile=False)
scaler = StandardScaler()
z_fixed = -24
seq_length = 10

# External concentration control
concentration_control = {'target': 0.6}

# -------- GUI Slider --------
def launch_control_gui():
    def update_concentration(val):
        concentration_control['target'] = float(val)
        label_var.set(f"Target Concentration: {float(val):.2f}")
    
    window = tk.Tk()
    window.title("Concentration Control")

    label_var = tk.StringVar(value=f"Target Concentration: {concentration_control['target']:.2f}")
    ttk.Label(window, textvariable=label_var, font=("Arial", 14)).pack(pady=10)

    slider = ttk.Scale(window, from_=0.0, to=1.0, orient='horizontal', command=update_concentration)
    slider.set(concentration_control['target'])
    slider.pack(fill='x', padx=20, pady=10)

    window.mainloop()

# -------- VGG16 Feature Extractor --------
vgg_base = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
vgg_model = Model(inputs=vgg_base.input, outputs=GlobalAveragePooling2D()(vgg_base.output))

# -------- EEG Functions --------
def get_live_eeg_data(duration=2.0, min_samples=200, max_retries=5):
    inlet = None
    for attempt in range(max_retries):
        streams = resolve_byprop('type', 'EEG', timeout=5)
        if streams:
            inlet = StreamInlet(streams[0], max_chunklen=12)
            break
        time.sleep(2)
    if inlet is None:
        return None
    time.sleep(2)
    for _ in range(max_retries):
        eeg_data = []
        start = time.time()
        while (time.time() - start) < duration:
            chunk, _ = inlet.pull_chunk(timeout=1.0)
            if chunk:
                eeg_data.extend(chunk)
        eeg_data = np.array(eeg_data)
        if eeg_data.shape[0] >= min_samples:
            return eeg_data.T[:4]
        time.sleep(1)
    return None

def nextpow2(i):
    n = 1
    while n < i:
        n *= 2
    return n

def compute_combined_band_features(eegdata, Fs):
    winSampleLength, nbCh = eegdata.shape
    w = np.hamming(winSampleLength)
    dataWinCentered = eegdata - np.mean(eegdata, axis=0)
    dataWinCenteredHam = (dataWinCentered.T * w).T
    NFFT = nextpow2(winSampleLength)
    Y = np.fft.fft(dataWinCenteredHam, n=NFFT, axis=0) / winSampleLength
    PSD = 2 * np.abs(Y[0:int(NFFT/2), :])
    f = Fs / 2 * np.linspace(0, 1, int(NFFT/2))

    def band_power(indices):
        return np.mean(PSD[indices, :], axis=0)

    ind_delta = np.where(f < 4)[0]
    ind_theta = np.where((f >= 4) & (f <= 8))[0]
    ind_alpha = np.where((f >= 8) & (f <= 12))[0]
    ind_beta = np.where((f >= 12) & (f <= 30))[0]

    delta = np.mean(band_power(ind_delta))
    theta = np.mean(band_power(ind_theta))
    alpha = np.mean(band_power(ind_alpha))
    beta = np.mean(band_power(ind_beta))

    features = {
        'log_delta': np.log10(delta + 1e-8),
        'log_theta': np.log10(theta + 1e-8),
        'log_alpha': np.log10(alpha + 1e-8),
        'log_beta': np.log10(beta + 1e-8),
        'log_theta_beta_ratio': np.log10((theta + 1e-8) / (beta + 1e-8)),
        'log_alpha_theta_ratio': np.log10((alpha + 1e-8) / (theta + 1e-8)),
        'log_alpha_beta_ratio': np.log10((alpha + 1e-8) / (beta + 1e-8)),
    }
    return np.array(list(features.values()))

# -------- MCMC Optimizer --------
def mcmc_optimize(concentration, context, image_seq, steps=50, T=1.0):
    current = np.array([1, 1, z_fixed, 0, 1])
    best = current
    best_score = -np.inf
    for _ in range(steps):
        proposal = current + np.random.normal(scale=[1, 1, 0, 1, 1], size=5)
        x = int(np.clip((0 - round(proposal[0])) + 2 if proposal[0] < 2 else (3 - round(proposal[0])) - 2, 0, 3))
        y = int(np.clip(round(proposal[1]), 0, 2))
        z = z_fixed
        r = int((round(proposal[3]) % 8)) * 45
        t = int(np.clip(round(proposal[4]), 0, 1))
        deviation = concentration - concentration_control['target']
        score = -abs(deviation)
        if score > best_score or np.random.rand() < np.exp((score - best_score) / T):
            best, best_score, current = [x, y, z, r, t], score, [x, y, z, r, t]
    return best

# -------- Send to Unity --------
def send_cube_directly(x, y, z, r, t):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("localhost", 12345))
            msg = f"{x},{y},{z},{r},{t}"
            sock.sendall(msg.encode("ascii"))
            print(f"📦 Cube sent to Unity: {msg}")
    except Exception as e:
        print(f"❌ Cube send error: {e}")

# -------- Handle Screenshot Upload --------
def handle_unity_connection(conn, addr, eeg_seq, image_seq):
    try:
        img_data = b''
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            img_data += chunk
        image = Image.open(BytesIO(img_data)).convert("RGB")
        image = image.resize((224, 224))
        image_array = preprocess_input(np.expand_dims(np.array(image), axis=0))
        image_feat = vgg_model.predict(image_array, verbose=0).flatten()
        eeg_chunk = get_live_eeg_data()
        if eeg_chunk is None:
            return
        eeg_features = compute_combined_band_features(eeg_chunk.T, fs=256)
        eeg_seq.append(eeg_features)
        image_seq.append(image_feat)
        if len(eeg_seq) >= seq_length and len(image_seq) >= seq_length:
            context = np.array(eeg_seq[-seq_length:])
            images = np.array(image_seq[-seq_length:]).reshape(1, seq_length, -1)
            concentration = model.predict([images, np.expand_dims(context, 0)], verbose=0)[0][0]
            best_cube = mcmc_optimize(concentration, context, images)
            send_cube_directly(*best_cube)
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

# -------- Start TCP Server --------
def start_server():
    eeg_seq = []
    image_seq = []
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5001))
    server.listen(5)
    print("🖼️ Screenshot server listening on port 5001...")
    threading.Thread(target=launch_control_gui, daemon=True).start()
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_unity_connection, args=(conn, addr, eeg_seq, image_seq)).start()

# -------- Main --------
if __name__ == "__main__":
    try:
        print("⚠️ Make sure to run 'muselsl stream' in another terminal before this.")
        start_server()
    except KeyboardInterrupt:
        print("👋 Exiting.")
