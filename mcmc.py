import socket
import threading
import time
import numpy as np
import mne
from io import BytesIO
from PIL import Image
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.layers import GlobalAveragePooling2D

from pylsl import StreamInlet, resolve_byprop
from mne.time_frequency import tfr_multitaper

# -------- Load model --------
model = load_model("/Users/pragnasrivellanki/Desktop/best_combined_model.h5", compile=False)
scaler = StandardScaler()
z_fixed = -24
seq_length = 10

# -------- VGG16 Feature Extractor --------
vgg_base = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
vgg_model = Model(inputs=vgg_base.input, outputs=GlobalAveragePooling2D()(vgg_base.output))

# -------- EEG Functions --------
def get_live_eeg_data(duration=1.0, sfreq=256, max_retries=10):
    inlet = None
    for attempt in range(max_retries):
        try:
            print(f"🔎 Searching for EEG stream (attempt {attempt+1}/{max_retries})...")
            streams = resolve_byprop('type', 'EEG', timeout=5)
            if streams:
                inlet = StreamInlet(streams[0], max_chunklen=12)
                print("✅ EEG stream found.")
                break
            else:
                print("⚠️ No EEG stream found yet. Retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"❌ Stream resolution error: {e}")
            time.sleep(2)

    if inlet is None:
        print("❌ Failed to connect to EEG stream after retries.")
        return None

    eeg_data = []
    start = time.time()
    while (time.time() - start) < duration:
        chunk, _ = inlet.pull_chunk(timeout=1.0)
        if chunk:
            eeg_data.extend(chunk)

    eeg_data = np.array(eeg_data)
    if eeg_data.shape[0] < sfreq:
        print("⚠️ EEG data chunk too short.")
        return None

    return eeg_data.T[:4]  # TP9, AF7, AF8, TP10


def compute_band_frequencies(eeg_chunk, sfreq=256):
    info = mne.create_info(ch_names=["TP9", "AF7", "AF8", "TP10"], sfreq=sfreq, ch_types=["eeg"]*4)
    raw = mne.io.RawArray(eeg_chunk, info)
    freqs = np.arange(0.5, 100, 1)
    n_cycles = freqs / 2
    tfr = tfr_multitaper(raw, freqs=freqs, n_cycles=n_cycles, time_bandwidth=4.0, return_itc=False)

    freq_bands = {"Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 13), "Beta": (13, 30), "Gamma": (30, 100)}
    features = []
    for fmin, fmax in freq_bands.values():
        idx = np.logical_and(freqs >= fmin, freqs <= fmax)
        power = np.abs(tfr.data[:, idx, :]).mean(axis=1).sum(axis=0)
        normalized = (power - power.min()) / (power.max() - power.min() + 1e-6)
        features.append((fmin + (fmax - fmin) * (1 - normalized)).mean())
    return np.array(features)

# -------- MCMC Optimizer --------
def mcmc_optimize(predicted, actual, context, image_seq, steps=50, T=1.0):
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
        pred = model.predict([image_seq, np.expand_dims(context, 0)], verbose=0)[0]
        mse = mean_squared_error(predicted, actual)
        score = -mse
        if score > best_score or np.random.rand() < np.exp((score - best_score) / T):
            best, best_score, current = [x, y, z, r, t], score, [x, y, z, r, t]
    return best

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

        eeg_chunk = get_live_eeg_data(duration=1.0)
        if eeg_chunk is None:
            print("⚠️ EEG data not available.")
            return

        eeg_freqs = compute_band_frequencies(eeg_chunk)

        eeg_seq.append(eeg_freqs)
        image_seq.append(image_feat)

        if len(eeg_seq) >= seq_length and len(image_seq) >= seq_length:
            context = np.array(eeg_seq[-seq_length:])
            images = np.array(image_seq[-seq_length:]).reshape(1, seq_length, -1)
            predicted = model.predict([images, np.expand_dims(context, 0)], verbose=0)[0]
            actual = context[-1]
            best_cube = mcmc_optimize(predicted, actual, context, images)

            response = f"{best_cube[0]},{best_cube[1]},{best_cube[2]},{best_cube[3]},{best_cube[4]}"
            conn.sendall(response.encode('ascii'))
            print(f"🎯 Sent cube to Unity: {response}")
        else:
            print("⏳ Waiting for enough data...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

# -------- TCP Socket Server --------
def start_server():
    eeg_seq = []
    image_seq = []

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5001))  # Match Unity's target
    server.listen(5)
    print("🖼️ Screenshot server listening on port 5001...")

    while True:
        conn, addr = server.accept()
        print(f"📥 Image received from {addr}")
        threading.Thread(target=handle_unity_connection, args=(conn, addr, eeg_seq, image_seq)).start()

# -------- MAIN --------
if __name__ == "__main__":
    try:
        print("⚠️ Make sure to run 'muselsl stream' in another terminal before this.")
        start_server()
    except KeyboardInterrupt:
        print("👋 Exiting.")
