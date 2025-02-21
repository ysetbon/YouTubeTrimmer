# YouTube Video Downloader & Trimmer

This project is a graphical application built with Python and Tkinter that allows you to download videos from YouTube using yt-dlp and trim them using FFmpeg. It also supports trimming local video files.

## Features

- **Download YouTube Videos**: Uses yt-dlp to download the best quality video and audio, then merges them into an MP4 file.
- **Thumbnail Preview**: Automatically loads YouTube video thumbnails.
- **Video Trimming**: Trim downloaded or local videos based on a start time and either an end time or a specified duration using FFmpeg.
- **Local Video List**: Displays a list of local video files with generated or placeholder thumbnails.
- **Context Menu**: Provides right-click context menu functionality for entry fields (cut, copy, paste).
- **User-Friendly GUI**: A visually appealing and intuitive interface built with Tkinter.

## Requirements

- **Python 3.x**
- **yt-dlp**: [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- **FFmpeg**: [FFmpeg Official Website](https://ffmpeg.org/)
- **Pillow**: For image handling (`pip install pillow`)
- **Tkinter**: Usually comes pre-installed with Python

Other Python packages used: `requests`, `logging`

## Installation

1. **Install Python Dependencies**:

    ```bash
    pip install pillow requests yt-dlp
    ```

2. **Install FFmpeg**:

   FFmpeg is required for video trimming. You can install FFmpeg manually or, if you're on Windows, run the provided installer script:

    ```bash
    python ffpinstall.py
    ```

   *Note*: After running the script, you might need to restart your session for the PATH changes to take effect.

## Usage

1. **Launch the Application**:

    ```bash
    python gui.py
    ```

2. **For YouTube Videos**:
    - Enter a valid YouTube URL in the provided field.
    - Click **Load Thumbnail** to preview the video.
    - Set the **Start Time** and choose whether to specify an **End Time** or a **Duration**.
    - Click **Download and Trim** to download and trim the video.

3. **For Local Videos**:
    - Select the **Local Video** option.
    - Browse to choose a video file, or select one from the displayed list.
    - Set the trim settings (start time, duration/end time).
    - Click **Trim Local Video** to trim the video.

## Directory Structure 