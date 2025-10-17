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
DEBUG_DIR = "debug"
DEBUG_FILE = os.path.join(DEBUG_DIR, "error.log")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "config.json")

os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(SETTINGS_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

# --- Logging ---
def log_error(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def log_exception(e, context=""):
    tb = traceback.format_exc()
    log_error(f"{context} Exception: {e}\n{tb}")

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
    except Exception as e:
        log_exception(e, "atomic_save_json")
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as ex:
            log_exception(ex, "atomic_save_json cleanup")
        return False

def backup_file(path):
    """Create a timestamped backup of a file."""
    try:
        if os.path.exists(path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{path}.backup_{timestamp}"
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(data)
    except Exception as e:
        log_exception(e, "backup_file")

def load_settings():
    """Load settings or create defaults if missing/corrupted."""
    default_settings = {
        "_comment_1": "------------ GOYOJO GW192A CAMERA INDEX ---------------------",
        "_comment_2": "",
        "_comment_WINDOWS_SYSTEM": "For Windows use numeric index (e.g., 0, 1, 2). Example: 'gw192a_camera_index': 1 will open the second camera detected by the system.",
        "_comment_3": "",
        "_comment_LINUX_SYSTEM": "For Linux/Raspberry Pi use device path instead (e.g., '/dev/video0', '/dev/video1', '/dev/v4l/by-id/usb-GW192A_Thermal_Camera-video-index0').",
        "_comment_4": "",
        "_comment_5": "-------------------------------------------------------------",
        "gw192a_camera_index": 1,
        "rotation_index": 1,
        "map_index": 0,
        "interpolation_index": 0,
        "scale_percent": 650
    }

    if not os.path.exists(SETTINGS_FILE):
        atomic_save_json(SETTINGS_FILE, default_settings)
        return default_settings

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        changed = False
        for k, v in default_settings.items():
            if k not in data or not isinstance(data[k], type(v)):
                data[k] = v
                changed = True
        if changed:
            backup_file(SETTINGS_FILE)
            atomic_save_json(SETTINGS_FILE, data)
        return data
    except Exception as e:
        log_exception(e, "load_settings")
        backup_file(SETTINGS_FILE)
        atomic_save_json(SETTINGS_FILE, default_settings)
        return default_settings

def update_and_save(settings, key, value):
    """Update settings dict and save to disk."""
    settings[key] = value
    success = atomic_save_json(SETTINGS_FILE, settings)
    if not success:
        log_error("Warning: Failed to save settings to disk.")
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
BLINK_INTERVAL = 1  # seconds

# --- Load persisted settings ---
settings = load_settings()
camera_source = settings.get("gw192a_camera_index", 1)
rotation_index = int(settings.get("rotation_index", 1))
map_index = int(settings.get("map_index", 0))
interpolation_index = int(settings.get("interpolation_index", 0))
scale_percent = int(settings.get("scale_percent", 600))

# --- Parameters ---
min_scale, max_scale, step = 150, 1000, 50
show_text = False
cameraResolution_Horizontal = 96
cameraResolution_Vertical = 96

# --- Gradient overlay settings ---
show_gradient = True
gradient_width = 20
gradient_margin = 10

# --- Rotation modes ---
rotation_modes = [
    None,
    cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_180,
    cv2.ROTATE_90_COUNTERCLOCKWISE
]

# --- Color maps ---
color_maps = [
    cv2.COLORMAP_INFERNO, cv2.COLORMAP_AUTUMN, cv2.COLORMAP_BONE, cv2.COLORMAP_CIVIDIS,
    cv2.COLORMAP_COOL, cv2.COLORMAP_DEEPGREEN, cv2.COLORMAP_HOT, cv2.COLORMAP_HSV,
    cv2.COLORMAP_JET, cv2.COLORMAP_MAGMA, cv2.COLORMAP_OCEAN, cv2.COLORMAP_PARULA,
    cv2.COLORMAP_PINK, cv2.COLORMAP_PLASMA, cv2.COLORMAP_RAINBOW, cv2.COLORMAP_SPRING,
    cv2.COLORMAP_SUMMER, cv2.COLORMAP_TURBO, cv2.COLORMAP_TWILIGHT, cv2.COLORMAP_TWILIGHT_SHIFTED,
    cv2.COLORMAP_VIRIDIS, cv2.COLORMAP_WINTER
]

# --- Interpolation types ---
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
if isinstance(camera_source, str) and camera_source.isdigit():
    camera_source = int(camera_source)

def open_camera(source, width, height):
    for attempt in range(3):
        try:
            if os.name == 'nt':
                stream = cv2.VideoCapture(source, cv2.CAP_DSHOW)
            else:
                stream = cv2.VideoCapture(source)
            stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            if stream.isOpened():
                return stream
            else:
                log_error(f"Attempt {attempt+1}: Camera open failed.")
                time.sleep(1)
        except Exception as e:
            log_exception(e, "open_camera")
    return None

stream = open_camera(camera_source, cameraResolution_Horizontal, cameraResolution_Vertical)
if not stream:
    log_error("Camera could not be opened. Exiting.")
    sys.exit(1)

# --- Gradient generation function ---
def create_vertical_gradient(height):
    """Create a vertical grayscale gradient from 0 (black, bottom) to 255 (white, top)."""
    gradient = np.linspace(0, 255, height, dtype=np.uint8)
    gradient = np.flipud(gradient)
    gradient = np.tile(gradient[:, np.newaxis], (1, gradient_width))
    return gradient

# --- Mouse tracking variables ---
mouse_x, mouse_y = 0, 0
mouse_value = 0

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

cv2.namedWindow("GW192A thermal Camera Live View")
cv2.setMouseCallback("GW192A thermal Camera Live View", mouse_callback)

# --- Main loop ---
try:
    while True:
        try:
            ret, frame = stream.read()
            if not ret or frame is None:
                log_error("Stream read error.")
                break

            # --- Rotation ---
            if rotation_modes[rotation_index] is not None:
                frame = cv2.rotate(frame, rotation_modes[rotation_index])

            # --- Grayscale and normalize ---
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
            gray_uint8 = np.uint8(gray_norm)

            # --- Apply colormap safely ---
            try:
                cmap = color_maps[map_index]
                colored = cv2.applyColorMap(gray_uint8, cmap)
            except Exception as e:
                log_exception(e, "applyColorMap")
                map_index = 0
                colored = cv2.applyColorMap(gray_uint8, color_maps[0])

            # --- Resize safely ---
            new_w = max(1, int(colored.shape[1] * scale_percent / 100))
            new_h = max(1, int(colored.shape[0] * scale_percent / 100))
            interp = interpolation_type[interpolation_index]
            try:
                clean_frame = cv2.resize(colored, (new_w, new_h), interpolation=interp)
            except Exception as e:
                log_exception(e, "resize")
                clean_frame = cv2.resize(colored, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # --- Overlay ---
            display_frame = clean_frame.copy()
            h, w = display_frame.shape[:2]

            # --- Overlay gradient if enabled ---
            if show_gradient:
                grad_h = h - 2 * gradient_margin
                grad_gray = create_vertical_gradient(grad_h)
                try:
                    grad_colored = cv2.applyColorMap(grad_gray, color_maps[map_index])
                except Exception as e:
                    log_exception(e, "applyColorMap to gradient")
                    grad_colored = cv2.applyColorMap(grad_gray, color_maps[0])
                grad_resized = cv2.resize(grad_colored, (gradient_width, grad_h), interpolation=cv2.INTER_NEAREST)
                display_frame[gradient_margin:h-gradient_margin, w-gradient_width-gradient_margin:w-gradient_margin] = grad_resized

            # --- Draw static text ---
            cv2.putText(display_frame, 'GOYOJO GW192A Thermal Camera. Type [H] for help.',
                        (10, h - 10), FONT, FONT_SCALE, TEXT_COLOR, THICKNESS, cv2.LINE_AA)

            # --- Draw help text ---
            if show_text:
                lines = [
                    'Application features:',
                    ' ',
                    'Type [H] to show/hide help',
                    'Type [+]/[-] to resize window',
                    'Type [R] to rotate window',
                    'Type [P] to change the color palette',
                    'Type [G] to turn the color gradient bar on/off',
                    'Type [I] to change the interpolation type',
                    'Type [S] to save the screenshot as a PNG file',
                    'Type [V] to capture video as MP4 file',
                    'Type [Q] to close application'
                ]
                y_line = 20
                for line in lines:
                    cv2.putText(display_frame, line, (10, y_line), FONT, FONT_SCALE, TEXT_COLOR, THICKNESS, cv2.LINE_AA)
                    y_line += 15

            # --- Draw last message ---
            if last_message and (time.time() - last_message_time < MESSAGE_DURATION):
                cv2.putText(display_frame, last_message, (10, h - 25), FONT, FONT_SCALE, TEXT_COLOR, THICKNESS, cv2.LINE_AA)

            # --- Update mouse value scaled to original frame ---
            orig_x = int(mouse_x / scale_percent * 100)
            orig_y = int(mouse_y / scale_percent * 100)

            # Defensive bounds
            orig_x = min(max(orig_x, 0), gray_uint8.shape[1]-1)
            orig_y = min(max(orig_y, 0), gray_uint8.shape[0]-1)

            # Calculate grayscale value 0-100%
            mouse_value = int(gray_uint8[orig_y, orig_x] / 255 * 100)

           # --- Draw mouse value with full black outline (8-neighbor) ---
            text = f"{mouse_value}%"
            x = mouse_x + 5
            y = mouse_y - 5

            # Draw black outline around text (all 8 neighbours)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    cv2.putText(display_frame, text, (x + dx, y + dy),
                                FONT, FONT_SCALE, (64, 64, 64), THICKNESS + 1, cv2.LINE_AA)

            # Draw main green text
            cv2.putText(display_frame, text, (x, y),
                        FONT, FONT_SCALE, (0, 255, 0), THICKNESS, cv2.LINE_AA)

            # Draw main green text
            cv2.putText(display_frame, text, (x, y),
                        FONT, FONT_SCALE, (0, 255, 255), THICKNESS, cv2.LINE_AA)

            # --- Recording ---
            if is_recording:
                current_time = time.time()
                if current_time - last_blink_time >= BLINK_INTERVAL:
                    rec_blink_state = not rec_blink_state
                    last_blink_time = current_time
                if rec_blink_state:
                    cv2.putText(display_frame, "REC", (w - 80, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3, cv2.LINE_AA)
                if video_writer is not None:
                    try:
                        video_writer.write(clean_frame)
                    except Exception as e:
                        log_exception(e, "video_writer.write")

            # --- Show window ---
            cv2.imshow("GW192A thermal Camera Live View", display_frame)

            # --- Keyboard controls ---
            key = cv2.waitKey(10) & 0xFF
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
            elif key in (ord('+'), ord('=')) and not is_recording:
                scale_percent = min(scale_percent + step, max_scale)
                update_and_save(settings, "scale_percent", scale_percent)
                show_message(f"Scale: {scale_percent}%")
            elif key in (ord('-'), ord('_')) and not is_recording:
                scale_percent = max(scale_percent - step, min_scale)
                update_and_save(settings, "scale_percent", scale_percent)
                show_message(f"Scale: {scale_percent}%")
            elif key in (ord('s'), ord('S')):
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = os.path.join(SAVE_DIR, f"snapshot_{timestamp}.png")
                try:
                    cv2.imwrite(filename, clean_frame)
                    show_message(f"Saved: {os.path.basename(filename)}")
                except Exception as e:
                    log_exception(e, "save snapshot")
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
                    except Exception as e:
                        log_exception(e, "start recording")
                        show_message("Failed to start recording.")
                        video_writer = None
                        is_recording = False
                else:
                    is_recording = False
                    if video_writer is not None:
                        try:
                            video_writer.release()
                            show_message(f"Recording stopped: {os.path.basename(video_filename)}")
                        except Exception as e:
                            log_exception(e, "stop recording")
                            show_message("Failed to stop recording.")
                        finally:
                            video_writer = None
            elif key in (ord('g'), ord('G')):
                show_gradient = not show_gradient

        except Exception as e:
            log_exception(e, "main loop iteration")
            show_message("An unexpected error occurred.")

except KeyboardInterrupt:
    show_message("Interrupted by user.")

finally:
    try:
        if video_writer is not None:
            video_writer.release()
    except Exception as e:
        log_exception(e, "release video_writer in finally")
    try:
        if stream is not None:
            stream.release()
    except Exception as e:
        log_exception(e, "release camera in finally")
    cv2.destroyAllWindows()
