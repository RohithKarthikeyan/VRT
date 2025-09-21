import os
import socket
import threading
import time
from io import BytesIO
from datetime import datetime

import numpy as np
import mne
from PIL import Image

from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from tensorflow.keras.layers import GlobalAveragePooling2D

from sklearn.metrics import mean_squared_error

from pylsl import StreamInlet, resolve_byprop
from mne.time_frequency import tfr_multitaper

# ============================== CONFIG ==============================
MODEL_PATH = "/Users/pragnasrivellanki/Desktop/best_concentration_model.h5"  # <-- your scalar model
Z_FIXED = -24
SEQ_LENGTH = 10

# Ports
UNITY_SEND_PORT = 12345     # where we send "x,y,z,r,t"
UNITY_IMAGE_PORT = 5001     # where we receive screenshots (raw bytes)

# EEG
EEG_SFREQ = 256
EEG_MIN_SAMPLES = 200
EEG_DURATION_SEC = 2.0
EEG_MAX_RETRIES = 5

# Targeting
TARGET_UP_STEP = 0.15  # aim to boost concentration by +0.15 (clipped to 1.0)

# ====================================================================

# ---------------------- Load Model & VGG -----------------------------
model = load_model(MODEL_PATH, compile=False)

# Expect 2 inputs: [images, brainwaves]
# Shapes like: [(None, T, 512), (None, T, BW_DIM)]
if isinstance(model.input_shape, list) and len(model.input_shape) == 2:
    IMG_TIMESTEPS, IMG_DIM = model.input_shape[0][1], model.input_shape[0][2]
    BW_TIMESTEPS, BW_DIM  = model.input_shape[1][1], model.input_shape[1][2]
else:
    raise RuntimeError("Expected a two-input model: [image_seq, brain_seq].")

if IMG_TIMESTEPS != SEQ_LENGTH or BW_TIMESTEPS != SEQ_LENGTH:
    print(f"⚠️ Model timesteps ({IMG_TIMESTEPS},{BW_TIMESTEPS}) != SEQ_LENGTH ({SEQ_LENGTH}). Proceeding anyway.")

# VGG16 feature extractor (512-D after GAP)
vgg_base = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
vgg_model = Model(inputs=vgg_base.input, outputs=GlobalAveragePooling2D()(vgg_base.output))

# ---------------------- EEG Helpers ------------------------------
def get_live_eeg_data(duration=EEG_DURATION_SEC, min_samples=EEG_MIN_SAMPLES, max_retries=EEG_MAX_RETRIES):
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

    print("⏳ Waiting 2 seconds for buffer to fill...")
    time.sleep(2)

    for attempt in range(max_retries):
        eeg_data = []
        start = time.time()
        while (time.time() - start) < duration:
            chunk, _ = inlet.pull_chunk(timeout=1.0)
            if chunk:
                eeg_data.extend(chunk)

        eeg_data = np.array(eeg_data)
        print(f"📏 EEG chunk attempt {attempt+1}: {eeg_data.shape[0]} samples")

        if eeg_data.shape[0] >= min_samples:
            return eeg_data.T[:4]  # TP9, AF7, AF8, TP10

        print("⚠️ EEG chunk too short. Retrying...")
        time.sleep(1)

    print("❌ Failed to get a full EEG chunk after retries.")
    return None

