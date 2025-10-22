#test input

import pandas as pd

# Load the Excel file
file_path = "songs_input.xlsx"
songs_df = pd.read_excel(file_path)

print(songs_df.columns)


# Filter rows where track_id == 7
track_7 = songs_df[songs_df["track_id"] == 7]

# Show the result
print(track_7)


