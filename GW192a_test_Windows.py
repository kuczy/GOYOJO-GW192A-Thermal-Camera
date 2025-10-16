import cv2
import numpy as np
from datetime import datetime
import os

# The name of the folder where the screenshots will be saved
SAVE_DIR = "snapshots"
# Create folder if it does not exist
os.makedirs(SAVE_DIR, exist_ok=True)
# Camera resolution
cameraResolution_Horizontal = 96
cameraResolution_Vertical = 96
# Resize the frame
scale_percent = 600  # początkowa wartość
min_scale = 150
max_scale = 1000
step = 50
# Rotation frame
rotation_index = 1  # 0=NoRotation, 1=90°, 2=180°, 3=270°
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
    # mapa 2
]
map_index = 0  # current heat map index
# Help text visibility
show_text = False  # hidden on start

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
  
    cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)
    frame = np.uint8(frame)
    # Use of the current color map
    frame = cv2.applyColorMap(frame, color_maps[map_index])
    frame = cv2.resize(frame, dim, interpolation = cv2.INTER_LINEAR_EXACT) #https://www.opencvhelp.org/tutorials/video-processing/how-to-resize-video/
    #frame = cv2.resize(frame, (200, 200)) # You could specyfy your own window size if needed
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
        cv2.putText(frame, 'Type [P] to change the color palette.', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 100)
        cv2.putText(frame, 'Type [S] to save the screenshot as a PNG file', org, font, fontScale, color, thickness, cv2.LINE_AA)
        org = (10, 115)
        cv2.putText(frame, 'Type [Q] to close application', org, font, fontScale, color, thickness, cv2.LINE_AA)
        pass
    
    cv2.imshow("GW192A thermal Camera Live View", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == ord('Q'):  # Exit aplication
        break
    elif key == ord('+') or key == ord('='):
        scale_percent = min(scale_percent + step, max_scale)
    elif key == ord('-') or key == ord('_'):
        scale_percent = max(scale_percent - step, min_scale)
    elif key == ord('h') or key == ord('H'):
        show_text = not show_text  # switching help information
    elif key == ord('r') or key == ord('R'):
        rotation_index = (rotation_index + 1) % 4  # rotate 90° right
    elif key == ord('p') or key == ord('P'):
        map_index = (map_index + 1) % len(color_maps) # switch heat colour maps
    elif key == ord('s') or key == ord('S'):
        # Current date and time
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(SAVE_DIR, f"snapshot_{timestamp}.png")
        # Capturing a frame and saving it to a file
        cv2.imwrite(filename, frame)

stream.release()
cv2.destroyAllWindows() #!