import cv2
import os   
print(cv2.__version__)

dispW=320
dispH=240
flip=2

# Logo dimensions and initial position
logoW=40
logoH=40
cX=logoW//2
cY=logoH//2

# Movement increments
dx=4
dy=4

# Create window and trackbar for opacity of the watermark image
cv2.namedWindow('WEBCAM')
cv2.createTrackbar('blended', 'WEBCAM', 50, 100, lambda x: None)

# Load the logo image and create masks
path = os.path.join(os.path.dirname(__file__), '..', 'images', 'pi.png')
pilogo = cv2.imread(path)
pilogo = cv2.resize(pilogo, (logoW, logoH))
pigray = cv2.cvtColor(pilogo, cv2.COLOR_BGR2GRAY)
cv2.imshow('CV LOGO', pilogo)
cv2.moveWindow('CV LOGO', 450, 0)
cv2.imshow('CV GRAY', pigray)
cv2.moveWindow('CV GRAY', 450, 240)

# Create a binary mask of the logo
_, BGMask = cv2.threshold(pigray, 225, 255, cv2.THRESH_BINARY)
cv2.imshow('BG Mask', BGMask)
cv2.moveWindow('BG Mask', 450, 420)

# Invert the mask to get the foreground mask
FGMask = cv2.bitwise_not(BGMask)
cv2.imshow('FG Mask', FGMask)
cv2.moveWindow('FG Mask', 450, 600)


# For Pi camera, use the following line:
# camSet='nvarguscamerasrc !  video/x-raw(memory:NVMM), width=3264, height=2464, format=NV12, framerate=28/1 ! nvvidconv flip-method='+str(flip)+' ! video/x-raw, width='+str(dispW)+', height='+str(dispH)+', format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink'
#cam=cv2.VideoCapture(camSet)

# For USB webcam, use the following line:
cam=cv2.VideoCapture(0, cv2.CAP_V4L2)

while True:
    ret, frame=cam.read()
    frame = cv2.resize(frame, (dispW, dispH))

    # Background is the webcam image where the logo is not present in the small region of interest
    BG = cv2.bitwise_and(frame[cY-logoH//2:cY+logoH//2, cX-logoW//2:cX+logoW//2], 
                         frame[cY-logoH//2:cY+logoH//2, cX-logoW//2:cX+logoW//2], 
                         mask=BGMask)
    cv2.imshow('BG', BG)
    cv2.moveWindow('BG', 0, 400)

    # Blended frame and logo based on the trackbar value
    BV1 = cv2.getTrackbarPos('blended', 'WEBCAM')/100
    BV2 = 1-BV1
    blended = cv2.addWeighted(frame[cY-logoH//2:cY+logoH//2, cX-logoW//2:cX+logoW//2], BV1, pilogo, BV2, 0)
    cv2.imshow('BLENDED', blended)
    cv2.moveWindow('BLENDED', 0, 600)

    # Foreground is the blended image where the logo is present
    FG = cv2.bitwise_and(blended, blended, mask=FGMask)
    cv2.imshow('FG', FG)
    cv2.moveWindow('FG', 450, 780)

    # Complementary image is the combination of the background and foreground images
    CompImage = cv2.add(BG, FG)
    cv2.imshow('COMP IMAGE', CompImage)
    cv2.moveWindow('COMP IMAGE', 0, 800)

    # Update the region of interest in the webcam frame with the complementary image
    frame[cY-logoH//2:cY+logoH//2, cX-logoW//2:cX+logoW//2] = CompImage

    cv2.imshow('WEBCAM', frame)
    cv2.moveWindow('WEBCAM', 0, 0)

    # Update the position of the logo for the next frame
    cX += dx
    cY += dy
    if cX >= dispW-logoW//2 or cX <= logoW//2:
        dx = -dx
    if cY >= dispH-logoH//2 or cY <= logoH//2:
        dy = -dy

    if cv2.waitKey(1)==ord('q'):
        break

cam.release()
cv2.destroyAllWindows()