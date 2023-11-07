import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import subprocess
from difflib import SequenceMatcher

# Execute dump_playlist_to_txt.py to get songs from ViMusic
dump_result = subprocess.run(['python', 'dump_playlist_to_txt.py'], capture_output=True, text=True)

# Check if the subprocess was successful
if dump_result.returncode != 0:
    print(f"Error executing 'dump_playlist_to_txt.py': {result.stderr}")
    exit(1) 
else:
    print("Database dumped successfully to txt files.")

# Load environment variables
load_dotenv()

# Retrieve environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')
username = os.getenv('SPOTIFY_USERNAME')
playlist_public = os.getenv('PLAYLIST_PUBLIC') == 'True'
playlist_collaborative = os.getenv('PLAYLIST_COLLABORATIVE') == 'True'
match_percentage = os.getenv('MATCH_VALUE')

# Set up Spotipy with user credentials
token = SpotifyOAuth(client_id=client_id,
                     client_secret=client_secret,
                     redirect_uri=redirect_uri,
                     scope='playlist-modify-public playlist-modify-private')
spotify = spotipy.Spotify(auth_manager=token)

# Function to create a playlist
def create_playlist(name, public, collaborative, description=''):
    playlist = spotify.user_playlist_create(user=username, name=name, public=public,
                                            collaborative=collaborative, description=description)
    return playlist['id']

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def verify_track(query, track):
    query_parts = query.lower().split(" - ")
    query_words = set(query_parts[0].split())  # Always include artist and song
    track_words = set(f"{track['artists'][0]['name']} {track['name']}".lower().split())

    # Include the album in the comparison if it's present in the query
    if len(query_parts) > 2 and 'album' in track:
        query_album = query_parts[2]
        track_album = track['album']['name']
        query_words.update(query_album.split())
        track_words.update(track_album.lower().split())

    # Calculate the ratio of intersection between both sets
    match_ratio = len(query_words.intersection(track_words)) / len(query_words.union(track_words))

    return match_ratio

# Function to search for the Track names on Spotify, including the album if available
def search_track(artist_song_album_str):
    parts = artist_song_album_str.split(" - ")
    artist_song = parts[0] if len(parts) > 0 else ""
    album = parts[2] if len(parts) > 2 else ""

    query = artist_song
    if album:
        query += f" - {album}"  # Just append the album for the search query

    results = spotify.search(q=query, type='track', limit=10)
    for track in results['tracks']['items']:
        match_ratio = verify_track(artist_song_album_str, track)
        if match_ratio > match_percentage:  # adjust threshold in .env file
            return track['uri']
    
    return None

# Function to add to playlist in chunks
def add_tracks_to_playlist(playlist_id, track_uris):
    # Spotify's API allows adding a maximum of 100 tracks per request, use 99 to be safe
    max_tracks_per_request = 99
    for i in range(0, len(track_uris), max_tracks_per_request):
        batch = track_uris[i:i + max_tracks_per_request]
        spotify.playlist_add_items(playlist_id, batch)

# Function to read files and search for track URIs
def process_playlist_file(file_path, playlist_id):
    track_uris = []
    not_imported_songs = []
    total_lines = sum(1 for line in open(file_path, 'r'))
    print(f"Processing {total_lines} songs in {file_path}...")

    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            try:
                # Show progress
                print(f"Processing song {line_number}/{total_lines}...", end='\r')

                # Check if line contains album information
                if '+' in line:
                    artist_song, album = line.strip().split(' + ')
                    track_uri = search_track(f"{artist_song} - {album}")
                else:
                    track_uri = search_track(line.strip())
                
                if track_uri:
                    track_uris.append(track_uri)
                else:
                    not_imported_songs.append(line.strip())
            except Exception as e:
                print(f"Error processing {line.strip()}: {e}")
                not_imported_songs.append(f"{line.strip()} - Error: {e}")

    # Add all found tracks to the playlist
    if track_uris:
        add_tracks_to_playlist(playlist_id, track_uris)
    
    # Write not imported songs to a file
    if not_imported_songs:
        with open('not_imported_songs.txt', 'a') as error_file:
            for song in not_imported_songs:
                error_file.write(f"{song}\n")

# Loop over your text files in the 'playlists' folder and create playlists accordingly
for filename in os.listdir('playlists'):
    if filename.endswith('.txt'):
        playlist_name = filename.rsplit('.', 1)[0]
        playlist_id = create_playlist(playlist_name, playlist_public, playlist_collaborative)
        file_path = os.path.join('playlists', filename)
        process_playlist_file(file_path, playlist_id)
        print(f"Finished processing {file_path}.")
