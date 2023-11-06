import sqlite3
import os

# Establish a connection to the SQLite database
conn = sqlite3.connect('vimusic.db')

# Create a cursor object using the cursor() method
cursor = conn.cursor()

# SQL query to fetch the required data
query = """
SELECT p.name AS playlist_name, s.title AS song_title, a.name AS artist_name
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

# Dictionary to hold playlist songs
playlist_songs = {}

# Process the results
for playlist_name, song_title, artist_name in results:
    # Format the song entry as "Artist - Song Title" if artist name is present
    song_entry = f"{artist_name} - {song_title}" if artist_name else song_title
    # Append the song entry to the corresponding playlist in the dictionary
    playlist_songs.setdefault(playlist_name, []).append(song_entry)

# Folder to save playlist files
output_folder = "playlists"
os.makedirs(output_folder, exist_ok=True)

# Write to text files within the "playlists" folder
for playlist_name, songs in playlist_songs.items():
    # Replace any characters that are invalid in file names
    valid_file_name = "".join(x for x in playlist_name if x.isalnum() or x in " -_").rstrip()
    # Path for the file
    file_path = os.path.join(output_folder, f"{valid_file_name}.txt")
    # Create a file for each playlist
    with open(file_path, 'w', encoding='utf-8') as file:
        # Write each song entry to the file
        for song_entry in songs:
            file.write(song_entry + '\n')

# Close the cursor and connection
cursor.close()
conn.close()