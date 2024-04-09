import cv2
import numpy as np
import easyocr
import csv
import os

video_path = r"C:\Users\User\OneDrive - University of Helsinki\Desktop\Vaibhav_Studies\RA_work_HEPP\Instagram_OCR\part_11_reel.mp4"
output_csv_path = os.path.join(os.path.dirname(video_path), 'ocr_results.csv')

cap = cv2.VideoCapture(video_path)

display_width, display_height = 540, 960
roi_box_size = (69, 250)
roi_box_position = (10, display_height - 400)

reader = easyocr.Reader(['en', 'bg'])  # Initialize EasyOCR reader for English and Bulgarian

# Prepare to write results to CSV
with open(output_csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
    fieldnames = ['Input Path', 'Frame Number', 'OCR Text', 'Confidence']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()

    frame_number = 0  # Keep track of frame numbers

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        resized_frame = cv2.resize(frame, (display_width, display_height))
        roi_img = resized_frame[
            roi_box_position[1]:roi_box_position[1] + roi_box_size[1],
            roi_box_position[0]:roi_box_position[0] + roi_box_size[0]
        ]

        # Apply a blur to reduce noise without changing color
        blurred = cv2.GaussianBlur(roi_img, (9, 9), 2)

        # Split the image into its B, G, R channels
        channels = cv2.split(blurred)

        # Initialize a list to store circles detected in each channel
        circles_list = []

        for idx, channel in enumerate(channels):
            # Perform HoughCircles on each color channel
            circles = cv2.HoughCircles(
                channel,
                cv2.HOUGH_GRADIENT,
                dp=1.2,
                minDist=100,  # Adjusted to a larger value to detect only one circle
                param1=50,
                param2=35,  # Increased to make detection stricter
                minRadius=12,  # Set min and max radius close to expected circle size
                maxRadius=40
            )

            if circles is not None:
                circles = np.uint16(np.around(circles))
                circles_list.extend(circles[0, :])

        # If any circles are detected, process them
        if circles_list:
            # Assuming the circle you're interested in is the largest detected
            largest_circle = max(circles_list, key=lambda c: c[2])
            x, y, r = largest_circle
            # Adjust circle position relative to the entire frame
            center = (x + roi_box_position[0], y + roi_box_position[1])
            # Draw the outer circle
            cv2.circle(resized_frame, center, r, (0, 255, 0), 2)
            # Draw the center of the circle
            cv2.circle(resized_frame, center, 2, (0, 0, 255), 3)

            # Now, define the new ROI to the right of the circle
            new_roi_width, new_roi_height = 275, 40

            # Calculate the top-left corner of the new ROI
            new_roi_x = center[0] + r  # Start right after the circle
            new_roi_y = center[1] - new_roi_height // 2  # Centered vertically with the circle

            # Ensure the new ROI is within the image boundaries
            if new_roi_x + new_roi_width > resized_frame.shape[1]:
                new_roi_x = resized_frame.shape[1] - new_roi_width
            if new_roi_y < 0:
                new_roi_y = 0
            elif new_roi_y + new_roi_height > resized_frame.shape[0]:
                new_roi_y = resized_frame.shape[0] - new_roi_height

            new_roi_x = int(new_roi_x)
            new_roi_y = int(new_roi_y)

            # Extract the new ROI
            new_roi_img = resized_frame[new_roi_y:new_roi_y + new_roi_height, new_roi_x:new_roi_x + new_roi_width]

            # Run EasyOCR on the new ROI
            ocr_result = reader.readtext(new_roi_img)

            # If OCR results are found, process them
            for res in ocr_result:
                bbox, text, confidence = res
                # Write the result to CSV
                writer.writerow({
                    'Input Path': video_path,
                    'Frame Number': frame_number,
                    'OCR Text': text,
                    'Confidence': confidence
                })

            # Draw the new ROI rectangle
            cv2.rectangle(
                resized_frame,
                (new_roi_x, new_roi_y),
                (new_roi_x + new_roi_width, new_roi_y + new_roi_height),
                (255, 0, 0),
                2
            )

        # Draw the original ROI rectangle
        cv2.rectangle(
            resized_frame,
            roi_box_position,
            (roi_box_position[0] + roi_box_size[0], roi_box_position[1] + roi_box_size[1]),
            (0, 255, 0),
            2
        )

        cv2.imshow('Processed Video Frame', resized_frame)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

        frame_number += 1  # Increment frame number

cap.release()
cv2.destroyAllWindows()