def compute_band_vector_5(eeg_chunk, sfreq=EEG_SFREQ):
    """
    Returns normalized 5-band vector: [Delta, Theta, Alpha, Beta, Gamma], each in 0..1
    """
    info = mne.create_info(ch_names=["TP9", "AF7", "AF8", "TP10"], sfreq=sfreq, ch_types=["eeg"]*4)
    raw = mne.io.RawArray(eeg_chunk, info)
    freqs = np.arange(0.5, 100, 1.0)
    n_cycles = freqs / 2
    tfr = tfr_multitaper(raw, freqs=freqs, n_cycles=n_cycles, time_bandwidth=4.0, return_itc=False, n_jobs=1)

    bands = {"Delta": (0.5, 4), "Theta": (4, 8), "Alpha": (8, 13), "Beta": (13, 30), "Gamma": (30, 100)}
    feats = []
    for fmin, fmax in bands.values():
        idx = np.logical_and(freqs >= fmin, freqs <= fmax)
        # mean over channels & freqs, keep time; then mean over time
        band_power = np.abs(tfr.data[:, idx, :]).mean(axis=(0, 1)).mean()
        feats.append(band_power)

    feats = np.array(feats, dtype=float)
    # normalize robustly to 0..1
    mn, mx = feats.min(), feats.max()
    denom = (mx - mn) if (mx - mn) > 1e-12 else 1.0
    return (feats - mn) / denom

def adapt_brain_vec_to_dim(bands5, target_dim):
    """
    The model expects BW_DIM features per timestep. We have 5 band features.
    Map to target_dim by tiling & truncation.
    """
    if target_dim == 5:
        return bands5
    # tile and slice
    tiled = np.resize(bands5, target_dim)
    return tiled

# ---------------------- Image Feature Extraction -------------------
def extract_image_feature_from_bytes(img_bytes):
    image = Image.open(BytesIO(img_bytes)).convert("RGB")
    image = image.resize((224, 224))
    img_array = preprocess_input(np.expand_dims(np.array(image), axis=0))
    feat = vgg_model.predict(img_array, verbose=0)[0]  # 512-d
    return feat

# ---------------------- Unity I/O ------------------------------
def send_cube_directly(x, y, z, r, t, host="localhost", port=UNITY_SEND_PORT):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.5)
            sock.connect((host, port))
            msg = f"{x},{y},{z},{r},{t}"
            sock.sendall(msg.encode("ascii"))
            print(f"📦 Cube sent to Unity via port {port}: {msg}")
    except Exception as e:
        print(f"❌ Cube send error: {e}")

# ---------------------- MCMC (Heuristic — Option 1) --------------
def clamp_int(v, lo, hi):
    return int(np.clip(v, lo, hi))

def propose_neighbor(action):
    """
    action: [x(0..3), y(0..2), z(fixed), r in {0,45,..,315}, t in {0,1}]
    """
    x, y, z, r, t = action
    which = np.random.randint(0, 4)  # tweak x/y/r/t; z fixed
    if which == 0:
        x = clamp_int(x + np.random.choice([-1, 1]), 0, 3)
    elif which == 1:
        y = clamp_int(y + np.random.choice([-1, 1]), 0, 2)
    elif which == 2:
        r = (r + np.random.choice([-45, 45])) % 360
    else:
        t = 1 - t
    # guard rules
    if (r == 0 and y == 2):
        y = np.random.choice([0, 1])
    elif (r == 180 and y == 0):
        y = np.random.choice([1, 2])
    return np.array([x, y, z, r, t], dtype=int)

def expected_conc_delta_from_action(action):
    """
    Heuristic: small delta added to the model's scalar prediction (0..1).
    Positive => higher concentration.
    """
    x, y, z, r, t = action
    delta = 0.0

    # Type: treat 1 as more focus-demanding -> modest boost
    if t == 1:
        delta += 0.08
    else:
        delta -= 0.02

    # Moderate rotations helpful, extremes at edges harmful
    if r in (45, 315, 135, 225):
        delta += 0.03
    if (r in (0, 180)) and (y in (0, 2)):
        delta -= 0.05

    # Lane centering bonus
    delta += (2 - abs(x - 1.5)) * 0.015  # ~0..0.03

    return float(np.clip(delta, -0.15, 0.15))

def score_action_scalar(action, base_pred_conc, target_conc):
    """
    Score = negative squared error between (pred + action_delta) and target.
    """
    adj = np.clip(base_pred_conc + expected_conc_delta_from_action(action), 0.0, 1.0)
    err = adj - target_conc
    return -(err * err)

