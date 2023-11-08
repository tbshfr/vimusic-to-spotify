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
    print(f"Error executing 'dump_playlist_to_txt.py': {dump_result.stderr}")
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
match_percentage = float(os.getenv('MATCH_VALUE'))

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
    query_artist_names = {name.strip() for name in query_parts[0].split(',')}
    track_artist_names = {artist['name'].lower() for artist in track['artists']}
    
    artist_match = not query_artist_names.isdisjoint(track_artist_names)
    if not artist_match:
        return 0  # No artist match, return 0%

    query_song = query_parts[1] if len(query_parts) > 1 else ""
    track_song = track['name'].lower()

    # Calculate the similarity percentage between song names
    song_match_percentage = similar(query_song, track_song) * 100

    # Include the album in the comparison if it's present in the query
    album_match_percentage = 100  # Default to 100 if no album is specified
    if len(query_parts) > 2 and 'album' in track:
        query_album = query_parts[2].lower()
        track_album = track['album']['name'].lower()
        album_match_percentage = similar(query_album, track_album) * 100

    # Calculate a weighted average where the song name is twice as important as the album
    weighted_match_percentage = (song_match_percentage * 2 + album_match_percentage) / 3

    return weighted_match_percentage

def clean_title(title):
    # List of words/phrases to filter out
    filters = ['video', 'official video', 'lyrics', 'official audio', 'official', 'audio']
    
    # Replace each filter word/phrase with an empty string
    for f in filters:
        title = title.replace(f, '')
    
    # Return the cleaned title
    return title.strip()

# Function to search for the Track names on Spotify, including the album if available
def search_track(artist_song_album_str):
    parts = artist_song_album_str.split(" - ")
    artist = clean_title(parts[0]) if len(parts) > 0 else ""
    song = clean_title(parts[1]) if len(parts) > 1 else ""
    album = clean_title(parts[2]) if len(parts) > 2 else ""

    # Use explicit fields for artist and track if both are available
    if artist and song:
        query = f"artist:{artist} track:{song}"
    else:
        # Fallback to general search query if only one is available
        query = f"{artist} {song}"

    # Include album in the query if available
    if album:
        query += f" album:{album}"

    results = spotify.search(q=query, type='track', limit=10)
    best_match = None
    best_match_percentage = 0
    best_match_uri = None

    for track in results['tracks']['items']:
        current_match_percentage = verify_track(artist_song_album_str, track)
        if current_match_percentage > best_match_percentage:
            best_match_percentage = current_match_percentage
            best_match = f"{track['artists'][0]['name']} - {track['name']}"
            if current_match_percentage >= match_percentage * 100:  # Convert threshold to percentage
                best_match_uri = track['uri']
    
    return best_match_uri, best_match, best_match_percentage

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
                    full_query = f"{artist_song} - {album}"
                else:
                    artist_song = line.strip()
                    full_query = artist_song
                    album = ""
                
                track_uri, best_match, best_match_percentage = search_track(full_query)
                
                if track_uri:
                    track_uris.append(track_uri)
                else:
                    # Append the best match details to the not_imported_songs list
                    not_imported_songs.append(f"{full_query} -> {best_match} with match percentage {best_match_percentage:.2f}")
            except Exception as e:
                print(f"Error processing {line.strip()}: {e}")
                not_imported_songs.append(f"{line.strip()} - Error: {e}")

    # Add all found tracks to the playlist
    if track_uris:
        add_tracks_to_playlist(playlist_id, track_uris)
    
    # Write not imported songs to a file
    not_imported_count = len(not_imported_songs)
    if not_imported_songs:
        with open('not_imported_songs.txt', 'a') as error_file:
            for song in not_imported_songs:
                error_file.write(f"{song}\n")

    # Print summary after processing each file
    print(f"\nFinished processing {file_path}.")
    print(f"Imported {len(track_uris)} songs.")
    print(f"Did not import {not_imported_count} songs.")
    if not_imported_count > 0:
        print("Details of songs not imported can be found in 'not_imported_songs.txt'.")

# Loop over your text files in the 'playlists' folder and create playlists accordingly
for filename in os.listdir('playlists'):
    if filename.endswith('.txt'):
        playlist_name = filename.rsplit('.', 1)[0]
        playlist_id = create_playlist(playlist_name, playlist_public, playlist_collaborative)
        file_path = os.path.join('playlists', filename)
        process_playlist_file(file_path, playlist_id)