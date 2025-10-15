# GOYOJO-GW192A-Thermal-Camera

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
<br>96x96 nv12 - contains a grayscale image,
<br>96x100 yuyv422 - contains a green image with high contrast,
<br>96x176 yuyv422 - is a composite of the 96x100 image with two additional smaller copies:
  
![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/96x96_nv12.jpg "96x96_nv12.jpg")

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/96x100_yuyv422.jpg "96x100_yuyv422.jpg")

![alt text](https://raw.githubusercontent.com/kuczy/GOYOJO-GW192A-Thermal-Camera/refs/heads/main/images/96x176_yuyv422.jpg "96x176_yuyv422.jpg")

</p>
