import _thread
import youtube_dl


class PlayerPlaylist:
    def __init__(self, channel, voice_client, source):
        self.channel = channel
        self.voice_client = voice_client
        self.source = source
        self.urls = []
        self.completed = False
        self.youtube_dl_options = dict(
            ignoreerrors=True,
            noplaylist=False,
            default_search="auto",
            quiet=True,
            nocheckcertificate=True,
            abortonerror=False
        )
        try:
            _thread.start_new_thread(self.download_playlist_info, ())
        except Exception as e:
            print(e)
            pass

    def download_playlist_info(self):
        with youtube_dl.YoutubeDL(self.youtube_dl_options) as ytdl:
            ytdl_playlist = ytdl.extract_info(self.source, download=False)
        for video in ytdl_playlist['entries']:
            if video is not None:
                self.urls.append(video['webpage_url'])
        self.completed = True
