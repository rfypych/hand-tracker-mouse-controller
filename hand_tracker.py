import cv2
import mediapipe as mp
import time
import math

class HandTracker():
    def __init__(self, mode=False, maxHands=1, modelComplexity=1, detectionCon=0.5, trackCon=0.5):
        """Initializes the HandTracker.

        Args:
            mode: Whether to treat the input images as a batch of static
                images or a video stream.
            maxHands: Maximum number of hands to detect.
            modelComplexity: Complexity of the hand landmark model (0 or 1).
            detectionCon: Minimum confidence value ([0.0, 1.0]) for hand detection.
            trackCon: Minimum confidence value ([0.0, 1.0]) for hand tracking.
        """
        self.mode = mode
        self.maxHands = maxHands
        self.modelComplex = modelComplexity
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        # Initialize Mediapipe Hands
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(self.mode, self.maxHands, self.modelComplex,
                                        self.detectionCon, self.trackCon)
        self.mpDraw = mp.solutions.drawing_utils
        self.tipIds = [4, 8, 12, 16, 20] # Finger tip landmarks IDs
        self.results = None # Store results of hand processing
        self.lmList = []

    def find_hands(self, img, draw=True):
        """Finds hands in an image and draws landmarks.

        Args:
            img: The input image (BGR format).
            draw: Whether to draw the landmarks and connections on the image.

        Returns:
            The image with landmarks drawn (if draw=True).
        """
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)
        # self.lmList = [] # Reset landmark list for the current frame

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms,
                                               self.mpHands.HAND_CONNECTIONS)
        return img

    def find_position(self, img, handNo=0, draw=True):
        """Finds the landmarks positions for a specific hand.

        Args:
            img: The input image.
            handNo: The index of the hand to find positions for.
            draw: Whether to draw circles on the landmarks.

        Returns:
            A list of landmark positions [[id, x, y], ...].
            Returns an empty list if no hand or the specified hand is not found.
        """
        self.lmList = []
        h, w, c = img.shape
        if self.results.multi_hand_landmarks:
            if handNo < len(self.results.multi_hand_landmarks):
                myHand = self.results.multi_hand_landmarks[handNo]
                for id, lm in enumerate(myHand.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    self.lmList.append([id, cx, cy])
                    if draw:
                        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)
        return self.lmList

    def fingers_up(self):
        """Checks which fingers are up.

        Assumes self.lmList is populated for the current hand.

        Returns:
            A list of 5 elements (0 or 1) representing the state of each finger
            (Thumb, Index, Middle, Ring, Pinky). 1 means up, 0 means down.
            Returns an empty list if lmList is not populated correctly.
        """
        fingers = []
        if len(self.lmList) != 21: # Need all 21 landmarks
            return []

        # Thumb: Check x-position of tip vs landmark below it.
        # Considers handedness implicitly (works for flipped image too if thumb logic is based on relative x)
        # Use > for left hand in mirrored view, < for right hand in mirrored view.
        # Let's use a more robust method comparing tip distance to a point further inside.
        thumb_tip = self.lmList[self.tipIds[0]][1]
        thumb_ip = self.lmList[self.tipIds[0] - 1][1]
        thumb_mcp = self.lmList[self.tipIds[0] - 2][1]
        # Simplified: Check if tip is further 'out' (left for right hand in mirror) than the joint below
        if self.lmList[self.tipIds[0]][1] < self.lmList[self.tipIds[0] - 1][1]: # Adjust based on actual testing
             fingers.append(1)
        else:
             fingers.append(0)


        # Other 4 Fingers: Check y-position of tip vs joint 2 landmarks below it.
        for id in range(1, 5):
            if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers

    def find_distance(self, p1_id, p2_id, img=None, draw=True):
        """Calculates the distance between two landmarks.

        Args:
            p1_id: Landmark ID of the first point.
            p2_id: Landmark ID of the second point.
            img: Image to draw on (optional).
            draw: Whether to draw the line and distance on the image.

        Returns:
            The distance between the two points.
            Center coordinates (cx, cy) of the line between points.
            Returns infinity and None if landmarks are not found.
        """
        if not self.lmList or max(p1_id, p2_id) >= len(self.lmList):
            return float('inf'), None

        x1, y1 = self.lmList[p1_id][1], self.lmList[p1_id][2]
        x2, y2 = self.lmList[p2_id][1], self.lmList[p2_id][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        length = math.hypot(x2 - x1, y2 - y1)

        if draw and img is not None:
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
            cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (cx, cy), 10, (0, 0, 255), cv2.FILLED)
            # cv2.putText(img, f'{int(length)}', (cx - 20, cy - 20),
            #             cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

        return length, (cx, cy) 