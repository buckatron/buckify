import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import re
from concurrent.futures import ThreadPoolExecutor

# Replace these with your Spotify Developer credentials
CLIENT_ID = 'eaf534fdf3144297ada96343fdce8478'
CLIENT_SECRET = '0c67ed68d7cc4207ba7ef7ec82adb6a7'
REDIRECT_URI = 'http://localhost:8888/callback'

# Spotify authorization scope
SCOPE = 'playlist-modify-public playlist-modify-private playlist-read-private'

def get_playlist_id(playlist_url):
    match = re.match(r'https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)', playlist_url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Spotify playlist URL")

def get_playlist_tracks(sp, playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def is_valid_track(sp, track_uri):
    try:
        sp.track(track_uri)
        return True
    except spotipy.exceptions.SpotifyException:
        return False

def validate_tracks(sp, track_uris):
    valid_tracks = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(is_valid_track, sp, track_uri): track_uri for track_uri in track_uris}
        for future in futures:
            track_uri = futures[future]
            try:
                if future.result():
                    valid_tracks.append(track_uri)
            except Exception as e:
                print(f"Error validating track {track_uri}: {e}")
    return valid_tracks

def create_shuffled_playlist(sp, user_id, original_playlist_id):
    # Get the original playlist's tracks
    tracks = get_playlist_tracks(sp, original_playlist_id)
    
    # Extract track URIs
    track_uris = [track['track']['uri'] for track in tracks if track['track'] is not None]
    
    # Validate tracks concurrently
    valid_tracks = validate_tracks(sp, track_uris)
    
    # Shuffle the tracks
    random.shuffle(valid_tracks)
    
    # Get the original playlist's details
    original_playlist = sp.playlist(original_playlist_id)
    original_name = original_playlist['name']
    
    # Create a new playlist
    new_playlist = sp.user_playlist_create(user_id, original_name + " (Shuffled)", public=False)
    new_playlist_id = new_playlist['id']
    
    # Add shuffled tracks to the new playlist in chunks of 100 (API limit)
    for i in range(0, len(valid_tracks), 100):
        sp.user_playlist_add_tracks(user_id, new_playlist_id, valid_tracks[i:i+100])
    
    print(f"New shuffled playlist created: {new_playlist['external_urls']['spotify']}")

def main():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,
                                                   client_secret=CLIENT_SECRET,
                                                   redirect_uri=REDIRECT_URI,
                                                   scope=SCOPE))
    
    user_id = sp.current_user()['id']
    
    playlist_url = input("Enter the Spotify playlist URL: ")
    
    try:
        playlist_id = get_playlist_id(playlist_url)
        create_shuffled_playlist(sp, user_id, playlist_id)
    except ValueError as e:
        print(e)
    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify error: {e}")

if __name__ == "__main__":
    main()
