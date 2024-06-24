import os
import tempfile
from typing import Optional, BinaryIO, List

from yt_dlp import YoutubeDL
from pydantic import BaseModel

MAX_DURATION = 120  # two minutes


class YoutubeResult(BaseModel):
    video_id: str
    title: str
    description: Optional[str]
    length: int
    views: int


def is_valid_id(youtube_id: str) -> bool:
    return youtube_id is not None and len(youtube_id) == 11


def skip_live(info_dict):
    """
    function to skip downloading if it's a live video (yt_dlp doesn't respect the 20 minute
    download limit for live videos), and we don't want to hang on an hour long stream
    """
    if info_dict.get("is_live"):
        return "Skipping live video"
    return None


class FakeVideoException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class IPBlockedException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def search_videos(query, max_results=8):
    videos = []
    ydl_opts = {
        "format": "worst",
        "dumpjson": True,
        "extract_flat": True,
        "quiet": True,
        "simulate": True,
        "match_filter": skip_live,
    }
    with YoutubeDL(ydl_opts) as ydl:
        try:
            search_query = f"ytsearch{max_results}:{query}"
            result = ydl.extract_info(search_query, download=False)
            if "entries" in result and result["entries"]:
                videos = [
                    YoutubeResult(
                        video_id=entry["id"],
                        title=entry["title"],
                        description=entry.get("description"),
                        length=(int(entry.get("duration")) if entry.get("duration") else MAX_DURATION),
                        views=(entry.get("view_count") if entry.get("view_count") else 0),
                    ) for entry in result["entries"]
                ]
        except Exception as e:
            print(f"Error searching for videos: {e}")
            return []
    return videos


def download_video(
        video_id: str, start: Optional[int] = None, end: Optional[int] = None, proxy: Optional[str] = None
) -> Optional[BinaryIO]:
    if not is_valid_id(video_id):
        raise FakeVideoException(f"Invalid video ID: {video_id}")

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    temp_fileobj = tempfile.NamedTemporaryFile(suffix=".mp4")
    ydl_opts = {
        "format": "worst",  # Download the worst quality
        "outtmpl": temp_fileobj.name,  # Set the output template to the temporary file's name
        "overwrites": True,
        "quiet": True,
        "noprogress": True,
        "match_filter": skip_live,
    }

    if start is not None and end is not None:
        ydl_opts["download_ranges"] = lambda _, __: [{"start_time": start, "end_time": end}]

    if proxy is not None:
        ydl_opts["proxy"] = proxy

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Check if the file is empty (download failed)
        if os.stat(temp_fileobj.name).st_size == 0:
            print(f"Error downloading video: {temp_fileobj.name} is empty")
            temp_fileobj.close()
            return None

        return temp_fileobj
    except Exception as e:
        temp_fileobj.close()
        if (
                "Your IP is likely being blocked by Youtube" in str(e) or
                "Requested format is not available" in str(e)
        ):
            raise IPBlockedException(e)
        if any(fake_vid_msg in str(e) for fake_vid_msg in
               ["Video unavailable", "is not a valid URL", "Incomplete YouTube ID"]):
            raise FakeVideoException(e)
        print(f"Error downloading video: {e}")
        return None


def get_description(yt: YoutubeDL) -> str:
    """
    Get / generate the description of a video from the YouTube API.

    Miner TODO: Implement logic to get / generate the most relevant and information-rich
    description of a video from the YouTube API.
    """
    description = yt.title
    if yt.description:
        description += f"\n\n{yt.description}"
    return description


class VideoMetadata(BaseModel):
    """
    A model class representing YouTube video metadata.
    """
    video_id: str
    description: str
    views: int
    start_time: float
    end_time: float
    video_emb: List[float]
    description_emb: List[float]

    def __repr_args__(self):
        parent_args = super().__repr_args__()
        exclude_args = ['video_emb', 'description_emb']
        return (
                [(a, v) for a, v in parent_args if a not in exclude_args] +
                [(a, ["..."]) for a in exclude_args]
        )
