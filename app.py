import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import subprocess
import re
import platform
import speedtest
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import math


# ====== CONFIGURATION ======
WATERMARK_TEXT = "Network Monitor v1.0 By Gabriel Bravo 2025"
DARK_BG = "#2d2d2d"
DARK_FG = "#e0e0e0"
ACCENT_COLOR = "#4e79a7"
GRAPH_BG = "#1e1e1e"
GRAPH_GRID = "#3a3a3a"
GRAPH_LINE = "#ff7f0e"
# ===========================

def patch_speedtest():
    """Monkey-patch speedtest-cli to work with PyInstaller"""
    try:
        import speedtest
        # Fix for __builtin__ module
        if not hasattr(speedtest, '__builtin__'):
            import builtins
            speedtest.__builtin__ = builtins
        
        # Fix for file descriptor issue
        if hasattr(speedtest, 'stderr'):
            speedtest.stderr = sys.stderr
    except ImportError:
        pass

# Apply patches before creating the GUI
patch_speedtest()

class NetworkTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Tester")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        self.root.configure(bg=DARK_BG)
        
        # Initialize value_labels
        self.value_labels = []
        
        # Configure styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure(".", background=DARK_BG, foreground=DARK_FG, font=('Arial', 10))
        self.style.configure("TButton", padding=10, background="#3a3a3a")
        self.style.configure("Header.TLabel", font=('Arial', 12, 'bold'), foreground="#ffffff")
        self.style.configure("Stop.TButton", foreground="#ff6b6b", font=('Arial', 10, 'bold'))
        self.style.map("TButton", background=[('active', '#4a4a4a')])
        
        # Main frame
        self.main_frame = ttk.Frame(root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_label = ttk.Label(self.main_frame, text="Network Testing Tool", style="Header.TLabel")
        header_label.pack(pady=(0, 20))
        
        # Control buttons frame
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.pack(pady=10)
        
        self.speed_test_btn = ttk.Button(self.control_frame, 
                                       text="Speed Test", 
                                       command=self.start_speed_test)
        self.speed_test_btn.grid(row=0, column=0, padx=10)
        
        self.latency_test_btn = ttk.Button(self.control_frame, 
                                         text="Latency Test", 
                                         command=self.latency_test_setup)
        self.latency_test_btn.grid(row=0, column=1, padx=10)
        
        # Content frame
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Watermark
        self.watermark = ttk.Label(
            self.root, 
            text=WATERMARK_TEXT,
            font=('Arial', 8),
            foreground="#555555",
            background=DARK_BG
        )
        self.watermark.place(relx=0.99, rely=0.99, anchor='se')
        
        # Initialize remaining variables
        self.latency_running = False
        self.ping_times = []
        self.time_elapsed = []
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_failed = 0
        self.start_time = 0
        
        # Show main menu
        self.show_main_menu()

    def format_time(self, seconds):
        """Format time as MM:SS minutes or HH:MM:SS hours"""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds_remaining = seconds % 60
            return f"{int(minutes):02d}:{int(seconds_remaining):02d} minutes"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds_remaining = seconds % 60
            return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds_remaining):02d} hours"

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        # Safely clear the value_labels
        if hasattr(self, 'value_labels') and self.value_labels:
            self.value_labels.clear()

    def show_main_menu(self):
        self.latency_running = False
        self.clear_content_frame()
        welcome_label = ttk.Label(
            self.content_frame, 
            text="Welcome to Network Tester!\n\nSelect a test from the options above.",
            foreground=DARK_FG
        )
        welcome_label.pack(pady=50)

    # Speed Test Implementation
    def start_speed_test(self):
        self.clear_content_frame()
        
        progress_frame = ttk.Frame(self.content_frame)
        progress_frame.pack(pady=20)
        
        self.status_label = ttk.Label(progress_frame, text="Initializing speed test...")
        self.status_label.pack(pady=10)
        
        self.progress = ttk.Progressbar(progress_frame, length=400, mode="indeterminate")
        self.progress.pack(pady=10)
        self.progress.start()
        
        self.cancel_btn = ttk.Button(self.content_frame, 
                                    text="Cancel", 
                                    command=self.show_main_menu)
        self.cancel_btn.pack(pady=10)
        
        def run_test():
            try:
                self.status_label.config(text="Finding best server...")
                st = speedtest.Speedtest()
                st.get_best_server()
                
                self.status_label.config(text="Testing download speed...")
                download = st.download() / 1_000_000  # Mbps
                
                self.status_label.config(text="Testing upload speed...")
                upload = st.upload() / 1_000_000  # Mbps
                
                self.status_label.config(text="Calculating ping...")
                ping = st.results.ping
                
                self.progress.stop()
                self.display_speed_results(download, upload, ping)
                
            except Exception as e:
                self.progress.stop()
                messagebox.showerror("Error", f"Speed test failed: {str(e)}")
                self.show_main_menu()
        
        threading.Thread(target=run_test, daemon=True).start()

    def draw_tachometer(self, ax, value, max_value, title, color):
        """Draw a tachometer-style gauge for speed results"""
        # Set up the gauge
        ax.set_aspect('equal')
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(0, 1.2)
        ax.axis('off')
        ax.set_facecolor(GRAPH_BG)
        
        # Draw the gauge arc
        arc = patches.Arc((0, 0), width=2, height=2, angle=0, theta1=0, theta2=180, 
                         linewidth=2, color='gray')
        ax.add_patch(arc)
        
        # Calculate needle position
        angle = 180 * min(value / max_value, 1.0)
        angle_rad = math.radians(angle)
        needle_length = 1
        x = needle_length * math.cos(angle_rad)
        y = needle_length * math.sin(angle_rad)
        
        # Draw needle
        ax.plot([0, x], [0, y], color=color, linewidth=3, solid_capstyle='round')
        
        # Draw center circle
        center_circle = plt.Circle((0, 0), 0.05, color=color)
        ax.add_patch(center_circle)
        
        # Add value text
        ax.text(0, -0.2, f"{value:.1f} Mbps", ha='center', va='center', 
               fontsize=12, color='white', weight='bold')
        
        # Add title
        ax.text(0, 1.1, title, ha='center', va='center', 
               fontsize=12, color='white', weight='bold')
        
        # Add scale markers
        for i in range(0, 181, 30):
            rad = math.radians(i)
            x1 = 1.05 * math.cos(rad)
            y1 = 1.05 * math.sin(rad)
            x2 = 1.15 * math.cos(rad)
            y2 = 1.15 * math.sin(rad)
            ax.plot([x1, x2], [y1, y2], color='white', linewidth=1)
            
            # Add scale labels
            if i > 0:
                value_label = (i / 180) * max_value
                x_text = 1.25 * math.cos(rad)
                y_text = 1.25 * math.sin(rad)
                ax.text(x_text, y_text, f"{value_label:.0f}", 
                       ha='center', va='center', color='white', fontsize=8)

    def display_speed_results(self, download, upload, ping):
        self.clear_content_frame()
        
        results_frame = ttk.Frame(self.content_frame)
        results_frame.pack(pady=20)
        
        ttk.Label(results_frame, text="Speed Test Results", style="Header.TLabel").pack(pady=(0, 20))
        
        # Results grid
        metrics = [
            ("Download:", f"{download:.2f} Mbps"),
            ("Upload:", f"{upload:.2f} Mbps"),
            ("Ping:", f"{ping:.2f} ms")
        ]
        
        for label, value in metrics:
            frame = ttk.Frame(results_frame)
            frame.pack(fill=tk.X, pady=5)
            ttk.Label(frame, text=label, foreground="#aaaaaa").pack(side=tk.LEFT)
            ttk.Label(frame, text=value, foreground="#ffffff").pack(side=tk.LEFT)
        
        # ====== TACHOMETER GAUGES ======
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), facecolor=GRAPH_BG)
        fig.subplots_adjust(wspace=0.4)
        
        # Calculate max value for gauges (round up to nearest 50)
        max_val = max(download, upload, 50)
        max_val = ((int(max_val) // 50) + 1) * 50
        
        # Download gauge
        self.draw_tachometer(ax1, download, max_val, "Download Speed", ACCENT_COLOR)
        
        # Upload gauge
        self.draw_tachometer(ax2, upload, max_val, "Upload Speed", '#59a14f')
        
        canvas = FigureCanvasTkAgg(fig, master=results_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=20)
        # ===============================
        
        ttk.Button(self.content_frame, 
                  text="Back to Main Menu", 
                  command=self.show_main_menu).pack(pady=10)

    # Latency Test Implementation
    def latency_test_setup(self):
        target = simpledialog.askstring("Target Selection", 
                                       "Enter IP/hostname (default: 8.8.8.8):",
                                       initialvalue="8.8.8.8")
        if target is None: 
            return
        self.start_latency_test(target.strip() or "8.8.8.8")

    def start_latency_test(self, target):
        self.clear_content_frame()
        self.latency_running = True
        
        # Reset metrics
        self.ping_times = []
        self.time_elapsed = []
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_failed = 0
        self.start_time = time.time()
        
        # Control panel
        control_panel = ttk.Frame(self.content_frame)
        control_panel.pack(fill=tk.X, pady=10)
        
        self.stop_btn = ttk.Button(control_panel, 
                                 text="⏹ Stop Test", 
                                 style="Stop.TButton", 
                                 command=self.stop_latency_test)
        self.stop_btn.pack(side=tk.RIGHT, padx=10)
        
        # Stats display
        stats_frame = ttk.Frame(self.content_frame)
        stats_frame.pack(pady=10)
        
        # Create labels and store references
        stats_labels = [
            ("Target:", target),
            ("Time Elapsed:", "0 seconds"),
            ("Packets Sent:", "0"),
            ("Success Rate:", "0%"),
            ("Received:", "0"),
            ("Failed:", "0")
        ]
        
        self.value_labels = []  # Reinitialize for this test
        for i in range(0, len(stats_labels), 2):
            row_frame = ttk.Frame(stats_frame)
            row_frame.pack(fill=tk.X)
            for j in range(2):
                if i+j >= len(stats_labels): 
                    break
                label_text, initial_value = stats_labels[i+j]
                frame = ttk.Frame(row_frame)
                frame.pack(side=tk.LEFT, padx=20, pady=2)
                ttk.Label(frame, text=label_text, foreground="#aaaaaa").pack(side=tk.LEFT)
                value_label = ttk.Label(frame, text=initial_value, width=15, foreground="#ffffff")
                value_label.pack(side=tk.LEFT)
                self.value_labels.append(value_label)

        # Enhanced graph
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(6, 4), facecolor=GRAPH_BG)
        self.ax.set_facecolor(GRAPH_BG)
        self.ax.set_title('Network Latency', color='white', fontweight='bold')
        self.ax.set_xlabel('Time (seconds)', color='white')
        self.ax.set_ylabel('Ping (ms)', color='white')
        self.ax.grid(True, color=GRAPH_GRID, linestyle='--', alpha=0.7)
        self.ax.tick_params(colors='white')
        self.line, = self.ax.plot([], [], color=GRAPH_LINE, linewidth=2, 
                                marker='o', markersize=4, markeredgecolor='white')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.content_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Start monitoring threads
        threading.Thread(target=self.run_latency_monitor, 
                        args=(target,), 
                        daemon=True).start()
        threading.Thread(target=self.update_latency_ui, 
                        daemon=True).start()

    def run_latency_monitor(self, target):
        ping_cmd = ["ping", "-n", "1", target] if platform.system() == "Windows" else ["ping", "-c", "1", "-W", "1", target]
        
        while self.latency_running:
            self.packets_sent += 1
            try:
                result = subprocess.run(ping_cmd, 
                                       capture_output=True, 
                                       text=True, 
                                       timeout=1)
                if result.returncode == 0:
                    pattern = r"time=(\d+\.?\d*) ms" if platform.system() != "Windows" else r"time[=<](\d+)ms"
                    match = re.search(pattern, result.stdout)
                    if match:
                        ping_time = float(match.group(1))
                        self.ping_times.append(ping_time)
                        self.time_elapsed.append(time.time() - self.start_time)
                        self.packets_received += 1
                    else:
                        self.packets_failed += 1
                else:
                    self.packets_failed += 1
            except Exception as e:
                self.packets_failed += 1
            
            time.sleep(0.5)

    def update_latency_ui(self):
        while self.latency_running:
            try:
                elapsed = time.time() - self.start_time
                success_rate = (self.packets_received / self.packets_sent * 100) if self.packets_sent else 0
                
                # Use improved time formatting
                elapsed_str = self.format_time(elapsed)
                
                values = [
                    elapsed_str,
                    str(self.packets_sent),
                    f"{success_rate:.1f}%",
                    str(self.packets_received),
                    str(self.packets_failed)
                ]
                
                # Update only the dynamic labels
                for label, value in zip(self.value_labels[1:], values):
                    label.config(text=value)
                
                if self.ping_times:
                    self.line.set_data(self.time_elapsed, self.ping_times)
                    self.ax.relim()
                    self.ax.autoscale_view()
                    self.ax.set_ylim(0, max(self.ping_times)*1.2 if self.ping_times else 100)
                    self.canvas.draw()
                
                time.sleep(0.5)
            except Exception as e:
                print(f"UI Update Error: {str(e)}")
                break

    def stop_latency_test(self):
        self.latency_running = False
        self.stop_btn.config(state=tk.DISABLED, text="Stopping...")
        self.show_test_summary()

    def show_test_summary(self):
        duration = self.format_time(time.time() - self.start_time)
        avg_latency = sum(self.ping_times)/len(self.ping_times) if self.ping_times else 0
        summary = (
            f"Test Summary:\n\n"
            f"Target: {self.value_labels[0].cget('text')}\n"
            f"Duration: {duration}\n"
            f"Packets Sent: {self.packets_sent}\n"
            f"Success Rate: {(self.packets_received/self.packets_sent*100):.1f}%\n"
            f"Average Latency: {avg_latency:.1f} ms"
        )
        
        messagebox.showinfo("Test Complete", summary)
        self.show_main_menu()

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkTester(root)
    root.mainloop()