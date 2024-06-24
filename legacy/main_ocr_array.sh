#!/bin/bash
#SBATCH --account=project_2009497  # Your project ID
#SBATCH --output=/dev/null  # Discard individual output files
#SBATCH --error=/dev/null  # Discard individual error files
#SBATCH --time=24:00:00  # Adjust time as needed
#SBATCH --mem-per-cpu=10G  # Memory per CPU in MB
#SBATCH --array=1-344 # Array indices
#SBATCH --ntasks=1
#SBATCH --partition=small  # Use the small partition

# Define a common output file
COMMON_OUTPUT_FILE="/users/zakiandr/combined_output.out"

#echo "Starting job script for task ID: $SLURM_ARRAY_TASK_ID" >> $COMMON_OUTPUT_FILE  # Debugging statement

# Activate the virtual environment
source /projappl/project_2009497/.venv/bin/activate

export PATH=$HOME/ffmpeg-7.0.2-amd64-static:$PATH

#echo "Virtual environment activated for task ID: $SLURM_ARRAY_TASK_ID" >> $COMMON_OUTPUT_FILE  # Debugging statement

# Run the Python script and append output to the common file
cd /projappl/project_2009497/OCR
srun python main_array.py >> $COMMON_OUTPUT_FILE 2>&1


#echo "Python script executed for task ID: $SLURM_ARRAY_TASK_ID" >> $COMMON_OUTPUT_FILE  # Debugging statement
