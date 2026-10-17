'''
Flask creates a web server that can be accessed from a web browser.
This is needed if the Jetson is running headless (without a monitor) 
and you want to view the webcam stream from another computer.
Response lets us send the webcam frames to the web browser.
'''
import cv2
from flask import Flask, Response

# Creates flask application object with the name of the current script.
app = Flask(__name__)

# Initialize the webcam with USB port 0 and the V4L2 backend. This is the default for most USB webcams.
camera = cv2.VideoCapture(1, cv2.CAP_V4L2)

'''
Set the video format to MJPG (Motion JPEG) for better performance.
MJPEG means the camera sends a sequence of JPEG images, which is faster than sending raw frames.
* splits the string into individual characters, which is what VideoWriter_fourcc expects.
'''
camera.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*"MJPG")
)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)

if not camera.isOpened():
    raise RuntimeError("Could not open webcam")


def generate_frames():
    while True:
        success, frame = camera.read()

        if not success:
            print("Could not read frame")
            break

        # Encode the frame as JPEG. This is necessary because the web browser expects JPEG images.
        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            continue

        # Convert JPEG data to raw bytes. (HTTP requires raw bytes, not numpy arrays.)
        frame_bytes = buffer.tobytes()

        '''
        Yield is like return, but it allows the function to be paused and resumed. 
        This is useful for streaming data because it allows the server to send frames 
        one at a time without waiting for the entire video to be processed.
        b means the data is in bytes format, which is required for HTTP responses.
        '''
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame_bytes +
            b"\r\n"
        )

        '''
        --frame
        Content-Type: image/jpeg

        [JPEG FRAME 1]

        --frame
        Content-Type: image/jpeg

        [JPEG FRAME 2]

        --frame
        Content-Type: image/jpeg

        [JPEG FRAME 3]
        '''


'''
When someone visits the root URL ("/") of the web server, 
Flask runs index().
Whetever index() returns is sent to the web browser as the response.
So visiting http://127.0.0.1:5000/ in a web browser will show the HTML returned by index().
'''
@app.route("/")
def index():
    return """
    <html>
        <head>
            <title>Jetson Webcam</title>
        </head>
        <body>
            <h1>Jetson Webcam</h1>
            <p>Welcome to the Jetson Webcam!</p>
            <img src="/video_feed" width="640">
        </body>
    </html>
    """

'''
When someone visits http://127.0.0.1:5000/video_feed, Flask runs only video_feed().
/              → normal webpage
/video_feed    → only the camera stream
'''
@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        # The mimetype tells the web browser that the response is a multipart stream of JPEG images.
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

'''
The following code runs the Flask web server. It listens on all network interfaces (0.0.0.0).
The port is set to 5000, which is the default for Flask.
if host="127.0.0.1", the server would only be accessible from the Jetson itself.
'''
if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        camera.release()