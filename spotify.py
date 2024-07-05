import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from tqdm import tqdm

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 获取环境变量
spotify_client_id = os.getenv('spotify_client_id')
spotify_client_secret = os.getenv('spotify_client_secret')
spotify_redirect_uri = os.getenv('spotify_redirect_uri')
spotify_scope = os.getenv('spotify_scope')
spotify_username = os.getenv('spotify_username')

# 指定缓存文件的位置
cache_path = 'C:/Users/mumua/Desktop/spotify_youtube/.cache'

# Spotify 認證
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_client_id,
                                               client_secret=spotify_client_secret,
                                               redirect_uri=spotify_redirect_uri,
                                               scope=spotify_scope,
                                               cache_path=cache_path))

# 獲取 Spotify 播放列表的曲目信息
def get_playlist_tracks(username, playlist_id):
    try:
        results = sp.user_playlist_tracks(username, playlist_id)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        return tracks
    except spotipy.exceptions.SpotifyException as e:
        print(f"Error retrieving playlist: {e}")
        return None

# 獲取 Spotify 喜歡的曲目
def get_liked_tracks():
    try:
        results = sp.current_user_saved_tracks()
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        return tracks
    except spotipy.exceptions.SpotifyException as e:
        print(f"Error retrieving liked tracks: {e}")
        return None

# 獲取 YouTube API 的憑證
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

def youtube_auth():
    print("Current working directory: ", os.getcwd())  # 打印當前工作目錄
    creds = None
    credentials_path = "C:/Users/mumua/Desktop/spotify_youtube/credentials.json"
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

youtube = youtube_auth()

# 在 YouTube 上查找對應的視頻
def search_youtube(track_name, cache):
    if track_name in cache:
        return cache[track_name]
    
    print(f"[sea]{track_name}")
    request = youtube.search().list(
        part="snippet",
        maxResults=1,
        q=track_name
    )
    response = request.execute()
    if response["items"]:
        for item in response["items"]:
            if 'videoId' in item["id"]:
                video_id = item["id"]["videoId"]
                cache[track_name] = video_id
                return video_id
    return None

# 創建 YouTube 播放列表
def create_youtube_playlist(title, description):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return response["id"]

# 添加視頻到 YouTube 播放列表
def add_video_to_playlist(playlist_id, video_id, track_name):
    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    request.execute()
    print(f"[add]{track_name}")

# 保存和加載 YouTube 搜索結果的缓存
def load_cache(cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache, cache_file):
    with open(cache_file, 'wb') as f:
        pickle.dump(cache, f)

# 選擇要轉移的曲目
def transfer_tracks_to_youtube(tracks, playlist_name, youtube_playlist_id):
    not_found_tracks = []
    cache_file = 'youtube_search_cache.pkl'
    cache = load_cache(cache_file)
    
    for track in tqdm(tracks, desc="Processing tracks"):  # 移除最大處理曲目數量限制
        track_name = track['track']['name'] + " " + track['track']['artists'][0]['name']
        video_id = search_youtube(track_name, cache)
        if video_id:
            add_video_to_playlist(youtube_playlist_id, video_id, track_name)
        else:
            not_found_tracks.append(track_name)
    
    save_cache(cache, cache_file)

    # 將找不到的歌曲保存到文本文件
    if not_found_tracks:
        with open(f'C:/Users/mumua/Desktop/spotify_youtube/not_found_tracks_{playlist_name}.txt', 'w') as f:
            f.write("The following tracks could not be found on YouTube:\n")
            for track in not_found_tracks:
                f.write(track + "\n")
        print(f"{len(not_found_tracks)} songs not found")

# 從 Spotify 播放列表或喜歡的曲目中選擇曲目進行轉移
def main():
    choice = input("Enter playlist ID or liked to download liked-playlist: ")
    if choice.lower() == 'liked':
        tracks = get_liked_tracks()
        playlist_name = 'liked'
    else:
        playlist_id = choice
        tracks = get_playlist_tracks(spotify_username, playlist_id)
        playlist_name = 'specific_playlist'

    if tracks is None:
        print("No tracks found. Exiting.")
        return

    youtube_playlist_id = create_youtube_playlist(f'spotify-{playlist_name}', f'Converted from Spotify {playlist_name}')
    transfer_tracks_to_youtube(tracks, playlist_name, youtube_playlist_id)

if __name__ == "__main__":
    main()
