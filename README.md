# GOYOJO-GW192A-Thermal-Camera

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/script.jpg "Script")

<p>The script allows you to launch a live image preview from the GOYOJO GW192A camera.
I used Python.
<br>For the script to work properly, you need to install openCV and numpy.
</p>
<p>
<b>[2025/10/16, 11:10]
<br>1. I added the option to take a screenshot as *.png - save to the ‘snapshots’ folder,
<br>2. I added an automatic option to save user settings for rotation, scale, and heat maps - ‘settings’ folder - ‘config.json’ file
</b>
<br><b>[2025/10/15, 23:30] I changed the app controls:</b>
<br>Application features:
<br>
<br>Type [H] to show/hide help
<br>Type [+]/[-] to resize window
<br>Type [R] to rotate window
<br>Type [P] to change the color palette.
<br>Type [S] to save the screenshot as a PNG file
<br>Type [Q] to close application

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/new_features.JPG "new_features.JPG")
  
</p>
<hr>
<p>
<b>NOTE:</b>
<br>The GOYOJO thermal imaging camera is advertised and sold as a camera with a resolution of 192x192 pixels, while in fact the resolution of the optical sensor is only 96x96 pixels:

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/camera_resolution.jpg "Camera resolurion")

<p>When connected to Windows, the camera appears as “UVC Camera.” Using ffmpeg and the command:
<br><code>ffmpeg -list_options true -f dshow -i video="UVC Camera"</code>
<br>we get the following result:

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/camera_resolution_ffmpeg.jpg "Camera resolurion ffmpeg")

<br>It is therefore clear beyond any doubt that the resolution of the IR matrix is 96x96 pixels.
</p>
<p>Of the streams listed, only three can be played using ffmpeg:
<br>96x96 nv12 - contains a grayscale image:

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/96x96_nv12.jpg "96x96_nv12.jpg")

96x100 yuyv422 - contains a green image with high contrast:

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/96x100_yuyv422.jpg "96x100_yuyv422.jpg")

96x176 yuyv422 - is a composite of the 96x100 image with two additional smaller copies:

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/96x176_yuyv422.jpg "96x176_yuyv422.jpg")

</p>
<p>
<br>Unfortunately, none of the images contain 16-bit grayscale data, which usually allows for video transmission together with a temperature map.
<br>I tried to analyze the files I received using ChatGPT, but unfortunately I did not obtain any positive information.
<br>Below is a transcript of the conversation with ChatGPT (PDF file):
<br>https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/YUYV422_file_analysis.pdf
</p>
