import os
import requests
import zipfile
import tempfile
import shutil
import winreg

def download_ffmpeg(url, dest_path):
    print("Downloading FFmpeg from:", url)
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(response.raw, f)
    print("Download complete.")

def extract_zip(zip_path, extract_to):
    print("Extracting FFmpeg...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")

def add_to_user_path(new_path):
    print("Adding to user PATH:", new_path)
    try:
        env_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            current_path, _ = winreg.QueryValueEx(env_key, "PATH")
        except FileNotFoundError:
            current_path = ""
        if new_path.lower() not in current_path.lower():
            new_path_value = current_path + ";" + new_path if current_path else new_path
            winreg.SetValueEx(env_key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path_value)
            print("Successfully added to PATH. You may need to restart your session for changes to take effect.")
        else:
            print("The path is already in the user PATH.")
    except Exception as e:
        print("Failed to update PATH:", e)
    finally:
        env_key.Close()

def main():
    # URL for FFmpeg static build (Essentials build)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # Download the ZIP to a temporary location
    tmp_dir = tempfile.gettempdir()
    zip_path = os.path.join(tmp_dir, "ffmpeg.zip")
    download_ffmpeg(ffmpeg_url, zip_path)
    
    # Define the directory where FFmpeg will be installed
    install_dir = r"C:\ffmpeg"
    if not os.path.exists(install_dir):
        os.makedirs(install_dir)
    
    # Extract the downloaded ZIP to the install directory
    extract_zip(zip_path, install_dir)
    
    # The archive typically extracts to a folder named something like "ffmpeg-2025-02-15-git-xxxxxx"
    # We need to locate the folder that contains the "bin" directory.
    extracted_folders = [f for f in os.listdir(install_dir) if os.path.isdir(os.path.join(install_dir, f))]
    if not extracted_folders:
        print("No folders were extracted. Exiting.")
        return
    
    ffmpeg_folder = os.path.join(install_dir, extracted_folders[0])
    bin_path = os.path.join(ffmpeg_folder, "bin")
    
    if os.path.exists(bin_path):
        add_to_user_path(bin_path)
    else:
        print("Could not locate the 'bin' directory in the extracted files.")
    
    # Clean up downloaded ZIP file (optional)
    try:
        os.remove(zip_path)
        print("Cleaned up temporary files.")
    except Exception as e:
        print("Could not remove temporary files:", e)

if __name__ == "__main__":
    main()
