import cv2
import numpy as np
from datetime import datetime
import os
import json
import tempfile
import traceback
import time

# The name of the folder where the screenshots and settings will be saved
SAVE_DIR = "snapshots"
SETTINGS_DIR = "settings"
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "config.json")
# Create folder if it does not exist
os.makedirs(SAVE_DIR, exist_ok=True)
# Load settings
def ensure_settings_dir():
    os.makedirs(SETTINGS_DIR, exist_ok=True)

def atomic_save_json(path, data):
    """Writes JSON atomically: first to a temporary file, then replace."""
    ensure_settings_dir()
    dir_name = os.path.dirname(path) or "."
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="tmp_settings_", dir=dir_name, text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # atomic override
        os.replace(tmp_path, path)
        return True
    except Exception:
        # If something went wrong, try deleting the temporary file
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        traceback.print_exc()
        return False

def load_settings():
    """Loads settings from a JSON file or creates defaults and saves them."""
    ensure_settings_dir()
    default_settings = {
        "rotation_index": 1,  # 90°
        "map_index": 0,
        "interpolation_index": 0,
        "scale_percent": 600
    }

    if not os.path.exists(SETTINGS_FILE):
        # we save the default settings and return them
        atomic_save_json(SETTINGS_FILE, default_settings)
        return default_settings

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # make sure all keys exist (adjustment after program update)
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
        # if the file is corrupted - overwrite with default ones
        atomic_save_json(SETTINGS_FILE, default_settings)
        return default_settings

def update_and_save(settings, key, value):
    """Update settings[key] = value and immediately save to file."""
    settings[key] = value
    success = atomic_save_json(SETTINGS_FILE, settings)
    if not success:
        print("Warning: Failed to save settings to disk.")
    return success

# --- text messages ---
last_message = ""
last_message_time = 0
MESSAGE_DURATION = 2.0  # seconds

def show_message(text):
    """Show a short on-screen message for 2 seconds."""
    global last_message, last_message_time
    last_message = text
    last_message_time = time.time()
    
# Video recording state
is_recording = False
video_writer = None
video_filename = None
rec_blink_state = False  # True/False switch for blinking effect
last_blink_time = 0
BLINK_INTERVAL = 1  # seconds for blinking "REC"
    
# Load settings from file
settings = load_settings()
rotation_index = int(settings.get("rotation_index", 1))
map_index = int(settings.get("map_index", 0))
interpolation_index = int(settings.get("interpolation_index", 0))
scale_percent = int(settings.get("scale_percent", 600))
min_scale = 150
max_scale = 1000
step = 50
# Help text visibility
show_text = False  # hidden on start
# Camera resolution
cameraResolution_Horizontal = 96
cameraResolution_Vertical = 96
# Rotation frame
rotation_modes = [
    None,  # 0 stopni
    cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_180,
    cv2.ROTATE_90_COUNTERCLOCKWISE
]
# List of available color maps
color_maps = [
    cv2.COLORMAP_INFERNO,   # default
    cv2.COLORMAP_AUTUMN,
    cv2.COLORMAP_BONE,
    cv2.COLORMAP_CIVIDIS,
    cv2.COLORMAP_COOL,
    cv2.COLORMAP_DEEPGREEN,
    cv2.COLORMAP_HOT,
    cv2.COLORMAP_HSV,
    cv2.COLORMAP_JET,
    cv2.COLORMAP_MAGMA,
    cv2.COLORMAP_OCEAN,
    cv2.COLORMAP_PARULA,
    cv2.COLORMAP_PINK,
    cv2.COLORMAP_PLASMA,
    cv2.COLORMAP_RAINBOW,
    cv2.COLORMAP_SPRING,
    cv2.COLORMAP_SUMMER,
    cv2.COLORMAP_TURBO,
    cv2.COLORMAP_TWILIGHT,
    cv2.COLORMAP_TWILIGHT_SHIFTED,
    cv2.COLORMAP_VIRIDIS,
    cv2.COLORMAP_WINTER
]
# List of available interpolation
interpolation_type = [
    cv2.INTER_LINEAR_EXACT,   # default
    cv2.INTER_NEAREST,
    cv2.INTER_AREA,
    cv2.INTER_BITS,
    cv2.INTER_BITS2,
    cv2.INTER_CUBIC,
    cv2.INTER_LANCZOS4,
    cv2.INTER_LINEAR
]

#--------------------------------------------------------------------------------

# Replace "0" with a file path to work with a saved video
stream = cv2.VideoCapture(1, cv2.CAP_DSHOW)
stream.set(cv2.CAP_PROP_FRAME_WIDTH, cameraResolution_Horizontal)
stream.set(cv2.CAP_PROP_FRAME_HEIGHT, cameraResolution_Vertical)
#stream.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('Y', '1', '6', ' '))
#stream.set(cv2.CAP_PROP_CONVERT_RGB, 0)

if not stream.isOpened():
    print("Camera open error")
    exit()

