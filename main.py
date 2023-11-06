import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import subprocess

# Execute dump_playlist_to_txt.py to get songs from ViMusic
subprocess.run(['python', 'dump_playlist_to_txt.py'])

# Load environment variables
load_dotenv()

# Retrieve environment variables
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')
username = os.getenv('SPOTIFY_USERNAME')
playlist_public = os.getenv('PLAYLIST_PUBLIC') == 'True'
playlist_collaborative = os.getenv('PLAYLIST_COLLABORATIVE') == 'True'

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

# Function to search for the Track names on Spotify
def search_track(artist_song_str):
    # Search for the track on Spotify
    results = spotify.search(q=artist_song_str, type='track', limit=1)
    # Get the first track's URI if the search returned tracks
    track_uri = results['tracks']['items'][0]['uri'] if results['tracks']['items'] else None
    return track_uri

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

