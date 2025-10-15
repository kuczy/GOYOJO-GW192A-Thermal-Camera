import cv2
import numpy as np

# Camera resolution
cameraResolution_Horizontal = 96
cameraResolution_Vertical = 96
# Resize the frame
scale_percent = 600
new_width = int(cameraResolution_Horizontal * scale_percent / 100)
new_height = int(cameraResolution_Vertical * scale_percent / 100)
dim = (new_width, new_height)

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
    
    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE) #rotate frame - GW192a USB port on top    
    cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)
    frame = np.uint8(frame)
    frame = cv2.applyColorMap(frame, cv2.COLORMAP_INFERNO)
    frame = cv2.resize(frame, dim, interpolation = cv2.INTER_LINEAR_EXACT) #https://www.opencvhelp.org/tutorials/video-processing/how-to-resize-video/
    #frame = cv2.resize(frame, (200, 200)) # You could specyfy your own window size if needed
    org = (10, (new_height - 10))
    color = (255, 255, 255)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.4
    thickness = 1
    cv2.putText(frame, 'GOYOJO GW192A Thermal Camera', org, font, fontScale, color, thickness, cv2.LINE_AA)
    
    cv2.imshow("GW192A thermal Camera - PRESS 'q' TO EXIT", frame)
    if cv2.waitKey(1) == ord('q'): # press "q" to quit
        break

stream.release()
cv2.destroyAllWindows() #!