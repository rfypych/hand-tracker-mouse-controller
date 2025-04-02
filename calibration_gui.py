import tkinter as tk
from tkinter import ttk

class CalibrationGUI:
    def __init__(self, mouse_controller, gesture_detector):
        """Initializes the Calibration GUI.

        Args:
            mouse_controller: Instance of MouseController.
            gesture_detector: Instance of GestureDetector.
        """
        self.controller = mouse_controller
        self.detector = gesture_detector
        self.root = None

    def _update_smoothing(self, val):
        """Callback for smoothing slider."""
        smoothing_val = int(float(val))
        self.controller.set_smoothing(smoothing_val)
        # Optional: Display current value
        if hasattr(self, 'smoothing_label_val'):
            self.smoothing_label_val.config(text=f"{smoothing_val}")

    def _update_click_threshold(self, val):
        """Callback for click threshold slider."""
        threshold_val = int(float(val))
        self.detector.set_click_threshold(threshold_val)
        # Optional: Display current value
        if hasattr(self, 'click_label_val'):
            self.click_label_val.config(text=f"{threshold_val}")

    # Add callbacks for other parameters if needed (e.g., sensitivity, fist threshold)
    # def _update_sensitivity(self, val):
    #     sensitivity_val = float(val)
    #     self.controller.set_sensitivity(sensitivity_val)
    #     if hasattr(self, 'sensitivity_label_val'):
    #         self.sensitivity_label_val.config(text=f"{sensitivity_val:.1f}")

    def _setup_widgets(self):
        """Creates and places the GUI widgets."""
        self.root.title("Virtual Mouse Calibration")
        # Make window stay on top
        self.root.attributes('-topmost', True)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Smoothing Slider ---
        smoothing_frame = ttk.Frame(main_frame)
        smoothing_frame.grid(row=0, column=0, pady=5, sticky=tk.W)
        ttk.Label(smoothing_frame, text="Smoothing (1-20):").pack(side=tk.LEFT)
        self.smoothing_label_val = ttk.Label(smoothing_frame, text=f"{self.controller.get_smoothing()}", width=3)
        self.smoothing_label_val.pack(side=tk.RIGHT, padx=5)
        smoothing_slider = ttk.Scale(
            main_frame, 
            from_=1, 
            to=20, 
            orient=tk.HORIZONTAL, 
            value=self.controller.get_smoothing(),
            command=self._update_smoothing
        )
        smoothing_slider.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # --- Click Threshold Slider ---
        click_frame = ttk.Frame(main_frame)
        click_frame.grid(row=2, column=0, pady=5, sticky=tk.W)
        ttk.Label(click_frame, text="Click Threshold (10-100):").pack(side=tk.LEFT)
        self.click_label_val = ttk.Label(click_frame, text=f"{self.detector.click_threshold}", width=3)
        self.click_label_val.pack(side=tk.RIGHT, padx=5)
        click_slider = ttk.Scale(
            main_frame, 
            from_=10, 
            to=100, 
            orient=tk.HORIZONTAL,
            value=self.detector.click_threshold,
            command=self._update_click_threshold
        )
        click_slider.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        # Add more sliders here if needed (e.g., sensitivity)
        
        # Add padding to all widgets in main_frame
        for child in main_frame.winfo_children():
            if isinstance(child, ttk.Scale):
                child.grid_configure(pady=5)
            else: # Frames containing labels
                 for grandchild in child.winfo_children():
                      grandchild.pack_configure(padx=5)
                 child.grid_configure(pady=(5,0)) # Padding below label frames

    def run(self):
        """Starts the Tkinter main loop."""
        self.root = tk.Tk()
        self._setup_widgets()
        self.root.mainloop() 