while True:
    ret, frame = stream.read()
    if not ret: # if no frames are returned
        print("Stream read error")
        break
    
    new_width = int(cameraResolution_Horizontal * scale_percent / 100)
    new_height = int(cameraResolution_Vertical * scale_percent / 100)
    dim = (new_width, new_height)
    
    # Rotation according to the current index
    if rotation_modes[rotation_index] is not None:
        frame = cv2.rotate(frame, rotation_modes[rotation_index])
  
    # Normalize frame to 256 gray
    cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)
    frame = np.uint8(frame)
    
    # Use of the current color map (make sure the map list is not empty)
    if len(color_maps) > 0:
        frame = cv2.applyColorMap(frame, color_maps[map_index])
        
    frame = cv2.resize(frame, dim, interpolation = interpolation_type[interpolation_index]) #https://www.opencvhelp.org/tutorials/video-processing/how-to-resize-video/
    #frame = cv2.resize(frame, (200, 200)) # You could specyfy your own window size if needed
    
    # --- If video recording is active, write the frame to file ---
    if is_recording and video_writer is not None:
        video_writer.write(frame)
        # Toggle blinking "REC" every 0.5 sec
        current_time = time.time()
        if current_time - last_blink_time >= BLINK_INTERVAL:
            rec_blink_state = not rec_blink_state
            last_blink_time = current_time
        # Show blinking "REC" text
        if rec_blink_state:
            cv2.putText(frame, "REC", (frame.shape[1] - 80, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3, cv2.LINE_AA)
    
    # TEXTS
    org = (10, (new_height - 10))
    color = (255, 255, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.4
    thickness = 1
    cv2.putText(frame, 'GOYOJO GW192A Thermal Camera. Type [H] for help.', org, font, fontScale, color, thickness, cv2.LINE_AA)
    
    # if pressed [H] for help:
    if show_text:
        org = (10, 20)
        cv2.putText(frame, 'Application features:', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 40)
        cv2.putText(frame, 'Type [H] to show/hide help', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 55)
        cv2.putText(frame, 'Type [+]/[-] to resize window', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 70)
        cv2.putText(frame, 'Type [R] to rotate window', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 85)
        cv2.putText(frame, 'Type [P] to change the color palette', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 100)
        cv2.putText(frame, 'Type [I] to change the interpolation type', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 115)
        cv2.putText(frame, 'Type [S] to save the screenshot as a PNG file', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 130)
        cv2.putText(frame, 'Type [V] to capture video as MP4 file', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 145)
        cv2.putText(frame, 'Type [Q] to close application', org, font, fontScale, color, thickness, cv2.LINE_AA)
        pass
    
    # --- wyświetlanie komunikatu przez 2 sekundy ---
    if last_message and (time.time() - last_message_time < MESSAGE_DURATION):
        org = (10, (new_height - 25))
        cv2.putText(frame, last_message, org, font, fontScale, color, thickness, cv2.LINE_AA)
    
    # Show video frame
    cv2.imshow("GW192A thermal Camera Live View", frame)
    
    # Keyboard application control
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('h') or key == ord('H'):
        show_text = not show_text  # switching help information
    elif key in (ord('r'), ord('R')):
        rotation_index = (rotation_index + 1) % 4
        update_and_save(settings, "rotation_index", rotation_index)
        show_message(f"Rotate: {rotation_index * 90}*")
    elif key in (ord('p'), ord('P')):
        # security: what if the map list is empty?
        if len(color_maps) == 0:
            print("No color maps available in color_maps.")
        else:
            map_index = (map_index + 1) % len(color_maps)
            update_and_save(settings, "map_index", map_index)
            show_message(f"Color palette: {map_index+1} of 22")
    elif key in (ord('i'), ord('I')):
        # security: what if the map list is empty?
        if len(interpolation_type) == 0:
            print("No interpolation type available in interpolation_type.")
        else:
            interpolation_index = (interpolation_index + 1) % len(interpolation_type)
            update_and_save(settings, "interpolation_index", interpolation_index)
            show_message(f"Interpolation type: {interpolation_index+1} of 8")
    elif key in (ord('+'), ord('=')):
        scale_percent = min(scale_percent + step, max_scale)
        update_and_save(settings, "scale_percent", scale_percent)
        show_message(f"Scale: {scale_percent}%")
    elif key in (ord('-'), ord('_')):
        scale_percent = max(scale_percent - step, min_scale)
        update_and_save(settings, "scale_percent", scale_percent)
        show_message(f"Scale: {scale_percent}%")
    elif key == ord('s') or key == ord('S'):
        # Current date and time
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(SAVE_DIR, f"snapshot_{timestamp}.png")
        # Capturing a frame and saving it to a file
        cv2.imwrite(filename, frame)
    elif key in (ord('v'), ord('V')):
            # Start/stop video recording
            if not is_recording:
                # --- Start recording ---
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                video_filename = os.path.join(SAVE_DIR, f"capture_{timestamp}.mp4")

                # Determine output parameters
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = 25
                frame_size = (frame.shape[1], frame.shape[0])

                video_writer = cv2.VideoWriter(video_filename, fourcc, fps, frame_size)
                is_recording = True
                show_message(f"Recording started: {os.path.basename(video_filename)}")
            else:
                # --- Stop recording ---
                is_recording = False
                if video_writer is not None:
                    video_writer.release()
                    video_writer = None
                    show_message(f"Recording stopped: {os.path.basename(video_filename)}")


stream.release()
if video_writer is not None:
    video_writer.release()
cv2.destroyAllWindows() #!