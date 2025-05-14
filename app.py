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

class NetworkTester:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Tester")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Variables
        self.latency_running = False
        self.ping_times = []
        self.time_elapsed = []
        self.packets_sent = 0
        self.packets_received = 0
        self.packets_failed = 0
        self.start_time = 0
        self.value_labels = []  # Store references to value labels
        
        # Style Configuration
        self.style = ttk.Style()
        self.style.configure("TButton", padding=10, font=('Arial', 10))
        self.style.configure("TLabel", font=('Arial', 10))
        self.style.configure("Header.TLabel", font=('Arial', 12, 'bold'))
        self.style.configure("Stop.TButton", foreground="red", font=('Arial', 10, 'bold'))
        
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
        
        # Initial welcome message
        self.show_main_menu()

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.value_labels.clear()

    def show_main_menu(self):
        self.latency_running = False
        self.clear_content_frame()
        welcome_label = ttk.Label(self.content_frame, 
                                 text="Welcome to Network Tester!\n\nSelect a test from the options above.")
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
            ttk.Label(frame, text=label).pack(side=tk.LEFT)
            ttk.Label(frame, text=value).pack(side=tk.LEFT)
        
        # Visualization
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(["Download", "Upload"], [download, upload], color=['#1f77b4', '#2ca02c'])
        ax.set_ylabel('Speed (Mbps)')
        ax.set_title('Speed Performance')
        
        canvas = FigureCanvasTkAgg(fig, master=results_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=20)
        
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
            ("Time Elapsed:", "0s"),
            ("Packets Sent:", "0"),
            ("Success Rate:", "0%"),
            ("Received:", "0"),
            ("Failed:", "0")
        ]
        
        self.value_labels = []
        for i in range(0, len(stats_labels), 2):
            row_frame = ttk.Frame(stats_frame)
            row_frame.pack(fill=tk.X)
            for j in range(2):
                if i+j >= len(stats_labels): 
                    break
                label_text, initial_value = stats_labels[i+j]
                frame = ttk.Frame(row_frame)
                frame.pack(side=tk.LEFT, padx=20, pady=2)
                ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
                value_label = ttk.Label(frame, text=initial_value, width=10)
                value_label.pack(side=tk.LEFT)
                self.value_labels.append(value_label)

        # Live graph
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.ax.set_title('Network Latency')
        self.ax.set_xlabel('Time (seconds)')
        self.ax.set_ylabel('Ping (ms)')
        self.ax.grid(True)
        
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
                
                # Update value labels
                values = [
                    f"{elapsed:.1f}s",
                    str(self.packets_sent),
                    f"{success_rate:.1f}%",
                    str(self.packets_received),
                    str(self.packets_failed)
                ]
                
                # Update only the dynamic labels (skip Target label at index 0)
                for label, value in zip(self.value_labels[1:], values):
                    label.config(text=value)
                
                # Update graph
                if self.ping_times:
                    self.ax.clear()
                    self.ax.plot(self.time_elapsed, self.ping_times, 'b-')
                    self.ax.set_ylim(0, max(self.ping_times)*1.2 if self.ping_times else 100)
                    self.ax.set_title('Network Latency')
                    self.ax.grid(True)
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
        summary = (
            f"Test Summary:\n\n"
            f"Target: {self.value_labels[0].cget('text')}\n"
            f"Duration: {self.value_labels[1].cget('text')}\n"
            f"Packets Sent: {self.packets_sent}\n"
            f"Success Rate: {(self.packets_received/self.packets_sent*100):.1f}%\n"
            f"Average Latency: {sum(self.ping_times)/len(self.ping_times):.1f} ms" if self.ping_times else ""
        )
        
        messagebox.showinfo("Test Complete", summary)
        self.show_main_menu()

if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkTester(root)
    root.mainloop()