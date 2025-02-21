#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw
import requests
import io
import subprocess
import threading
import os
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Right-click Context Menu for Entry
class EntryWithContextMenu(ttk.Entry):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="Cut", command=self.cut_text)
        self.popup_menu.add_command(label="Copy", command=self.copy_text)
        self.popup_menu.add_command(label="Paste", command=self.paste_text)
        self.bind("<Button-3>", self.show_popup_menu)
        logging.debug("Initialized EntryWithContextMenu.")

    def show_popup_menu(self, event):
        logging.debug("Showing context menu.")
        self.popup_menu.tk_popup(event.x_root, event.y_root)

    def cut_text(self):
        logging.debug("Cut text invoked.")
        self.event_generate("<<Cut>>")

    def copy_text(self):
        logging.debug("Copy text invoked.")
        self.event_generate("<<Copy>>")

    def paste_text(self):
        logging.debug("Paste text invoked.")
        self.event_generate("<<Paste>>")

# Helper Functions
def extract_video_id(url):
    logging.debug(f"Extracting video ID from URL: {url}")
    match = re.search(r"(?:v=|youtu\.be/)([^&/\s?]+)", url)
    if match:
        video_id = match.group(1)
        logging.debug(f"Extracted video ID: {video_id}")
        return video_id
    logging.debug("No video ID found in URL.")
    return None

def load_thumbnail(url, thumb_label):
    logging.debug(f"Loading thumbnail for URL: {url}")
    video_id = extract_video_id(url)
    if not video_id:
        messagebox.showerror("Error", "Invalid YouTube URL. Could not extract video ID.")
        logging.error("Invalid YouTube URL provided.")
        return
    thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    try:
        response = requests.get(thumb_url)
        if response.status_code == 404:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            response = requests.get(thumb_url)
        response.raise_for_status()
        image_data = response.content
        pil_image = Image.open(io.BytesIO(image_data))
        aspect_ratio = pil_image.width / pil_image.height
        new_height = 96
        new_width = int(new_height * aspect_ratio)
        pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil_image)
        thumb_label.config(image=photo)
        thumb_label.image = photo
        logging.debug(f"Thumbnail image updated in label. Size: {new_width}x{new_height}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load thumbnail: {e}")
        logging.error("Failed to load thumbnail.", exc_info=True)

def get_total_seconds(h_spin, m_spin, s_spin):
    try:
        hours = int(h_spin.get())
        minutes = int(m_spin.get())
        seconds = int(s_spin.get())
        logging.debug(f"Parsed spinbox times - Hours: {hours}, Minutes: {minutes}, Seconds: {seconds}")
        return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        logging.error("Invalid value in spinbox.", exc_info=True)
        return -1

