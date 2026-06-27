import pandas as pd
import glob
import os

# 1. Define the folder where your 8 Excel files are located
# Use './' if they are in the same folder as this script
path = './men/men_April7_10AM/' 
all_files = glob.glob(os.path.join(path, "*.csv"))

# 2. Load and combine all files into one list
df_list = []

for filename in all_files:
    print(f"Reading {filename}...")
    df = pd.read_csv(filename)
    
    base_name = os.path.basename(filename)
    clean_name = os.path.splitext(base_name)[0]
    print(clean_name)
    cleaner_name = clean_name.split("_")
    print("_".join(cleaner_name[-2:]))
    df['Source File'] = "_".join(cleaner_name[-2:])
    
    df_list.append(df)

# 3. Concatenate all dataframes into one large table
combined_df = pd.concat(df_list, ignore_index=True)

# 4. Remove duplicates based on the 'Product ID' column
# 'keep=first' ensures we keep the first instance found
initial_count = len(combined_df)
combined_df.drop_duplicates(subset=['Product_ID'], keep='first', inplace=True)
final_count = len(combined_df)

# 5. Export the clean, master file
output_file = "Zara_Master_Dataset_Men_April7_10AM_2026.csv"
combined_df.to_csv(output_file, index=False)

print("-" * 30)
print(f"✅ Process Complete!")
print(f"Total rows combined: {initial_count}")
print(f"Duplicates removed: {initial_count - final_count}")
print(f"Final unique products: {final_count}")
print(f"Master file saved as: {output_file}")
