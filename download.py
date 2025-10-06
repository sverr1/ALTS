import argparse
import subprocess
import re
import os
from datetime import datetime

def get_expected_filename(url):
    """
    Get the expected filename from yt-dlp without downloading.
    Returns the filename that would be used for download.
    """
    command = f"yt-dlp --cookies cookies.txt --get-filename {url}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        filename = result.stdout.strip()
        return filename
    return None

def parse_filename_to_mp3(filename):
    """
    Parse Panopto filename and convert to expected MP3 format.
    Example: "FYS102-1 25H Lecture..." -> "FYS102_2025-10-03.mp3"
    """
    # Extract emnekode from the filename
    emnekode = filename.split(" ")[0]

    # Extract date from the filename
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", filename)
    if match:
        day, month, year = match.groups()
        dato = f"{year}-{month}-{day}"
    else:
        dato = datetime.now().strftime("%Y-%m-%d")

    return f"{emnekode}_{dato}.mp3"

def get_video_id(url):
    """
    Gets all available video formats and resolutions from the provided url, and returns the ID of the best available quality.
    """
    # Get all available video formats and resolutions
    command = f"yt-dlp --cookies cookies.txt -F {url}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # Find the line with the desired resolution and format
    for line in result.stdout.split("\n"):
        if "960x540" in line and "mp4a.40.2" in line:
            # Extract the ID from the line
            match = re.search(r"hls-(\d{3,4})", line)
            if match:
                return match.group(0)
    return None

def download_video(url, video_id):
    """
    Downloads the video with the given ID to the 'downloads' directory.
    """
    # The -P flag directs all output, including temporary files, to the specified directory.
    command = f"yt-dlp --cookies cookies.txt -f {video_id} -P downloads {url}"
    print(f"Running command: {command}")
    subprocess.run(command, shell=True)

def convert_to_audio(video_path):
    """
    Converts video file to compressed MP3 audio to save space.
    Deletes the original video file after successful conversion.
    """
    audio_path = video_path.replace('.mp4', '.mp3')

    print(f"Converting to MP3: {os.path.basename(video_path)}")
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-q:a", "2",  # High quality VBR (~190 kbps)
        "-y",  # Overwrite if exists
        audio_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Audio saved: {os.path.basename(audio_path)}")
        # Delete original video to save space
        os.remove(video_path)
        print(f"Original video deleted: {os.path.basename(video_path)}")
        return audio_path
    else:
        print(f"Error converting to audio:")
        print(result.stderr)
        return None

def rename_file(filename, download_path="downloads"):
    """
    Renames the file to the format <emnekode>_<dato>.<ext> in the download directory.
    Removes lecture numbers (e.g., FYS102-1 → FYS102)
    """
    # Extract emnekode from the filename (first part before space)
    emnekode_raw = filename.split(" ")[0]

    # Remove lecture number suffix (e.g., "FYS102-1" → "FYS102")
    # Match pattern: BOKSTAVER + TALL, ignorer alt etter (som -1, -2, etc.)
    emnekode_match = re.match(r'^([A-Z]+\d+)', emnekode_raw)
    if emnekode_match:
        emnekode = emnekode_match.group(1)
    else:
        emnekode = emnekode_raw  # Fallback

    # Extract date from the filename
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", filename)
    if match:
        day, month, year = match.groups()
        dato = f"{year}-{month}-{day}"
    else:
        dato = datetime.now().strftime("%Y-%m-%d")

    # Get file extension
    ext = os.path.splitext(filename)[1]

    old_filepath = os.path.join(download_path, filename)
    new_filename = f"{emnekode}_{dato}{ext}"
    new_filepath = os.path.join(download_path, new_filename)

    # Check if the old file exists before trying to rename
    if os.path.exists(old_filepath):
        print(f"Renaming: {os.path.basename(old_filepath)}")
        print(f"      → : {new_filename}")
        os.rename(old_filepath, new_filepath)
        return new_filename
    else:
        print(f"Error: File to rename not found at '{old_filepath}'")
        return None


def main():
    parser = argparse.ArgumentParser(description="Download a video from a given URL to the 'downloads' folder.")
    parser.add_argument("url", nargs="?", help="The URL of the video to download.")
    args = parser.parse_args()

    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)

    if args.url:
        url = args.url
    else:
        url = input("Enter the URL of the video to download: ")

    # Check if file already exists
    print("Checking if file already exists...")
    expected_filename = get_expected_filename(url)

    if expected_filename:
        expected_mp3 = parse_filename_to_mp3(expected_filename)
        mp3_path = os.path.join(download_dir, expected_mp3)

        if os.path.exists(mp3_path):
            print(f"✓ File already exists: {expected_mp3}")
            print(f"  Skipping download.")
            return
        else:
            print(f"  File not found, will download: {expected_mp3}")

    video_id = get_video_id(url)

    if video_id:
        print(f"Found video with ID: {video_id}")
        download_video(url, video_id)
        
        # Find the most recently modified .mp4 file in the downloads directory.
        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if f.endswith('.mp4')]
        if not files:
            print("Error: No .mp4 file found in downloads directory after download.")
            return
            
        latest_file = max(files, key=os.path.getctime)
        original_filename = os.path.basename(latest_file)

        print(f"Downloaded file identified as: {original_filename}")

        # Rename video file
        if not re.match(r"^\w+_\d{4}-\d{2}-\d{2}\.mp4$", original_filename):
            new_filename = rename_file(original_filename, download_path=download_dir)
            if not new_filename:
                print("Could not rename the video file.")
                return
        else:
            new_filename = original_filename
            print("File already correctly named.")

        # Convert to MP3 audio to save space
        video_path = os.path.join(download_dir, new_filename)
        audio_path = convert_to_audio(video_path)

        if audio_path:
            print(f"\n✓ Download complete: {os.path.basename(audio_path)}")
        else:
            print(f"\n✓ Download complete (video retained): {new_filename}")

    else:
        print("Could not find a suitable video format.")

if __name__ == "__main__":
    main()