def mcmc_optimize_scalar(predicted_conc_scalar, target_conc_scalar, steps=60, T=1.0, z_fixed=Z_FIXED):
    current = np.array([1, 1, z_fixed, 0, 1], dtype=int)
    curr_score = score_action_scalar(current, predicted_conc_scalar, target_conc_scalar)
    best, best_score = current.copy(), curr_score

    for _ in range(steps):
        proposal = propose_neighbor(current)
        prop_score = score_action_scalar(proposal, predicted_conc_scalar, target_conc_scalar)
        # Metropolis vs current
        accept = (prop_score > curr_score) or (np.random.rand() < np.exp((prop_score - curr_score) / max(T, 1e-6)))
        if accept:
            current, curr_score = proposal, prop_score
            if curr_score > best_score:
                best, best_score = current.copy(), curr_score

    x, y, z, r, t = best
    return [int(x), int(y), int(z), int(r), int(t)]

# ---------------------- Connection Handler -----------------------
def handle_unity_connection(conn, addr, eeg_seq, img_seq, brain_dim):
    try:
        # 1) receive the full image bytes
        img_data = b''
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            img_data += chunk

        # 2) extract 512-D VGG feature
        img_feat = extract_image_feature_from_bytes(img_data)  # (512,)
        img_seq.append(img_feat)

        # 3) pull live EEG -> 5 bands -> adapt to brain_dim
        eeg_chunk = get_live_eeg_data()
        if eeg_chunk is None:
            print("⚠️ EEG data not available, skipping this frame.")
            return

        bands5 = compute_band_vector_5(eeg_chunk)
        brain_vec = adapt_brain_vec_to_dim(bands5, brain_dim)  # (brain_dim,)
        eeg_seq.append(brain_vec)

        # 4) Log sequence growth
        print(f"🧠 Brain seq: {len(eeg_seq)}/{SEQ_LENGTH} ; 🖼️ Image seq: {len(img_seq)}/{SEQ_LENGTH}")

        # 5) If we have enough history, predict & MCMC
        if len(eeg_seq) >= SEQ_LENGTH and len(img_seq) >= SEQ_LENGTH:
            images = np.array(img_seq[-SEQ_LENGTH:]).reshape(1, SEQ_LENGTH, IMG_DIM)   # (1,T,512)
            brain  = np.array(eeg_seq[-SEQ_LENGTH:]).reshape(1, SEQ_LENGTH, brain_dim) # (1,T,BW_DIM)

            # model predicts scalar concentration in [0,1]
            pred_conc = float(model.predict([images, brain], verbose=0)[0][0])
            target_conc = float(np.clip(pred_conc + TARGET_UP_STEP, 0.0, 1.0))

            best_cube = mcmc_optimize_scalar(pred_conc, target_conc, steps=60, T=1.0, z_fixed=Z_FIXED)
            send_cube_directly(*best_cube)
        else:
            # warm-up default
            send_cube_directly(1, 1, Z_FIXED, 45, 1)

    except Exception as e:
        print(f"❌ Handler error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

# ---------------------- TCP Socket Server ------------------------
def start_server():
    eeg_seq = []  # list of vectors length BW_DIM
    img_seq = []  # list of 512-D VGG features

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", UNITY_IMAGE_PORT))
    server.listen(5)
    print(f"🖼️ Screenshot server listening on port {UNITY_IMAGE_PORT}...")

    while True:
        conn, addr = server.accept()
        print(f"📥 Image received from {addr}")
        t = threading.Thread(target=handle_unity_connection, args=(conn, addr, eeg_seq, img_seq, BW_DIM), daemon=True)
        t.start()

# ---------------------- MAIN ------------------------
if __name__ == "__main__":
    try:
        print("⚠️ Make sure to run 'muselsl stream' in another terminal before this.")
        start_server()
    except KeyboardInterrupt:
        print("👋 Exiting.")
