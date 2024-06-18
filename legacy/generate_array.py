import os
import json

def extract_video_info(video_path):
    # Split the path into parts
    parts = video_path.split(os.sep)
    
    # Determine the platform
    # print(parts)
    if "Tiktok" in parts:
        platform = "TikTok"
    elif "Instagram" in parts:
        platform = "Instagram"
    else:
        platform = "Unknown"

    # Determine the type (reel or video)
    file_name = parts[-1].lower()
    if "reel" in file_name:
        video_type = "Reel"
    elif "video" in file_name:
        video_type = "Video"
    else:
        video_type = "Unknown"
    
    return platform, video_type

def generate_folder_array(folder_path, output_file):
    folder_array = []

    # Walk through the directory tree
    for root, dirs, files in os.walk(folder_path):
        # Check if the folder has no internal folders but has mp4 videos
        if not dirs and any(file.endswith('.mp4') for file in files):
            platform, _ = extract_video_info(root)
            if platform in ["Instagram", "TikTok"]:

                folder_array.append(root)

    print(len(folder_array))
    with open(output_file, 'w') as f:
        json.dump(folder_array, f)

# conutry_code_dic ={
# 'Bulgaria':'BG',
# # 'Croatia':'HR',
# # 'Finland':'FI',
# # 'France':'FR',
# # 'Germany':'DE',
# # 'Hungary':'HU',
# # 'Poland':'PL',
# # 'Portugal':'PT',
# # 'Spain':'ES',
# # 'Sweden':'SE'
# }

generate_folder_array('/scratch/project_2009497/MobileBackup/Hungary', 'Hungary.txt')