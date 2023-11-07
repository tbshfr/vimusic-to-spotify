import sqlite3
import os

def safe_filename(name):
    return "".join(x for x in name if x.isalnum() or x in " -_").rstrip()

# Establish a connection to the SQLite database
db_file = next((f for f in os.listdir('.') if f.startswith('vimusic_') and f.endswith('.db')), None)
if db_file is None:
    raise FileNotFoundError("No database file found starting with 'vimusic_' and ending with '.db'")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# SQL query to fetch the required data for favorites with grouped artists
query_favorites = """
SELECT s.title AS song_title, GROUP_CONCAT(a.name, ', ') AS artist_names, 
       al.title AS album_title, s.likedAt
FROM Song s
LEFT JOIN SongArtistMap sam ON s.id = sam.songId
LEFT JOIN Artist a ON sam.artistId = a.id
LEFT JOIN SongAlbumMap sal ON s.id = sal.songId
LEFT JOIN Album al ON sal.albumId = al.id
WHERE s.likedAt IS NOT NULL
GROUP BY s.id
ORDER BY s.likedAt DESC
"""

# SQL query to fetch the required data for playlists with grouped artists
query_playlists = """
SELECT p.name AS playlist_name, s.title AS song_title, GROUP_CONCAT(a.name, ', ') AS artist_names, 
       al.title AS album_title, spm.position
FROM Playlist p
JOIN SongPlaylistMap spm ON p.id = spm.playlistId
JOIN Song s ON s.id = spm.songId
LEFT JOIN SongArtistMap sam ON s.id = sam.songId
LEFT JOIN Artist a ON sam.artistId = a.id
LEFT JOIN SongAlbumMap sal ON s.id = sal.songId
LEFT JOIN Album al ON sal.albumId = al.id
GROUP BY p.name, s.id
ORDER BY p.name, spm.position
"""

# Execute and process favorites query
cursor.execute(query_favorites)
results_favorites = cursor.fetchall()

# Process and write favorites data
favorites_file_path = os.path.join("playlists", "Favs from ViMusic.txt")
os.makedirs("playlists", exist_ok=True)

with open(favorites_file_path, 'w', encoding='utf-8') as file:
    for song_title, artist_names, album_title, liked_at in results_favorites:
        if album_title not in [None, 'None', ''] and album_title != song_title:  # Exclude album if it has the same name as the song, is empty or has "None" as value
            file.write(f"{artist_names} - {song_title} + {album_title}\n")
        else:
            file.write(f"{artist_names} - {song_title}\n")

# Execute and process playlists query
cursor.execute(query_playlists)
results_playlists = cursor.fetchall()

# Process and write playlist data
playlist_songs = {}
for playlist_name, song_title, artist_names, album_title, position in results_playlists:
    playlist_name_safe = safe_filename(playlist_name)
    if playlist_name_safe not in playlist_songs:
        playlist_songs[playlist_name_safe] = []

    if album_title not in [None, 'None', ''] and album_title != song_title:  # Exclude album if it has the same name as the song, is empty or has "None" as value
        entry = f"{artist_names} - {song_title} + {album_title}"
    else:
        entry = f"{artist_names} - {song_title}"
    
    playlist_songs[playlist_name_safe].append((position, entry))

# Write to text files for each playlist
for playlist_name_safe, songs in playlist_songs.items():
    playlist_file_path = os.path.join("playlists", f"{playlist_name_safe}.txt")
    with open(playlist_file_path, 'w', encoding='utf-8') as file:
        for position, entry in sorted(songs):
            file.write(entry + '\n')

# Close the cursor and connection
cursor.close()
conn.close()
