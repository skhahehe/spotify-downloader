from unittest.mock import patch, MagicMock
from backend.services.youtube_service import YouTubeService

TRACK = {'title': 'Blinding Lights', 'raw_title': 'Blinding Lights', 'artist': 'The Weeknd', 'duration_ms': 200000}


def _fake_ydl(result):
    ydl = MagicMock()
    ydl.__enter__.return_value.extract_info.return_value = result
    return ydl


def test_search_survives_missing_fields():
    entries = [
        None,
        {'id': 'a', 'url': 'u1', 'title': 'The Weeknd - Blinding Lights', 'duration': None, 'uploader': None, 'channel': 'TheWeekndVEVO'},
        {'id': 'b', 'url': None, 'title': 'no url'},
        {'id': 'c', 'url': 'u3', 'title': 'Blinding Lights', 'duration': 200, 'uploader': 'The Weeknd - Topic'},
    ]
    with patch('backend.services.youtube_service.yt_dlp.YoutubeDL', return_value=_fake_ydl({'entries': entries})):
        res = YouTubeService().search_and_rank(TRACK)
    assert [r['id'] for r in res] == ['c', 'a']  # topic + exact duration ranks first; url-less entry dropped
    assert res[1]['channel'] == 'TheWeekndVEVO'


def test_search_handles_none_result():
    with patch('backend.services.youtube_service.yt_dlp.YoutubeDL', return_value=_fake_ydl(None)):
        assert YouTubeService().search_and_rank(TRACK) == []
