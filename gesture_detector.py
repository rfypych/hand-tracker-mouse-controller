import numpy as np
import math

class Gesture:
    """Enum-like class for gesture types."""
    MOVE = "move"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    DRAG_START = "drag_start" # Signal to start dragging
    DRAG_END = "drag_end"     # Signal to end dragging
    FIST = "fist"             # Gesture for initiating drag
    NONE = "none"

class GestureDetector:
    def __init__(self, click_threshold=30, scroll_threshold=0.05, fist_threshold=50):
        """Initializes the GestureDetector.

        Args:
            click_threshold (int): Maximum distance between thumb and finger tip for click.
            scroll_threshold (float): Min vertical distance change (normalized) for scroll.
            fist_threshold (int): Max total distance from wrist for fingers to be considered a fist.
        """
        self.click_threshold = click_threshold
        self.scroll_threshold = scroll_threshold # Needs tuning
        self.fist_threshold = fist_threshold # Needs tuning
        self.prev_middle_y = None
        self.dragging = False

        # Landmark IDs
        self.tipIds = [4, 8, 12, 16, 20]
        self.wristId = 0

    def _calculate_distance(self, p1, p2):
        """Helper function to calculate Euclidean distance."""
        return math.hypot(p1[1] - p2[1], p1[2] - p2[2])

    def detect(self, lmList, fingers_state):
        """Detects the gesture based on landmark list and finger states.

        Args:
            lmList (list): List of landmark positions [[id, x, y], ...].
            fingers_state (list): List of 5 elements (0 or 1) for finger up/down state.

        Returns:
            Gesture (str): The detected gesture type (from Gesture class).
        """
        gesture = Gesture.NONE

        if not lmList or len(lmList) != 21 or not fingers_state or len(fingers_state) != 5:
            return Gesture.NONE # Invalid input

        # ---- Drag Detection (Fist) ----
        # Check if all fingers are down (fist)
        # More robust fist check: sum distances of fingertips to wrist
        total_dist_to_wrist = sum(self._calculate_distance(lmList[tipId], lmList[self.wristId]) for tipId in self.tipIds)
        # print(f"Fingers: {fingers_state}, TotalDist: {total_dist_to_wrist:.0f}") # Debug
        # is_fist = all(f == 0 for f in fingers_state)
        # Let's try the distance threshold approach
        is_fist = total_dist_to_wrist < self.fist_threshold * 5 # Heuristic: average distance * 5
        # Need a better fist detection, the one from fingers_state might be unreliable
        # Let's refine the fist check: all fingertips closer to MCP joint than usual?
        fist_check = True
        for i in range(1, 5): # Check index, middle, ring, pinky
            tip_y = lmList[self.tipIds[i]][2]
            mcp_y = lmList[self.tipIds[i]-2][2]
            if tip_y < mcp_y: # If any finger tip is significantly above its base joint
                fist_check = False
                break
        # Check thumb as well (tip x vs ip x)
        if lmList[self.tipIds[0]][1] < lmList[self.tipIds[0]-1][1]:
             fist_check = False

        if fist_check: # All fingers curled in
            gesture = Gesture.FIST
            if not self.dragging:
                gesture = Gesture.DRAG_START
                self.dragging = True
                # print("DRAG START DETECTED") # Debug
        elif self.dragging:
            # If no longer a fist, stop dragging
            gesture = Gesture.DRAG_END
            self.dragging = False
            # print("DRAG END DETECTED") # Debug


        # If dragging, prioritize move gesture based on index tip for movement
        if self.dragging and gesture != Gesture.DRAG_END:
             # print("DRAGGING MOVE") # Debug
             return Gesture.MOVE # While dragging, the primary action is MOVE

        # Stop processing other gestures if drag just ended
        if gesture == Gesture.DRAG_END:
            self.prev_middle_y = None # Reset scroll state
            return gesture

        # ---- Click Detection ----
        # Left Click: Index and Thumb tips close
        dist_thumb_index, _ = self._calculate_distance(lmList[self.tipIds[0]], lmList[self.tipIds[1]]), None # Thumb tip (4) to Index tip (8)
        # Right Click: Middle and Thumb tips close
        dist_thumb_middle, _ = self._calculate_distance(lmList[self.tipIds[0]], lmList[self.tipIds[2]]), None # Thumb tip (4) to Middle tip (12)

        # Ensure relevant fingers are somewhat up for clicking
        index_up = fingers_state[1] == 1
        middle_up = fingers_state[2] == 1

        if index_up and dist_thumb_index < self.click_threshold:
            gesture = Gesture.LEFT_CLICK
            # print(f"LEFT CLICK: {dist_thumb_index:.1f}") # Debug
        elif middle_up and dist_thumb_middle < self.click_threshold:
            gesture = Gesture.RIGHT_CLICK
            # print(f"RIGHT CLICK: {dist_thumb_middle:.1f}") # Debug

        # ---- Scroll Detection ----
        # Middle and Ring finger up, others down
        elif fingers_state == [0, 0, 1, 1, 0]:
            current_middle_y = lmList[self.tipIds[2]][2] # Use middle finger tip Y
            
            if self.prev_middle_y is not None:
                delta_y = current_middle_y - self.prev_middle_y
                scroll_pixel_threshold = 5 # Adjust this value
                if delta_y > scroll_pixel_threshold: # Moved down
                    gesture = Gesture.SCROLL_DOWN
                elif delta_y < -scroll_pixel_threshold: # Moved up
                    gesture = Gesture.SCROLL_UP
            
            # Update previous Y for next frame's calculation, only if in scroll gesture
            self.prev_middle_y = current_middle_y 

        # ---- Move Detection ----
        # Index finger up, others down 
        # Only trigger move if no other specific gesture (like click or scroll) was detected previously in this frame
        elif fingers_state == [0, 1, 0, 0, 0] and gesture == Gesture.NONE: 
            gesture = Gesture.MOVE
            # Reset scroll state when move gesture is active
            self.prev_middle_y = None 

        # If NOT in scroll gesture state (Middle+Ring up) this frame, reset scroll tracking variable
        # This covers cases where the gesture becomes NONE or MOVE or CLICK etc.
        else: 
             if fingers_state != [0, 0, 1, 1, 0]:
                 self.prev_middle_y = None

        # If no specific gesture matched by now, gesture remains Gesture.NONE as initialized

        return gesture

    def set_click_threshold(self, value):
        self.click_threshold = value

    # Add setters for other thresholds if needed from GUI
    # def set_scroll_threshold(self, value):
    #    self.scroll_threshold = value
    # def set_fist_threshold(self, value):
    #     self.fist_threshold = value

    def set_scroll_threshold(self, value):
        self.scroll_threshold = value

    def set_fist_threshold(self, value):
        self.fist_threshold = value 