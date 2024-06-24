
from OCR_IG import *
from OCR_TK import *
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

def main(folder_path, csv_path):
    
    results = []

    # Get all video files in the folder
    video_files = sorted(
        [f for f in os.listdir(folder_path) if f.endswith('.mp4')],
        key=extract_part_number
    )

    for video_file in video_files:
        video_path = os.path.join(folder_path, video_file)
        
        platform, video_type = extract_video_info(video_path)
        print(platform, video_type )
        if platform == "TikTok":
            result = tikTok_wrapper(video_path)
        elif platform == "Instagram":
            if video_type == "Reel" or video_type == "Unknown":
                result = instagram_wrapper(video_path)
            elif video_type == "Video":
                result = [video_path, None, None, None]
            else:
                continue  # Skip files that are not reels or videos
        else:
            continue  # Skip files that are neither TikTok nor Instagram
        
        results.append(result)

    # Create a DataFrame from the results
    df = pd.DataFrame(results, columns=['Path', 'Union_Names', 'More_Than_One_Username', 'common_account_names'])
    df.to_csv(csv_path, index=False)

    # Create a DataFrame from the results
    df = pd.DataFrame(results, columns=['Path', 'Union_Names', 'More_Than_One_Username', 'common_account_names'])
    df.to_csv(csv_path, index=False)


def main_array(folders_list_path,country):

    with open(folders_list_path, 'r') as f:
        folders = json.load(f)
    task_id = int(os.getenv('SLURM_ARRAY_TASK_ID')) - 1

    if task_id < len(folders):
        folder_path = folders[task_id]
        
        results = []

        # Get all video files in the folder
        video_files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith('.mp4')],
            key=extract_part_number
        )

        for video_file in video_files:
            video_path = os.path.join(folder_path, video_file)
            
            platform, video_type = extract_video_info(video_path)
            print(platform, video_type)
            if platform == "TikTok":
                result = tikTok_wrapper(video_path)
            elif platform == "Instagram":
                if video_type == "Reel" or video_type == "Unknown":
                    result = instagram_wrapper(video_path)
                elif video_type == "Video":
                    result = [video_path, None, None, None]
                else:
                    continue  # Skip files that are not reels or videos
            else:
                continue  # Skip files that are neither TikTok nor Instagram
            
            results.append(result)

        # Create a folder with the name of the current folder and save the CSV file inside it
        output_folder = os.path.join('/projappl/project_2009497/OCR/Account Names Csv/', country)
        os.makedirs(output_folder, exist_ok=True)
        
        csv_path = os.path.join(output_folder, f'{os.path.basename(folder_path)}_{task_id}.csv')
        # Create a DataFrame from the results
        df = pd.DataFrame(results, columns=['Path', 'Union_Names', 'More_Than_One_Username', 'common_account_names'])
        df.to_csv(csv_path, index=False)
    else:
        print(f"Task ID {task_id + 1} is out of range for the list of files.")


    

# # Run the video processing
# folder_path = r"/scratch/project_2009497/MobileBackup/Croatia/HR1/Organic/Instagram/az_recorder_20240523_145452"
# main('/scratch/project_2009497/MobileBackup/Bulgaria/BG3/Synthetic/Tiktok/Tiksynthetic10062024','test.csv')
main_array('Hungary.txt','Hungary')