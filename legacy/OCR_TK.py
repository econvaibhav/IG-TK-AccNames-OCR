import os
import warnings
import easyocr
import cv2
import torch
import re
import regex
import pandas as pd
from difflib import SequenceMatcher
# Set up environment and warnings
os.environ['PYTHONWARNINGS'] = 'ignore::FutureWarning'
warnings.filterwarnings("ignore", category=FutureWarning)

reader = easyocr.Reader(['en', 'hu'])

def is_valid_tiktok_username(username):
    """Check if the TikTok username is valid."""
    if len(username) < 2 or len(username) > 24:
        return False
    if re.search(r'[@?#$%^&*(),"{}|<>`=\[\]\\;\'/]', username):
        return False
    if username.endswith('.'):
        return False
    if username.startswith(('See', 'translation')):
        return False
    if re.search(r'\s{3,}', username):  # Three or more consecutive spaces
        return False
    return True

def filter_short_words_from_list(text_list):
    """Remove the first and last word if they are smaller than 2 characters."""
    def filter_short_words(text):
        words = text.split()
        if len(words) > 0 and len(words[0]) < 3:
            words.pop(0)
        if len(words) > 0 and len(words[-1]) < 2:
            words.pop()
        return ' '.join(words)
    
    return [filter_short_words(text) for text in text_list]

def filter_non_usernames(usernames):
    """Filter out invalid TikTok usernames."""
    return [username for username in usernames if is_valid_tiktok_username(username)]

def is_number(text):
    """Check if the text is a number."""
    try:
        float(text.replace(',', ''))
        return True
    except ValueError:
        return False

def OCR(frame, roi=None):
    """Perform OCR on the given frame."""
    if roi:
        x, y, w, h = roi
        frame = frame[y:y+h, x:x+w]
    result = reader.readtext(frame, paragraph=True, x_ths=1.0, y_ths=0.1, text_threshold=0.8)
    return [item[1] for item in result if not is_number(item[1])]

def OCR_count(OCR_results, dic, min_diff=3):
    """Count the occurrences of each OCR result and return the top k most repeated account names based on count difference."""
    for result in OCR_results:

        dic[result] = dic.get(result, 0) + 1
        for key in dic.keys():
            if key not in OCR_results and (result in key or key in result):
                dic[key]+=1


    
    # Sort the dictionary by values in descending order
    sorted_results = sorted(dic.items(), key=lambda item: item[1], reverse=True)
    # print(sorted_results)
    # Determine the top k items based on the difference between counts
    top_k_results = []
    for i in range(len(sorted_results)):
        if i == 0 or (sorted_results[i-1][1] - sorted_results[i][1] <= min_diff):
            top_k_results.append(sorted_results[i])
        else:
            break

    # Extract the top k account names and their counts
    top_k_account_names = [item[0] for item in top_k_results]
    top_k_counts = [item[1] for item in top_k_results]

    return dic, top_k_counts, top_k_account_names

def OCR_pipeline(dic, frame):
    """Process a frame through the OCR pipeline."""
    y_start, y_end = 650, 880
    height, width, _ = frame.shape
    roi = (0, y_start, width // 2, y_end - y_start)

    OCR_results = OCR(frame, roi)
    usernames = filter_short_words_from_list(OCR_results)
    usernames = filter_non_usernames(usernames)
    
    dic, top_k_counts, top_k_account_names = OCR_count(usernames, dic)

    return top_k_counts, top_k_account_names, usernames

def process_video(video_path, checks_per_sec=3,number_of_sec=3):
    """Process the video and extract the most frequent username."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    skip_frames = int(fps / checks_per_sec)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    new_height = 960
    aspect_ratio = width / height
    new_width = int(new_height * aspect_ratio)

    frame_count = 0
    dic = {}
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break 

        
        if frame_count % skip_frames == 0:
            frame = cv2.resize(frame, (new_width, new_height))
            top_k_counts, top_k_account_names, usernames= OCR_pipeline(dic, frame)

            if top_k_counts and top_k_counts[0] > number_of_sec*checks_per_sec:
                dic = {}

                return top_k_account_names
            # print(f"Frame {frame_count}: {top_k_account_names}, {usernames}")
            # y_start, y_end = 650, 880
            # height, width, _ = frame.shape
            # roi = (0, y_start, width // 2, y_end - y_start)
            # x, y, w, h = roi
            # cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # # Save the frame with the ROI box
            # output_path = f"output_frame_{frame_count}.jpg"
            # cv2.imwrite(output_path, frame)
        
        frame_count += 1
    
    cap.release()
    return top_k_account_names

def process_video_reverse(video_path, checks_per_sec=3,number_of_sec=3):
    """Process the video in reverse and extract the most frequent username."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    skip_frames = int(fps / checks_per_sec)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    new_height = 960
    aspect_ratio = width / height
    new_width = int(new_height * aspect_ratio)

    dic = {}
    
    for frame_number in range(total_frames - 1, -1, -skip_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.resize(frame, (new_width, new_height))
        top_k_counts, top_k_account_names, usernames = OCR_pipeline(dic, frame)

        if top_k_counts and top_k_counts[0] > number_of_sec*checks_per_sec:
            dic = {}
            
            return top_k_account_names
        # print(f"Frame {frame_number}: {top_k_account_names}, {usernames}")
    
    cap.release()
    return top_k_account_names
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def find_similar_names(list1, list2, threshold=0.8):
    similar_names = []
    for name1 in list1:
        for name2 in list2:
            similarity = similar(name1, name2)
            if threshold <= similarity :
                similar_names.append((name1, name2, similarity))
    return similar_names

def extract_part_number(filename):
    match = re.search(r'part_(\d+)', filename)
    return int(match.group(1)) if match else float('inf')

def tikTok_wrapper(video_path):
    print(f"Processing {video_path}")
    top_k_account_names_forward = process_video(video_path, checks_per_sec=20, number_of_sec=0.5)
    print(f'Final Forward result is {top_k_account_names_forward}')
    top_k_account_names_reverse = process_video_reverse(video_path, checks_per_sec=20, number_of_sec=0.5)
    print(f'Final Reverse result is {top_k_account_names_reverse}')
    
    common_account_names = None
    more_than_one_username = 0
    if top_k_account_names_forward is None:
        union_names = top_k_account_names_reverse
    elif top_k_account_names_reverse is None:
        union_names = top_k_account_names_forward
    else:
        union_names = list(dict.fromkeys(top_k_account_names_forward + top_k_account_names_reverse))
        
        common_account_names = find_similar_names(top_k_account_names_forward, top_k_account_names_reverse, threshold=0.6)
        print(common_account_names)
        more_than_one_username = 0 if len(common_account_names) > 0 else 1
    
    return [video_path, union_names, more_than_one_username, common_account_names]

def main(folder_path, csv_path):
    results = []

    # Get all video files in the folder
    video_files = sorted(
        [f for f in os.listdir(folder_path) if f.endswith('.mp4')],
        key=extract_part_number
    )

    for video_file in video_files:
        video_path = os.path.join(folder_path, video_file)
        result = tikTok_wrapper(video_path)
        results.append(result)

    # Create a DataFrame from the results
    df = pd.DataFrame(results, columns=['Path', 'Union_Names', 'More_Than_One_Username', 'common_account_names'])
    df.to_csv(csv_path, index=False)
# Initialize EasyOCR reader with recognizer only
# reader = easyocr.Reader(['en', 'bg'], gpu=torch.cuda.is_available())
# main('/scratch/project_2009497/MobileBackup/Bulgaria/BG3/Synthetic/Tiktok/Tiksynthetic10062024','test.csv')