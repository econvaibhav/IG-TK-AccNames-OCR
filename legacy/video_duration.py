import os
from moviepy import *

def get_total_video_duration(directory):
    total_duration = 0  # in seconds
    for root, _, files in os.walk(directory):
        for file in files:
            # Check if the file is a video based on common extensions
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                video_path = os.path.join(root, file)
                try:
                    with VideoFileClip(video_path) as clip:
                        total_duration += clip.duration  # duration in seconds
                except Exception as e:
                    print(f"Error processing file {video_path}: {e}")
    
    return total_duration

if __name__ == "__main__":
    # Set your local Teams-synced folder path here
    directory = r"C:\Users\User\University of Helsinki\EP Election 2024 - AV Data Gathering - ES1 - ES1"
    total_duration = get_total_video_duration(directory)
    
    # Convert seconds to hours, minutes, and seconds
    hours, remainder = divmod(total_duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    print(f"Total video duration: {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds")
