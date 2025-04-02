import pygame
import os
import time
from gesture_detector import Gesture # Import Gesture enum

class SoundFeedback:
    def __init__(self, sound_dir="assets", click_sound="click.wav", drag_sound="drag_start.wav"):
        """Initializes the SoundFeedback system.

        Args:
            sound_dir (str): Directory containing sound files.
            click_sound (str): Filename for the click sound.
            drag_sound (str): Filename for the drag start sound.
        """
        self.sounds = {}
        self.last_played = {}
        self.play_delay = 0.1 # Minimum delay between playing the same sound

        try:
            pygame.mixer.init()
            print("Pygame mixer initialized for sound feedback.")

            click_path = os.path.join(sound_dir, click_sound)
            drag_path = os.path.join(sound_dir, drag_sound)

            if os.path.exists(click_path):
                self.sounds[Gesture.LEFT_CLICK] = pygame.mixer.Sound(click_path)
                self.sounds[Gesture.RIGHT_CLICK] = pygame.mixer.Sound(click_path) # Use same sound for both clicks
                print(f"Loaded sound for CLICK: {click_path}")
            else:
                print(f"Warning: Click sound file not found at {click_path}")

            if os.path.exists(drag_path):
                self.sounds[Gesture.DRAG_START] = pygame.mixer.Sound(drag_path)
                print(f"Loaded sound for DRAG_START: {drag_path}")
            else:
                print(f"Warning: Drag sound file not found at {drag_path}")

        except pygame.error as e:
            print(f"Error initializing pygame mixer or loading sounds: {e}")
            print("Sound feedback will be disabled.")
            self.sounds = {} # Disable sounds if init fails
        except Exception as e:
            print(f"An unexpected error occurred during sound initialization: {e}")
            self.sounds = {} # Disable sounds

    def play(self, gesture):
        """Plays the sound associated with the given gesture, with rate limiting."""
        sound = self.sounds.get(gesture)
        if sound:
            current_time = time.time()
            last_time = self.last_played.get(gesture, 0)
            if current_time - last_time > self.play_delay:
                try:
                    sound.play()
                    self.last_played[gesture] = current_time
                    # print(f"Played sound for {gesture}") # Debug
                except pygame.error as e:
                    print(f"Error playing sound for {gesture}: {e}")

    def quit(self):
        """Quit the pygame mixer."""
        if pygame.mixer.get_init():
            pygame.mixer.quit()
            print("Pygame mixer quit.") 