# This is a sample Python script.
import json
import time
from typing import List

from imagebind_wrapper import ImageBind
from video_utils import download_video, search_videos, MAX_DURATION, get_description, VideoMetadata

imagebind = ImageBind()


def search_and_embed_videos(query: str, num_videos: int) -> List[VideoMetadata]:
    """
    Search YouTube for videos matching the given query and return a list of VideoMetadata objects.

    Args:
        query (str): The query to search for.
        num_videos (int, optional): The number of videos to return.

    Returns:
        List[VideoMetadata]: A list of VideoMetadata objects representing the search results.
    """
    # fetch more videos than we need
    results = search_videos(query, max_results=int(num_videos * 1.5))
    print('search_results', len(results))
    video_metas = []
    # take the first N that we need
    for result in results:
        start = time.time()
        download_path = download_video(
            result.video_id,
            start=0,
            end=min(result.length, MAX_DURATION)
        )
        if download_path:
            try:
                description = get_description(result)
                embeddings = imagebind.embed([description], [download_path])
                video_metas.append(VideoMetadata(
                    video_id=result.video_id,
                    description=description,
                    views=result.views,
                    start_time=start,
                    end_time=MAX_DURATION,
                    video_emb=embeddings.video[0].tolist(),
                    description_emb=embeddings.description[0].tolist(),
                ))
            finally:
                download_path.close()
        if len(video_metas) == num_videos:
            break

    return video_metas


if __name__ == '__main__':
    QUERY_STRING = 'omega'
    NUM_VIDEOS = 8
    video_metas = search_and_embed_videos(QUERY_STRING, NUM_VIDEOS)
    with open('sample_output.txt', 'w') as the_file:
        the_file.write(json.dumps([meta.dict() for meta in video_metas]))
