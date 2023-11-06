import sqlite3
import os

# Get a list of all files in the current directory
files = os.listdir('.')

# Look for the file that starts with 'vimusic_' and ends with '.db'
for file in files:
    if file.startswith('vimusic_') and file.endswith('.db'):
        db_file = file
        break
else:
    raise FileNotFoundError("No database file found starting with 'vimusic_' and ending with '.db'")

# Establish a connection to the SQLite database
conn = sqlite3.connect(db_file)

# Create a cursor object using the cursor() method
cursor = conn.cursor()

# SQL query to fetch the required data
query = """
SELECT p.name AS playlist_name, s.title AS song_title, a.name AS artist_name, spm.position
FROM Playlist p
JOIN SongPlaylistMap spm ON p.id = spm.playlistId
JOIN Song s ON s.id = spm.songId
LEFT JOIN SongArtistMap sam ON s.id = sam.songId
LEFT JOIN Artist a ON sam.artistId = a.id
ORDER BY p.name, spm.position
"""

# Execute the SQL query
cursor.execute(query)

# Fetch all results
results = cursor.fetchall()

# Dictionary to hold playlist songs and artist names
playlist_songs = {}

# Process the results
for playlist_name, song_title, artist_name, position in results:
    # Initialize the playlist in the dictionary if it does not exist
    if playlist_name not in playlist_songs:
        playlist_songs[playlist_name] = {}

    # Initialize the song in the playlist if it does not exist
    if song_title not in playlist_songs[playlist_name]:
        playlist_songs[playlist_name][song_title] = {
            'artists': set(),  # Use a set to avoid duplicates
            'position': position
        }

    # Add the artist name to the set of artists for this song
    if artist_name:
        playlist_songs[playlist_name][song_title]['artists'].add(artist_name)

# Folder to save playlist files
output_folder = "playlists"
os.makedirs(output_folder, exist_ok=True)

# Write to text files within the "playlists" folder
for playlist_name, songs in playlist_songs.items():
    # Replace any characters that are invalid in file names
    valid_file_name = "".join(x for x in playlist_name if x.isalnum() or x in " -_").rstrip()
    # Path for the file
    file_path = os.path.join(output_folder, f"{valid_file_name}.txt")

    # Sort songs by the position before writing to the file
    sorted_songs = sorted(songs.items(), key=lambda x: x[1]['position'])

    # Create a file for each playlist
    with open(file_path, 'w', encoding='utf-8') as file:
        # Write each song entry to the file
        for song_title, details in sorted_songs:
            artist_names = ', '.join(details['artists'])
            song_entry = f"{artist_names} - {song_title}" if artist_names else song_title
            file.write(song_entry + '\n')

# Close the cursor and connection
cursor.close()
conn.close()