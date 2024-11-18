# .src/main.py
#!/usr/bin/env python3.10
import os
import subprocess
import sys
import argparse
import logging
import re
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Configure logging
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "error.log")
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Directories
DOWNLOAD_DIR = "Downloaded Videos"
SUBTITLE_DIR = "Subtitles"
SUBTITLED_VIDEO_DIR = "Subtitled Videos"
CLEAN_TEXT_DIR = "Clean Text"
AUDIO_DIR = "Audio Files"

# Create directories if they don't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(SUBTITLE_DIR, exist_ok=True)
os.makedirs(SUBTITLED_VIDEO_DIR, exist_ok=True)
os.makedirs(CLEAN_TEXT_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# File to keep track of processed URLs
URL_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "url_history.txt")

def load_url_history():
    url_history = {}
    if os.path.exists(URL_HISTORY_FILE):
        with open(URL_HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split('||')
                    if len(parts) == 2:
                        url, video_name = parts
                        url_history[url] = video_name
    return url_history

def save_url_history(url_history):
    with open(URL_HISTORY_FILE, 'w', encoding='utf-8') as f:
        for url, video_name in url_history.items():
            f.write(f"{url}||{video_name}\n")

def clean_srt_file(srt_path, txt_path):
    try:
        with open(srt_path, 'r', encoding='utf-8') as srt_file, open(txt_path, 'w', encoding='utf-8') as txt_file:
            for line in srt_file:
                line = line.strip()
                if not line:
                    continue
                if line.isdigit():
                    continue
                if '-->' in line:
                    continue
                txt_file.write(line + '\n')
    except Exception as e:
        logging.error(f"Failed to clean subtitle file {srt_path}. Error: {e}")
        print(f"{Fore.RED}Oops! Failed to clean subtitle file. Please check {LOG_FILE} for more details.")
        return False
    return True

def get_video_duration(video_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        logging.error(f"Failed to get video duration for {video_path}. Error: {e}")
        print(f"{Fore.RED}Could not retrieve video duration. Please check {LOG_FILE} for more details.")
        return None

def run_command_with_progress(command, duration=None, description="", is_ffmpeg=False, capture_output=False):
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        output_stream = process.stderr if is_ffmpeg else process.stdout

        pattern = re.compile(r'time=(\d+:\d+:\d+\.\d+)')
        total_seconds = duration if duration else 0
        last_percentage = -1
        captured_output = []

        while True:
            line = output_stream.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                if capture_output:
                    captured_output.append(line)
                if is_ffmpeg and 'time=' in line:
                    match = pattern.search(line)
                    if match:
                        time_str = match.group(1)
                        h, m, s = time_str.split(':')
                        elapsed_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        if total_seconds > 0:
                            percentage = int((elapsed_seconds / total_seconds) * 100)
                            if percentage != last_percentage:
                                print(f'\r{description} {Fore.GREEN}[{percentage}%]', end='', flush=True)
                                last_percentage = percentage
                elif not is_ffmpeg and '%' in line:
                    match = re.search(r'(\d+)%', line)
                    if match:
                        percentage = int(match.group(1))
                        if percentage != last_percentage:
                            print(f'\r{description} {Fore.GREEN}[{percentage}%]', end='', flush=True)
                            last_percentage = percentage
        process.wait()
        print()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
        if capture_output:
            return True, captured_output
        return True, []
    except subprocess.CalledProcessError as e:
        logging.error(f"Command '{' '.join(command)}' failed with return code {e.returncode}.")
        print(f"{Fore.RED}Operation failed. Please check {LOG_FILE} for more details.")
        return False, []
    except Exception as e:
        logging.error(f"An unexpected error occurred while running command '{' '.join(command)}'. Error: {e}")
        print(f"{Fore.RED}An unexpected error occurred. Please check {LOG_FILE} for more details.")
        return False, []

def process_video(url, video_name):
    output_video = os.path.join(DOWNLOAD_DIR, f"{video_name}.mp4")
    subtitle_file = os.path.join(SUBTITLE_DIR, f"{video_name}.srt")
    clean_txt_file = os.path.join(CLEAN_TEXT_DIR, f"{video_name}.txt")
    subtitled_video = os.path.join(SUBTITLED_VIDEO_DIR, f"{video_name}.mp4")
    audio_file = os.path.join(AUDIO_DIR, f"{video_name}.mp3")

    # Download video
    if not os.path.exists(output_video):
        print(f"{Fore.CYAN}Starting the epic download of your video... Hang tight!")
        ffmpeg_command = [
            'ffmpeg',
            '-i', url,
            '-c', 'copy',
            '-y',
            output_video
        ]
        success, _ = run_command_with_progress(ffmpeg_command, description="Downloading video:", is_ffmpeg=True)
        if not success:
            logging.error(f"Failed to download video from {url}.")
            print(f"{Fore.RED}Uh-oh! Failed to download video from {url}. Please check {LOG_FILE} for more details.")
            return False
        print(f"{Fore.GREEN}Video downloaded successfully! 🎉")
    else:
        print(f"{Fore.YELLOW}Hold on! The video already exists. Skipping download.")

    # Get video duration
    duration = get_video_duration(output_video)
    if not duration:
        return False

    # Generate subtitles
    if not os.path.exists(subtitle_file):
        print(f"{Fore.CYAN}Generating subtitles... This might take a moment or two.")
        auto_subtitle_command = [
            'auto_subtitle',
            output_video,
            '--output_dir', SUBTITLE_DIR,
            '--task', 'transcribe',
            '--output_srt', 'True',
            '--srt_only', 'True'
        ]
        success, output = run_command_with_progress(
            auto_subtitle_command,
            duration=duration,
            description="Generating subtitles:",
            capture_output=True
        )
        if not success:
            logging.error(f"Failed to generate subtitles for {output_video}.")
            print(f"{Fore.RED}Oops! Failed to generate subtitles for {output_video}. Please check {LOG_FILE} for more details.")
            return False

        # Parse the detected language from the output
        detected_language = None
        for line in output:
            if "Detected language:" in line:
                detected_language = line.split("Detected language:")[-1].strip()
                break

        if detected_language:
            print(f"{Fore.BLUE}Detected language: {Fore.GREEN}{detected_language}{Style.RESET_ALL}")
            if detected_language.lower() != "english":
                proceed = input(f"{Fore.YELLOW}The detected language is '{detected_language}'. Would you like to enable translation to English? (Y/n): ").strip().lower()
                if proceed in ['y', 'yes', '']:
                    print(f"{Fore.CYAN}Enabling translation to English...")
                    # Rerun the auto_subtitle command with translate task
                    auto_subtitle_translate_command = [
                        'auto_subtitle',
                        output_video,
                        '--output_dir', SUBTITLE_DIR,
                        '--task', 'translate',
                        '--output_srt', 'True',
                        '--srt_only', 'True'
                    ]
                    success_translate, translate_output = run_command_with_progress(
                        auto_subtitle_translate_command,
                        duration=duration,
                        description="Generating translated subtitles:",
                        capture_output=True
                    )
                    if not success_translate:
                        logging.error(f"Failed to generate translated subtitles for {output_video}.")
                        print(f"{Fore.RED}Failed to generate translated subtitles for {output_video}. Please check {LOG_FILE} for more details.")
                        return False
                    print(f"{Fore.GREEN}Translated subtitles generated successfully! Now you can understand the content in English.")
                else:
                    print(f"{Fore.YELLOW}Skipping translation. Subtitles will be in the detected language.")
        else:
            print(f"{Fore.RED}Could not detect the language of the video. Proceeding without language-specific actions.")

        print(f"{Fore.GREEN}Subtitles generated! Now you can understand even the mumbles.")
    else:
        print(f"{Fore.YELLOW}Subtitles already exist. Skipping subtitle generation.")

    # Create subtitled video using ffmpeg
    if not os.path.exists(subtitled_video):
        print(f"{Fore.CYAN}Creating subtitled video... Almost there!")
        ffmpeg_subtitle_command = [
            'ffmpeg',
            '-i', output_video,
            '-vf', f"subtitles={subtitle_file}",
            '-c:a', 'copy',
            '-y',
            subtitled_video
        ]
        success = run_command_with_progress(ffmpeg_subtitle_command, duration=duration, description="Adding subtitles:", is_ffmpeg=True)
        if not success:
            logging.error(f"Failed to create subtitled video for {output_video}.")
            print(f"{Fore.RED}Drat! Failed to create subtitled video for {output_video}. Please check {LOG_FILE} for more details.")
            return False
        print(f"{Fore.GREEN}Subtitled video created successfully! Enjoy the show! 🍿")
    else:
        print(f"{Fore.YELLOW}Subtitled video already exists. Skipping creation.")

    # Extract audio
    if not os.path.exists(audio_file):
        print(f"{Fore.CYAN}Extracting audio from video... Music to your ears!")
        ffmpeg_audio_command = [
            'ffmpeg',
            '-i', output_video,
            '-vn',
            '-acodec', 'libmp3lame',
            '-y',
            audio_file
        ]
        success = run_command_with_progress(ffmpeg_audio_command, duration=duration, description="Extracting audio:", is_ffmpeg=True)
        if not success:
            logging.error(f"Failed to extract audio from {output_video}.")
            print(f"{Fore.RED}Yikes! Failed to extract audio from {output_video}. Please check {LOG_FILE} for more details.")
            return False
        print(f"{Fore.GREEN}Audio extracted successfully! 🎧")
    else:
        print(f"{Fore.YELLOW}Audio file already exists. Skipping extraction.")

    # Clean subtitles
    if not os.path.exists(clean_txt_file):
        print(f"{Fore.CYAN}Cleaning up the subtitles... Tidying is our middle name.")
        if not clean_srt_file(subtitle_file, clean_txt_file):
            return False
        print(f"{Fore.GREEN}Subtitles cleaned! Sparkling like new.")
    else:
        print(f"{Fore.YELLOW}Clean text file already exists. Skipping cleaning.")

    return True

def main():
    parser = argparse.ArgumentParser(description="Download video, generate subtitles, and clean subtitle text.")
    args = parser.parse_args()

    url_history = load_url_history()

    url = input(f"{Fore.BLUE}Enter the video URL: ").strip()
    if not url:
        print(f"{Fore.RED}No URL provided. Exiting. Maybe next time!")
        sys.exit(0)

    if url in url_history:
        video_name = url_history[url]
        print(f"{Fore.MAGENTA}Wait a minute! You've been here before with '{video_name}'.")
        print(f"{Fore.MAGENTA}Files are already available. No need to reinvent the wheel.")
        proceed = input(f"{Fore.BLUE}Do you want to process it again? (y/N): ").strip().lower()
        if proceed != 'y':
            print(f"{Fore.GREEN}Alrighty! Have a great day!")
            sys.exit(0)
    else:
        video_name = input(f"{Fore.BLUE}Enter the Name of Video: ").strip()
        if not video_name:
            print(f"{Fore.RED}No Name of Video provided. Exiting.")
            sys.exit(0)
        url_history[url] = video_name
        save_url_history(url_history)

    print(f"{Fore.CYAN}Hold tight! We're working some magic for '{video_name}'.")
    success = process_video(url, video_name)
    if success:
        print(f"{Fore.GREEN}All done! Enjoy your freshly processed video. 🍿")
    else:
        print(f"{Fore.RED}Processing failed. Please check {LOG_FILE} for details.")

if __name__ == '__main__':
    main()
