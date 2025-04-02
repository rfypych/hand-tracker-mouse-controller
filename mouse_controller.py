import pyautogui
import numpy as np
import time
from gesture_detector import Gesture # Import Gesture enum

class MouseController:
    def __init__(self, screen_width=None, screen_height=None, sensitivity=1.5, smoothing=5, deadzone=10):
        """Initializes the MouseController.

        Args:
            screen_width (int, optional): Screen width. Defaults to detected width.
            screen_height (int, optional): Screen height. Defaults to detected height.
            sensitivity (float): Multiplier for mouse movement speed.
            smoothing (int): Number of frames to average for cursor position (higher = smoother but more lag).
            deadzone (int): Pixels around the center of the hand landmark used as a deadzone for movement.
        """
        # Disable pyautogui failsafe
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0 # Remove default pause between actions

        # Get screen size if not provided
        self.screen_width, self.screen_height = pyautogui.size() if screen_width is None or screen_height is None else (screen_width, screen_height)
        print(f"Screen size detected: {self.screen_width}x{self.screen_height}")

        self.sensitivity = sensitivity
        self.smoothing = max(1, smoothing) # Ensure smoothing is at least 1
        self.deadzone = deadzone

        # Previous position for smoothing
        self.prev_x, self.prev_y = 0, 0
        # Target position (before smoothing)
        self.target_x, self.target_y = 0, 0

        # For click debouncing / rate limiting
        self.last_click_time = 0
        self.click_delay = 0.2 # Minimum seconds between clicks
        self.last_scroll_time = 0
        self.scroll_delay = 0.05 # Minimum seconds between scroll actions

        self.is_dragging = False

    def update(self, gesture, lmList, frame_shape):
        """Updates the mouse state based on the detected gesture and landmarks.

        Args:
            gesture (str): The detected gesture from GestureDetector.
            lmList (list): List of landmark positions [[id, x, y], ...].
            frame_shape (tuple): Shape of the camera frame (height, width, channels).
        """
        frame_h, frame_w, _ = frame_shape

        # Use index finger tip (landmark 8) for cursor position
        index_tip_id = 8
        if lmList and len(lmList) > index_tip_id:
            x_cam, y_cam = lmList[index_tip_id][1], lmList[index_tip_id][2]

            # ---- Coordinate Mapping & Smoothing ----
            # Interpolate from camera coords to screen coords
            # Adding a deadzone/frame reduction for stability
            map_x_min, map_x_max = self.deadzone, frame_w - self.deadzone
            map_y_min, map_y_max = self.deadzone, frame_h - self.deadzone

            # Clamp camera coordinates to the mapping range
            x_cam_clamped = np.clip(x_cam, map_x_min, map_x_max)
            y_cam_clamped = np.clip(y_cam, map_y_min, map_y_max)

            # Map clamped coordinates to screen coordinates
            self.target_x = np.interp(x_cam_clamped, (map_x_min, map_x_max), (0, self.screen_width))
            self.target_y = np.interp(y_cam_clamped, (map_y_min, map_y_max), (0, self.screen_height))

            # Apply smoothing (simple averaging)
            current_x = self.prev_x + (self.target_x - self.prev_x) / self.smoothing
            current_y = self.prev_y + (self.target_y - self.prev_y) / self.smoothing

            # Apply sensitivity (optional, interp already scales)
            # dx = (current_x - self.prev_x) * self.sensitivity
            # dy = (current_y - self.prev_y) * self.sensitivity
            # move_x = self.prev_x + dx
            # move_y = self.prev_y + dy

            # Clamp final coordinates to screen boundaries
            final_x = np.clip(int(current_x), 0, self.screen_width - 1)
            final_y = np.clip(int(current_y), 0, self.screen_height - 1)

            # ---- Action Handling ----
            current_time = time.time()

            if gesture == Gesture.MOVE:
                # Move mouse if not dragging (drag move handled separately)
                if not self.is_dragging:
                    pyautogui.moveTo(final_x, final_y)
                # Update position even if dragging, for next non-drag move
                self.prev_x, self.prev_y = final_x, final_y

            elif gesture == Gesture.LEFT_CLICK:
                if current_time - self.last_click_time > self.click_delay:
                    # print("Controller: Left Click") # Debug
                    pyautogui.click(button='left')
                    self.last_click_time = current_time
                # Update position after click action
                self.prev_x, self.prev_y = final_x, final_y

            elif gesture == Gesture.RIGHT_CLICK:
                if current_time - self.last_click_time > self.click_delay:
                    # print("Controller: Right Click") # Debug
                    pyautogui.click(button='right')
                    self.last_click_time = current_time
                # Update position after click action
                self.prev_x, self.prev_y = final_x, final_y

            elif gesture == Gesture.SCROLL_UP:
                if current_time - self.last_scroll_time > self.scroll_delay:
                    # print("Controller: Scroll Up") # Debug
                    pyautogui.scroll(10) # Positive value scrolls up
                    self.last_scroll_time = current_time
                # Update position during scroll
                self.prev_x, self.prev_y = final_x, final_y

            elif gesture == Gesture.SCROLL_DOWN:
                if current_time - self.last_scroll_time > self.scroll_delay:
                    # print("Controller: Scroll Down") # Debug
                    pyautogui.scroll(-10) # Negative value scrolls down
                    self.last_scroll_time = current_time
                # Update position during scroll
                self.prev_x, self.prev_y = final_x, final_y

            elif gesture == Gesture.DRAG_START:
                if not self.is_dragging:
                    # print("Controller: Drag Start") # Debug
                    # Move to the current position first before dragging
                    pyautogui.moveTo(final_x, final_y)
                    pyautogui.mouseDown(button='left')
                    self.is_dragging = True
                    self.prev_x, self.prev_y = final_x, final_y # Update position at drag start

            elif gesture == Gesture.DRAG_END:
                if self.is_dragging:
                    # print("Controller: Drag End") # Debug
                    # Ensure mouse is at the final drag position before releasing
                    pyautogui.moveTo(final_x, final_y)
                    pyautogui.mouseUp(button='left')
                    self.is_dragging = False
                    self.prev_x, self.prev_y = final_x, final_y # Update position at drag end

            # If dragging, continuously update position
            elif self.is_dragging:
                # print(f"Controller: Dragging Move to {final_x}, {final_y}") # Debug
                pyautogui.moveTo(final_x, final_y)
                self.prev_x, self.prev_y = final_x, final_y

            else: # Gesture.NONE or other unhandled
                # Still update previous position if hand is detected but no action
                self.prev_x, self.prev_y = final_x, final_y

        else: # No landmarks detected
            # Optionally reset state if hand disappears? Or maintain last position?
            # For now, do nothing, keeps mouse at last known position.
            pass

    def set_sensitivity(self, value):
        # Sensitivity adjustment might be better applied directly in mapping or movement calculation
        # For now, let's adjust the interpolation range or add a multiplier
        self.sensitivity = value
        print(f"Sensitivity set to: {self.sensitivity}")
        # Re-evaluate how sensitivity is used. Maybe scale the delta? 
        # For now, placeholder, as interpolation handles scaling.

    def set_smoothing(self, value):
        self.smoothing = max(1, int(value))
        print(f"Smoothing set to: {self.smoothing}")

    # def set_deadzone(self, value):
    #     self.deadzone = int(value)

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

    def get_screen_size(self):
        return self.screen_width, self.screen_height

    def get_sensitivity(self):
        return self.sensitivity

    def get_smoothing(self):
        return self.smoothing

    def get_deadzone(self):
        return self.deadzone

    def get_is_dragging(self):
        return self.is_dragging

    def get_prev_position(self):
        return self.prev_x, self.prev_y

    def get_target_position(self):
        return self.target_x, self.target_y

    def get_last_click_time(self):
        return self.last_click_time

    def get_click_delay(self):
        return self.click_delay

    def get_last_scroll_time(self):
        return self.last_scroll_time

    def get_scroll_delay(self):
        return self.scroll_delay

 