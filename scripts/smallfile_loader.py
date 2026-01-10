# file_loader.py
import pandas as pd

def load_sequencing_file(filepath):
    """
    Reads a result file (Excel) and extracts relevant columns.
    Assumes standard columns exist in the file.
    """
    try:
        # TODO: Update this to handle CSV files if the lab changes formats
        df = pd.read_excel(filepath)
        
        # Select only the columns we need for our database
        # These column names are hypothetical; adjust based on actual file header
        clean_data = df[[
            'SampleID', 
            'UniqReads', 
            'GC_Ratio', 
            'FetalFraction', 
            'Z_Score_21', 
            'Z_Score_18', 
            'Z_Score_13'
        ]]
        
        # Convert to a list of dictionaries for easy processing
        return clean_data.to_dict('records')
        
    except Exception as e:
        print(f"Error loading file: {e}")
        return None
