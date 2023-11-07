import sqlite3
import os

def safe_filename(name):
    return "".join(x for x in name if x.isalnum() or x in " -_").rstrip()

def clean_artist_name(artist_names):
    # Define artist names to be removed
    artists_to_remove = {'UKF Drum & Bass', 'The Myth of NYX', 'Dubstep uNk'}
    # Remove the artists and return the cleaned string
    return ', '.join([artist for artist in artist_names.split(', ') if artist not in artists_to_remove])

def process_and_write_data(query, file_path, is_favorites=False):
    cursor.execute(query)
    results = cursor.fetchall()

    # Creating the directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as file:
        for row in results:
            song_title, artist_names, album_title = row[:3]
            artist_names = clean_artist_name(artist_names) if artist_names else ''
            # Format line according to presence of artist and album
            if artist_names and album_title not in [None, 'None', ''] and album_title != song_title:
                line = f"{artist_names} - {song_title} + {album_title}\n"
            elif artist_names:
                line = f"{artist_names} - {song_title}\n"
            else:
                line = f"{song_title}\n"  # No artist name present
            file.write(line)

    print(f"Data written to {file_path}")

# Establish a connection to the SQLite database
db_file = next((f for f in os.listdir('.') if f.startswith('vimusic_') and f.endswith('.db')), None)
if db_file is None:
    raise FileNotFoundError("No database file found starting with 'vimusic_' and ending with '.db'")

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Favorites query
query_favorites = """
SELECT s.title AS song_title, GROUP_CONCAT(a.name, ', ') AS artist_names, 
       al.title AS album_title
FROM Song s
LEFT JOIN SongArtistMap sam ON s.id = sam.songId
LEFT JOIN Artist a ON sam.artistId = a.id
LEFT JOIN SongAlbumMap sal ON s.id = sal.songId
LEFT JOIN Album al ON sal.albumId = al.id
WHERE s.likedAt IS NOT NULL
GROUP BY s.id
ORDER BY s.likedAt DESC
"""

favorites_file_path = "playlists/Favorites from ViMusic.txt"
process_and_write_data(query_favorites, favorites_file_path, is_favorites=True)

# Playlists query
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

cursor.execute(query_playlists)
results_playlists = cursor.fetchall()

playlist_songs = {}
for playlist_name, song_title, artist_names, album_title, position in results_playlists:
    playlist_name_safe = safe_filename(playlist_name)
    if playlist_name_safe not in playlist_songs:
        playlist_songs[playlist_name_safe] = []

    artist_names = clean_artist_name(artist_names) if artist_names else ''
    if album_title not in [None, 'None', ''] and album_title != song_title:
        entry = f"{artist_names} - {song_title} + {album_title}" if artist_names else f"{song_title} + {album_title}"
    else:
        entry = f"{artist_names} - {song_title}" if artist_names else song_title
    
    playlist_songs[playlist_name_safe].append((position, entry))

for playlist_name_safe, songs in playlist_songs.items():
    playlist_file_path = f"playlists/{playlist_name_safe}.txt"
    with open(playlist_file_path, 'w', encoding='utf-8') as file:
        for position, entry in sorted(songs):
            file.write(entry + '\n')
    print(f"Data written to {playlist_file_path}")

cursor.close()
conn.close()