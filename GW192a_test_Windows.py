#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import os
import json
import tempfile
import traceback
import time
from datetime import datetime
import sys

# --- Directories and configuration ---
SAVE_DIR = "snapshots"
SETTINGS_DIR = "settings"
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "config.json")
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(SETTINGS_DIR, exist_ok=True)

# --- Utility functions ---
def atomic_save_json(path, data):
    """Atomically save JSON (write to temp file then replace)."""
    tmp_path = None
    try:
        dir_name = os.path.dirname(path) or "."
        fd, tmp_path = tempfile.mkstemp(prefix="tmp_settings_", dir=dir_name, text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        return True
    except Exception:
        traceback.print_exc()
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False

def load_settings():
    """Load settings or create defaults if missing/corrupted."""
    default_settings = {
        "rotation_index": 1,  # 90°
        "map_index": 0,
        "interpolation_index": 0,
        "scale_percent": 600
    }
    if not os.path.exists(SETTINGS_FILE):
        atomic_save_json(SETTINGS_FILE, default_settings)
        return default_settings
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        changed = False
        for k, v in default_settings.items():
            if k not in data:
                data[k] = v
                changed = True
        if changed:
            atomic_save_json(SETTINGS_FILE, data)
        return data
    except Exception:
        traceback.print_exc()
        atomic_save_json(SETTINGS_FILE, default_settings)
        return default_settings

def update_and_save(settings, key, value):
    """Update settings dict and save to disk."""
    settings[key] = value
    success = atomic_save_json(SETTINGS_FILE, settings)
    if not success:
        print("Warning: Failed to save settings to disk.")
    return success

# --- On-screen message system ---
last_message = ""
last_message_time = 0
MESSAGE_DURATION = 2.0  # seconds

def show_message(text):
    global last_message, last_message_time
    last_message = text
    last_message_time = time.time()

# --- Recording state ---
is_recording = False
video_writer = None
video_filename = None
rec_blink_state = False
last_blink_time = 0
BLINK_INTERVAL = 0.5  # seconds

# --- Load persisted settings ---
settings = load_settings()
rotation_index = int(settings.get("rotation_index", 1))
map_index = int(settings.get("map_index", 0))
interpolation_index = int(settings.get("interpolation_index", 0))
scale_percent = int(settings.get("scale_percent", 600))

# --- Parameters ---
min_scale, max_scale, step = 150, 1000, 50
show_text = False
cameraResolution_Horizontal = 96
cameraResolution_Vertical = 96

# --- Rotation modes ---
rotation_modes = [
    None,
    cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_180,
    cv2.ROTATE_90_COUNTERCLOCKWISE
]

# --- Full color maps list (restored) ---
color_maps = [
    cv2.COLORMAP_INFERNO, cv2.COLORMAP_AUTUMN, cv2.COLORMAP_BONE, cv2.COLORMAP_CIVIDIS,
    cv2.COLORMAP_COOL, cv2.COLORMAP_DEEPGREEN, cv2.COLORMAP_HOT, cv2.COLORMAP_HSV,
    cv2.COLORMAP_JET, cv2.COLORMAP_MAGMA, cv2.COLORMAP_OCEAN, cv2.COLORMAP_PARULA,
    cv2.COLORMAP_PINK, cv2.COLORMAP_PLASMA, cv2.COLORMAP_RAINBOW, cv2.COLORMAP_SPRING,
    cv2.COLORMAP_SUMMER, cv2.COLORMAP_TURBO, cv2.COLORMAP_TWILIGHT, cv2.COLORMAP_TWILIGHT_SHIFTED,
    cv2.COLORMAP_VIRIDIS, cv2.COLORMAP_WINTER
]

# --- Full interpolation list (restored) ---
interpolation_type = [
    cv2.INTER_LINEAR_EXACT, cv2.INTER_NEAREST, cv2.INTER_AREA, cv2.INTER_BITS,
    cv2.INTER_BITS2, cv2.INTER_CUBIC, cv2.INTER_LANCZOS4, cv2.INTER_LINEAR
]

# Defensive bounds
rotation_index %= len(rotation_modes)
map_index %= len(color_maps)
interpolation_index %= len(interpolation_type)
scale_percent = max(min(scale_percent, max_scale), min_scale)

# --- Text constants ---
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.4
THICKNESS = 1
TEXT_COLOR = (255, 255, 255)

# --- Initialize camera ---
stream = cv2.VideoCapture(1, cv2.CAP_DSHOW if os.name == 'nt' else 0)
stream.set(cv2.CAP_PROP_FRAME_WIDTH, cameraResolution_Horizontal)
stream.set(cv2.CAP_PROP_FRAME_HEIGHT, cameraResolution_Vertical)

if not stream.isOpened():
    print("Camera open error")
    sys.exit(1)

try:
    while True:
        ret, frame = stream.read()
        if not ret:
            print("Stream read error")
            break

        # --- Rotation ---
        if rotation_modes[rotation_index] is not None:
            frame = cv2.rotate(frame, rotation_modes[rotation_index])

        # --- Convert to grayscale and normalize ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        gray_uint8 = np.uint8(gray_norm)

        # --- Apply colormap (safe) ---
        try:
            cmap = color_maps[map_index]
            colored = cv2.applyColorMap(gray_uint8, cmap)
        except Exception as e:
            traceback.print_exc()
            print(f"⚠️ Invalid colormap at index {map_index}, falling back to COLORMAP_INFERNO")
            map_index = 0
            colored = cv2.applyColorMap(gray_uint8, color_maps[0])

        # --- Resize safely ---
        new_w = max(1, int(colored.shape[1] * scale_percent / 100))
        new_h = max(1, int(colored.shape[0] * scale_percent / 100))
        interp = interpolation_type[interpolation_index]
        try:
            clean_frame = cv2.resize(colored, (new_w, new_h), interpolation=interp)
        except Exception as e:
            traceback.print_exc()
            print(f"⚠️ Invalid interpolation index {interpolation_index}, fallback to INTER_LINEAR.")
            clean_frame = cv2.resize(colored, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # --- Display frame with overlays ---
        display_frame = clean_frame.copy()
        h, w = display_frame.shape[:2]

        cv2.putText(display_frame, 'GOYOJO GW192A Thermal Camera. Type [H] for help.',
                    (10, h - 10), FONT, FONT_SCALE, TEXT_COLOR, THICKNESS, cv2.LINE_AA)

        if show_text:
            lines = [
                'Application features:',
                ' ',
                'Type [H] to show/hide help',
                'Type [+]/[-] to resize window',
                'Type [R] to rotate window',
                'Type [P] to change the color palette',
                'Type [I] to change the interpolation type',
                'Type [S] to save the screenshot as a PNG file',
                'Type [V] to capture video as MP4 file',
                'Type [Q] to close application'
            ]
            y = 20
            for line in lines:
                cv2.putText(display_frame, line, (10, y), FONT, FONT_SCALE, TEXT_COLOR, THICKNESS, cv2.LINE_AA)
                y += 15

        if last_message and (time.time() - last_message_time < MESSAGE_DURATION):
            cv2.putText(display_frame, last_message, (10, h - 25), FONT, FONT_SCALE, TEXT_COLOR, THICKNESS, cv2.LINE_AA)

        if is_recording:
            current_time = time.time()
            if current_time - last_blink_time >= BLINK_INTERVAL:
                rec_blink_state = not rec_blink_state
                last_blink_time = current_time
            if rec_blink_state:
                cv2.putText(display_frame, "REC", (w - 80, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3, cv2.LINE_AA)
            if video_writer is not None:
                video_writer.write(clean_frame)

        cv2.imshow("GW192A thermal Camera Live View", display_frame)

        # --- Keyboard controls ---
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key in (ord('h'), ord('H')):
            show_text = not show_text
        elif key in (ord('r'), ord('R')):
            rotation_index = (rotation_index + 1) % 4
            update_and_save(settings, "rotation_index", rotation_index)
            show_message(f"Rotate: {rotation_index * 90}°")
        elif key in (ord('p'), ord('P')):
            map_index = (map_index + 1) % len(color_maps)
            update_and_save(settings, "map_index", map_index)
            show_message(f"Color palette: {map_index + 1} of {len(color_maps)}")
        elif key in (ord('i'), ord('I')):
            interpolation_index = (interpolation_index + 1) % len(interpolation_type)
            update_and_save(settings, "interpolation_index", interpolation_index)
            show_message(f"Interpolation: {interpolation_index + 1} of {len(interpolation_type)}")
        elif key in (ord('+'), ord('=')):
            scale_percent = min(scale_percent + step, max_scale)
            update_and_save(settings, "scale_percent", scale_percent)
            show_message(f"Scale: {scale_percent}%")
        elif key in (ord('-'), ord('_')):
            scale_percent = max(scale_percent - step, min_scale)
            update_and_save(settings, "scale_percent", scale_percent)
            show_message(f"Scale: {scale_percent}%")
        elif key in (ord('s'), ord('S')):
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(SAVE_DIR, f"snapshot_{timestamp}.png")
            try:
                cv2.imwrite(filename, clean_frame)
                show_message(f"Saved: {os.path.basename(filename)}")
            except Exception:
                traceback.print_exc()
                show_message("Failed to save snapshot.")
        elif key in (ord('v'), ord('V')):
            if not is_recording:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                video_filename = os.path.join(SAVE_DIR, f"capture_{timestamp}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = 25
                frame_size = (clean_frame.shape[1], clean_frame.shape[0])
                try:
                    video_writer = cv2.VideoWriter(video_filename, fourcc, fps, frame_size)
                    if not video_writer.isOpened():
                        raise RuntimeError("VideoWriter failed to open.")
                    is_recording = True
                    rec_blink_state = True
                    last_blink_time = time.time()
                    show_message(f"Recording started: {os.path.basename(video_filename)}")
                except Exception:
                    traceback.print_exc()
                    show_message("Failed to start recording.")
                    video_writer = None
                    is_recording = False
            else:
                is_recording = False
                if video_writer is not None:
                    try:
                        video_writer.release()
                        show_message(f"Recording stopped: {os.path.basename(video_filename)}")
                    except Exception:
                        traceback.print_exc()
                        show_message("Failed to stop recording.")
                    finally:
                        video_writer = None

finally:
    try:
        if video_writer is not None:
            video_writer.release()
    except Exception:
        pass
    stream.release()
    cv2.destroyAllWindows()