def get_video_title(url):
    try:
        result = subprocess.run(["yt-dlp", "--get-title", url], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        logging.error("Failed to get video title", exc_info=True)
        return None

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', '', name).replace(" ", "_")[:60]

def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def generate_thumbnail(video_path):
    """Generate a clear thumbnail of the first frame using FFmpeg."""
    thumb_path = f"{os.path.splitext(video_path)[0]}_thumb.jpg"
    if not os.path.exists(thumb_path):
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", "0",
            "-frames:v", "1",
            "-vf", "scale=170:96:force_original_aspect_ratio=decrease,pad=170:96:(ow-iw)/2:(oh-ih)/2",
            "-q:v", "2",
            thumb_path,
            "-y"
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging.debug(f"Generated thumbnail for {video_path}: {thumb_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to generate thumbnail: {e}")
            return None
    try:
        pil_image = Image.open(thumb_path)
        if pil_image.size != (170, 96):
            pil_image = pil_image.resize((170, 96), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil_image)
        logging.debug(f"Loaded thumbnail size: {pil_image.size}")
        return photo
    except Exception as e:
        logging.error(f"Failed to load thumbnail {thumb_path}: {e}")
        return None

def create_placeholder_thumbnail():
    """Create a default placeholder image."""
    placeholder = Image.new("RGB", (170, 96), "gray")
    draw = ImageDraw.Draw(placeholder)
    try:
        draw.text((85, 48), "No Preview", fill="white", anchor="mm", font=None, size=12)
    except TypeError:
        # Some older Pillow versions don't allow the 'size' parameter in draw.text
        draw.text((80, 43), "No Preview", fill="white")
    photo = ImageTk.PhotoImage(placeholder)
    logging.debug("Created placeholder thumbnail of size 170x96")
    return photo

def run_download_and_trim(url, start_sec, duration_sec, mode, message_label,
                          update_local_list_callback=None, complete_callback=None,
                          progress_callback=None):
    def worker():
        try:
            if start_sec < 0 or duration_sec <= 0:
                message_label.config(text="Error: Invalid start time or duration.")
                logging.error(f"Invalid timing - start_sec: {start_sec}, duration_sec: {duration_sec}")
                return

            message_label.config(text="Downloading video (MP4)...")
            download_cmd = [
                "yt-dlp",
                "--newline",
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "-o", "downloaded_video.mp4",
                url
            ]
            proc = subprocess.Popen(download_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                logging.debug("yt-dlp: " + line.strip())
                # Modified regex pattern to better match progress percentage
                m = re.search(r'\[download\].*?(\d+(?:\.\d+)?)%', line)
                if m and progress_callback:
                    percent = float(m.group(1))
                    # Use after() to schedule the update on the main thread
                    message_label.after(1, lambda p=percent: progress_callback(p))
            proc.stdout.close()
            proc.wait()
            if proc.returncode != 0:
                message_label.config(text="Error: yt-dlp failed during download.")
                logging.error("yt-dlp command failed.")
                return

            input_file = "downloaded_video.mp4"
            if not os.path.exists(input_file):
                message_label.config(text="Error: Downloaded file not found.")
                logging.error("Downloaded video file not found.")
                return

            video_title = get_video_title(url) or "video"
            clean_title = sanitize_filename(video_title)
            new_full_filename = f"{clean_title}.mp4"
            try:
                if os.path.exists(new_full_filename):
                    os.remove(new_full_filename)
                os.rename(input_file, new_full_filename)
                input_file = new_full_filename
            except Exception as e:
                message_label.config(text=f"Error: Failed to rename downloaded video: {e}")
                logging.error("Failed to rename downloaded video", exc_info=True)
                return

            message_label.config(text="Trimming video with FFmpeg...")
            def filename_time_format(secs):
                h = secs // 3600
                m = (secs % 3600) // 60
                s = secs % 60
                return f"{h:02d}h{m:02d}m{s:02d}s"
            start_str = filename_time_format(start_sec)
            if mode == "end":
                end_sec = start_sec + duration_sec
                time_str = f"{start_str}-{filename_time_format(end_sec)}"
            else:
                time_str = f"{start_str}+{filename_time_format(duration_sec)}"
            output_filename = f"{clean_title}_{time_str}.mp4"

            trim_cmd = [
                "ffmpeg",
                "-ss", format_time(start_sec),
                "-i", input_file,
                "-t", str(duration_sec),
                "-c:v", "copy",
                "-c:a", "aac",
                output_filename
            ]
            
            result = subprocess.run(trim_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                message_label.config(text=f"Error: FFmpeg trimming failed.\n{result.stderr}")
                logging.error("FFmpeg trimming failed.")
                return

            message_label.config(text=f"Success: {output_filename} created!")
            if update_local_list_callback:
                message_label.after(0, update_local_list_callback)
            # Move the complete_callback inside the timer to ensure the success message stays
            if complete_callback:
                message_label.after(3000, lambda: (
                    complete_callback(),
                    message_label.config(text="")
                ))
            else:
                # If no complete_callback, just clear the message
                message_label.after(3000, lambda: message_label.config(text=""))
        except Exception as e:
            message_label.config(text=f"Error: {e}")
            logging.error("Exception during download and trim.", exc_info=True)
            if complete_callback:
                message_label.after(0, complete_callback)
    threading.Thread(target=worker, daemon=True).start()

# Main GUI Class
class YouTubeTrimmerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader & Trimmer")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        logging.debug("YouTubeTrimmerApp initialized.")

        self.source_option = tk.StringVar(value="local")
        self.mode = tk.StringVar(value="duration")
        self.thumbnail_cache = {}

        # Apply YouTube-inspired style
        style = ttk.Style()
        root.configure(background="#FFFFFF")  # Clean white background

        # Default widget styling
        style.configure("TFrame", background="#FFFFFF")
        style.configure("TLabel", background="#FFFFFF", foreground="#333333")
        style.configure("TEntry", fieldbackground="#FFFFFF", foreground="#333333")

        # YouTube-inspired button style
        style.configure("Modern.TButton",
                        font=("Helvetica", 12),
                        padding=10,
                        background="#FF0000",  # YouTube Red
                        foreground="#FFFFFF",
                        borderwidth=0)
        style.map("Modern.TButton",
                  background=[("active", "#E60000")],  # Slightly darker red when active
                  relief=[("pressed", "flat")])

        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill="both", expand=True)

        # URL Frame
        url_frame = ttk.LabelFrame(self.main_frame, text="YouTube Source", padding="5")
        url_frame.pack(fill="x", pady=5)
        ttk.Label(url_frame, text="YouTube URL:").pack(side="left", padx=5)
        self.url_entry = EntryWithContextMenu(url_frame, width=40)
        self.url_entry.pack(side="left", padx=5)
        ttk.Button(url_frame, text="Load Thumbnail", style="Modern.TButton",
                   command=self.on_load_thumbnail).pack(side="left", padx=5)

        # Thumbnail preview
        self.thumb_label = ttk.Label(self.main_frame)
        self.thumb_label.pack(pady=5)

        # Source Selection
        source_frame = ttk.Frame(self.main_frame)
        source_frame.pack(fill="x", pady=5)
        ttk.Label(source_frame, text="Video Source:").pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="YouTube", variable=self.source_option, value="youtube",
                        command=self.update_source).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Local Video", variable=self.source_option, value="local",
                        command=self.update_source).pack(side="left", padx=5)

        # Local Video Frame
        self.local_frame = ttk.LabelFrame(self.main_frame, text="Local Videos", padding="5")
        local_control_frame = ttk.Frame(self.local_frame)
        local_control_frame.pack(fill="x", pady=5)
        ttk.Label(local_control_frame, text="Selected File:").pack(side="left", padx=5)
        self.local_file_label = ttk.Label(local_control_frame, text="No file selected", relief="sunken", width=40)
        self.local_file_label.pack(side="left", padx=5)
        ttk.Button(local_control_frame, text="Browse", style="Modern.TButton",
                   command=self.on_browse_file).pack(side="left", padx=5)

        tree_frame = ttk.Frame(self.local_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)
        style.configure("Custom.Treeview", rowheight=96, font=("Helvetica", 10))
        self.local_tree = ttk.Treeview(
            tree_frame,
            columns=("Filename", "Size"),
            show="tree headings",
            height=5,
            style="Custom.Treeview"
        )
        self.local_tree.heading("#0", text="Preview")
        self.local_tree.heading("Filename", text="Video Filename")
        self.local_tree.heading("Size", text="Size")
        self.local_tree.column("#0", width=170, anchor="center")
        self.local_tree.column("Filename", width=400, anchor="w")
        self.local_tree.column("Size", width=100, anchor="e")
        self.local_tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.local_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.local_tree.configure(yscrollcommand=scrollbar.set)
        self.local_tree.bind("<Button-1>", self.on_select_local_video)
        ttk.Button(self.local_frame, text="Refresh List", style="Modern.TButton",
                   command=self.update_local_video_list).pack(pady=5)

        self.local_file_path = ""
        self.update_local_video_list()

        # Time Selection Frame
        self.time_frame = ttk.LabelFrame(self.main_frame, text="Trim Settings", padding="5")
        self.time_frame.pack(fill="x", pady=5)

        st_frame = ttk.Frame(self.time_frame)
        st_frame.pack(fill="x", pady=5)
        ttk.Label(st_frame, text="Start Time:").pack(side="left", padx=5)
        self.start_h = ttk.Spinbox(st_frame, from_=0, to=23, width=3)
        self.start_h.set("0")
        self.start_h.pack(side="left", padx=2)
        ttk.Label(st_frame, text="h").pack(side="left", padx=2)
        self.start_m = ttk.Spinbox(st_frame, from_=0, to=59, width=3)
        self.start_m.set("0")
        self.start_m.pack(side="left", padx=2)
        ttk.Label(st_frame, text="m").pack(side="left", padx=2)
        self.start_s = ttk.Spinbox(st_frame, from_=0, to=59, width=3)
        self.start_s.set("0")
        self.start_s.pack(side="left", padx=2)
        ttk.Label(st_frame, text="s").pack(side="left", padx=5)

        mode_frame = ttk.Frame(self.time_frame)
        mode_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(mode_frame, text="Specify End Time", variable=self.mode, value="end",
                        command=self.update_mode).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Specify Duration", variable=self.mode, value="duration",
                        command=self.update_mode).pack(side="left", padx=5)

        self.end_frame = ttk.Frame(self.time_frame)
        self.end_frame.pack(fill="x", pady=5)
        ttk.Label(self.end_frame, text="End Time:").pack(side="left", padx=5)
        self.end_h = ttk.Spinbox(self.end_frame, from_=0, to=23, width=3)
        self.end_h.set("0")
        self.end_h.pack(side="left", padx=2)
        ttk.Label(self.end_frame, text="h").pack(side="left", padx=2)
        self.end_m = ttk.Spinbox(self.end_frame, from_=0, to=59, width=3)
        self.end_m.set("0")
        self.end_m.pack(side="left", padx=2)
        ttk.Label(self.end_frame, text="m").pack(side="left", padx=2)
        self.end_s = ttk.Spinbox(self.end_frame, from_=0, to=59, width=3)
        self.end_s.set("0")
        self.end_s.pack(side="left", padx=2)
        ttk.Label(self.end_frame, text="s").pack(side="left", padx=5)

        self.duration_frame = ttk.Frame(self.time_frame)
        self.duration_frame.pack(fill="x", pady=5)
        ttk.Label(self.duration_frame, text="Duration:").pack(side="left", padx=5)
        self.dur_h = ttk.Spinbox(self.duration_frame, from_=0, to=23, width=3)
        self.dur_h.set("0")
        self.dur_h.pack(side="left", padx=2)
        ttk.Label(self.duration_frame, text="h").pack(side="left", padx=2)
        self.dur_m = ttk.Spinbox(self.duration_frame, from_=0, to=59, width=3)
        self.dur_m.set("0")
        self.dur_m.pack(side="left", padx=2)
        ttk.Label(self.duration_frame, text="m").pack(side="left", padx=2)
        self.dur_s = ttk.Spinbox(self.duration_frame, from_=0, to=59, width=3)
        self.dur_s.set("10")
        self.dur_s.pack(side="left", padx=2)
        ttk.Label(self.duration_frame, text="s").pack(side="left", padx=5)

        # Action Frame
        self.action_frame = ttk.Frame(self.main_frame)
        self.action_frame.pack(fill="x", pady=10)
        self.download_button = ttk.Button(self.action_frame, text="Download and Trim", style="Modern.TButton",
                                          command=self.on_download_and_trim)
        self.download_button.pack(side="top", pady=5)

        # Create a frame for the progress section
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_frame.pack(fill="x", pady=5)
        
        # Initialize message label in the progress frame
        self.message_label = ttk.Label(self.progress_frame, text="", bootstyle="info")
        self.message_label.pack(pady=5)
        
        # Initialize progress bar as None
        self.progress_bar = None
        self.progress_label = None

        self.update_mode()
        self.update_source()

    def update_mode(self):
        if self.mode.get() == "end":
            for widget in self.end_frame.winfo_children():
                widget.configure(state="normal")
            for widget in self.duration_frame.winfo_children():
                widget.configure(state="disabled")
        else:
            for widget in self.end_frame.winfo_children():
                widget.configure(state="disabled")
            for widget in self.duration_frame.winfo_children():
                widget.configure(state="normal")

    def on_load_thumbnail(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return
        load_thumbnail(url, self.thumb_label)

    def on_download_and_trim(self):
        if self.source_option.get() == "youtube":
            url = self.url_entry.get().strip()
            if not url:
                messagebox.showerror("Error", "Please enter a YouTube URL.")
                return
            start_sec = get_total_seconds(self.start_h, self.start_m, self.start_s)
            if start_sec < 0:
                messagebox.showerror("Error", "Invalid start time.")
                return
            if self.mode.get() == "end":
                end_sec = get_total_seconds(self.end_h, self.end_m, self.end_s)
                if end_sec <= start_sec:
                    messagebox.showerror("Error", "End time must be after start time.")
                    return
                duration_sec = end_sec - start_sec
            else:
                duration_sec = get_total_seconds(self.dur_h, self.dur_m, self.dur_s)
                if duration_sec <= 0:
                    messagebox.showerror("Error", "Duration must be > 0.")
                    return
            
            # Clear any existing progress bar
            self.stop_progress_bar()
            
            # Update message and start progress bar
            self.message_label.config(text="Starting download...")
            self.start_progress_bar(determinate=True)
            
            def update_progress(percent):
                if hasattr(self, "progress_bar") and self.progress_bar:
                    self.progress_bar["value"] = percent
                    if hasattr(self, "progress_label") and self.progress_label:
                        self.progress_label.config(text=f"{percent:.1f}%")
                    # Force update the GUI
                    self.root.update_idletasks()
            
            run_download_and_trim(
                url,
                start_sec,
                duration_sec,
                self.mode.get(),
                self.message_label,
                update_local_list_callback=self.update_local_video_list,
                complete_callback=self.stop_progress_bar,
                progress_callback=update_progress
            )

        elif self.source_option.get() == "local":
            if not self.local_file_path:
                messagebox.showerror("Error", "Please select a local video file.")
                return
            if not os.path.exists(self.local_file_path):
                messagebox.showerror("Error", "Selected video file not found.")
                return
            start_sec = get_total_seconds(self.start_h, self.start_m, self.start_s)
            if start_sec < 0:
                messagebox.showerror("Error", "Invalid start time.")
                return
            if self.mode.get() == "end":
                end_sec = get_total_seconds(self.end_h, self.end_m, self.end_s)
                if end_sec <= start_sec:
                    messagebox.showerror("Error", "End time must be after start time.")
                    return
                duration_sec = end_sec - start_sec
            else:
                duration_sec = get_total_seconds(self.dur_h, self.dur_m, self.dur_s)
                if duration_sec <= 0:
                    messagebox.showerror("Error", "Duration must be > 0.")
                    return
            self.message_label.config(text="Starting trim on local video...")
            self.start_progress_bar(determinate=True)

            def worker():
                try:
                    input_file = self.local_file_path
                    base_name = sanitize_filename(os.path.splitext(os.path.basename(input_file))[0])
                    def filename_time_format(secs):
                        h = secs // 3600
                        m = (secs % 3600) // 60
                        s = secs % 60
                        return f"{h:02d}h{m:02d}m{s:02d}s"
                    start_str = filename_time_format(start_sec)
                    if self.mode.get() == "end":
                        end_sec = start_sec + duration_sec
                        time_str = f"{start_str}-{filename_time_format(end_sec)}"
                    else:
                        time_str = f"{start_str}+{filename_time_format(duration_sec)}"
                    output_filename = f"{base_name}_{time_str}.mp4"
                    trim_cmd = [
                        "ffmpeg",
                        "-ss", format_time(start_sec),
                        "-i", input_file,
                        "-t", str(duration_sec),
                        "-c:v", "copy",
                        "-c:a", "aac",
                        output_filename
                    ]
                    result = subprocess.run(trim_cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        self.message_label.config(text=f"Error: FFmpeg trimming failed.\n{result.stderr}")
                        return
                    self.message_label.config(text=f"Success: {output_filename} created!")
                    self.root.after(0, self.update_local_video_list)
                except Exception as e:
                    self.message_label.config(text=f"Error: {e}")
                    logging.error("Exception during local video trimming.", exc_info=True)
                finally:
                    self.root.after(0, self.stop_progress_bar)
            threading.Thread(target=worker, daemon=True).start()

    def update_source(self):
        # Always show both sections so the window displays everything.
        self.url_entry.config(state="normal")
        # Ensure the local_frame is visible.
        if not self.local_frame.winfo_ismapped():
            self.local_frame.pack(fill="x", pady=5)
        # Update the button text based on the selected source.
        if self.source_option.get() == "youtube":
            self.download_button.config(text="Download and Trim")
        else:
            self.download_button.config(text="Trim Local Video")

    def on_browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(("Video Files", "*.mp4;*.mkv;*.avi;*.mov"), ("All Files", "*.*"))
        )
        if file_path:
            self.local_file_path = file_path
            self.local_file_label.config(text=os.path.basename(file_path))

    def on_select_local_video(self, event):
        item = self.local_tree.identify_row(event.y)
        if not item:
            return "break"
        if item in self.local_tree.selection():
            self.local_tree.selection_remove(item)
            self.local_file_path = ""
            self.local_file_label.config(text="No file selected")
        else:
            # Clear any existing selection, then select and focus the clicked item
            self.local_tree.selection_remove(self.local_tree.selection())
            self.local_tree.selection_set(item)
            self.local_tree.focus(item)
            file = self.local_tree.item(item, "values")[0]
            self.local_file_path = os.path.abspath(file)
            self.local_file_label.config(text=file)
        return "break"

    def update_local_video_list(self):
        allowed_ext = ('.mp4', '.mkv', '.avi', '.mov')
        try:
            for item in self.local_tree.get_children():
                self.local_tree.delete(item)
            self.thumbnail_cache.clear()

            files = [f for f in os.listdir('.') if f.lower().endswith(allowed_ext) and os.path.isfile(f)]
            full_videos = [f for f in files if not re.search(r'\d{2}h\d{2}m\d{2}s', f)]
            full_videos.sort()

            for video in full_videos:
                if video not in self.thumbnail_cache:
                    thumbnail = generate_thumbnail(video)
                    self.thumbnail_cache[video] = thumbnail if thumbnail else create_placeholder_thumbnail()
                size_bytes = os.path.getsize(video)
                size_str = (
                    f"{size_bytes / (1024*1024):.2f} MB"
                    if size_bytes > 1024*1024
                    else f"{size_bytes / 1024:.2f} KB"
                )
                self.local_tree.insert(
                    "", "end", text="", values=(video, size_str), image=self.thumbnail_cache[video]
                )
            logging.debug(f"Local video list updated with {len(full_videos)} videos.")
        except Exception as e:
            logging.error("Failed to update local video list.", exc_info=True)

    def start_progress_bar(self, determinate=False):
        # Remove any existing progress bar and label
        if hasattr(self, "progress_bar") and self.progress_bar:
            self.progress_bar.destroy()
        if hasattr(self, "progress_label") and self.progress_label:
            self.progress_label.destroy()

        # Create new progress bar in the progress frame
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode="determinate" if determinate else "indeterminate",
            length=300
        )
        self.progress_bar.pack(fill="x", padx=10, pady=5)

        if determinate:
            self.progress_bar["maximum"] = 100
            self.progress_bar["value"] = 0
            self.progress_label = ttk.Label(self.progress_frame, text="0%")
            self.progress_label.pack(pady=2)
        else:
            self.progress_bar.start(10)

    def stop_progress_bar(self):
        if hasattr(self, "progress_bar") and self.progress_bar:
            if self.progress_bar.cget("mode") == "indeterminate":
                self.progress_bar.stop()
            self.progress_bar.destroy()
            self.progress_bar = None
        
        if hasattr(self, "progress_label") and self.progress_label:
            self.progress_label.destroy()
            self.progress_label = None

    def update_progress_bar(self, percent):
        if self.progress_bar and self.progress_bar.cget("mode") == "determinate":
            self.progress_bar["value"] = percent
        if hasattr(self, "progress_label") and self.progress_label is not None:
            self.progress_label.config(text=f"{percent:.1f}%")

if __name__ == "__main__":
    root = ttk.Window(themename="flatly")  # Using ttkbootstrap window with a base theme
    logging.debug("Starting YouTubeTrimmerApp with ttkbootstrap theme...")
    try:
        subprocess.run(["ffmpeg", "-version"], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        messagebox.showwarning("FFmpeg Missing", "FFmpeg not found in PATH. Please install FFmpeg!")
        root.destroy()
    else:
        app = YouTubeTrimmerApp(root)
        # Center the window on the screen
        width, height = 1400, 900
        root.update_idletasks()  # Ensure the window has been drawn
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.mainloop()
