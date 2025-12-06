import tempfile
import os
import re
from typing import Dict, Any, List
from fastapi import HTTPException
import yt_dlp
import json

async def get_transcript_ytdlp(video_id: str) -> Dict[str, Any]:
    """
    Fetches transcript using yt-dlp Python library by downloading subtitle files.
    This is a fallback when youtube-transcript-api fails in production.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'subtitlesformat': 'json3',  # JSON format is easier to parse
            'outtmpl': os.path.join(temp_dir, f'{video_id}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download subtitles
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(video_url, download=False)
                
                # Check if subtitles are available
                has_subs = False
                
                # Try automatic captions first
                if 'automatic_captions' in info and 'en' in info['automatic_captions']:
                    has_subs = True
                    ydl.download([video_url])
                # Try manual subtitles
                elif 'subtitles' in info and 'en' in info['subtitles']:
                    has_subs = True
                    ydl_opts['writeautomaticsub'] = False
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                        ydl2.download([video_url])
                
                if not has_subs:
                    raise HTTPException(
                        status_code=404,
                        detail=f"No English subtitles available for video {video_id}"
                    )
                    
            except yt_dlp.utils.DownloadError as e:
                raise HTTPException(
                    status_code=404,
                    detail=f"Failed to download subtitles: {str(e)}"
                )
        
        # Find the subtitle file (json3 format)
        subtitle_files = [f for f in os.listdir(temp_dir) if f.endswith('.json3')]
        
        if not subtitle_files:
            # Fallback: try other formats
            subtitle_files = [f for f in os.listdir(temp_dir) if '.en.' in f and (f.endswith('.json3') or f.endswith('.vtt') or f.endswith('.srv3'))]
        
        if not subtitle_files:
            raise HTTPException(
                status_code=404,
                detail=f"Subtitle file not created for video {video_id}"
            )
        
        subtitle_path = os.path.join(temp_dir, subtitle_files[0])
        
        # Parse subtitle file
        segments = []
        full_text_parts = []
        
        if subtitle_path.endswith('.json3'):
            # Parse JSON3 format
            with open(subtitle_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if 'events' in data:
                    for event in data['events']:
                        if 'segs' in event and event.get('segs'):
                            # Combine segments within an event
                            text_parts = []
                            for seg in event['segs']:
                                if 'utf8' in seg:
                                    text_parts.append(seg['utf8'])
                            
                            text = ''.join(text_parts).strip()
                            # Clean up newlines and extra spaces
                            text = re.sub(r'\s+', ' ', text)
                            
                            if text and 'tStartMs' in event and 'dDurationMs' in event:
                                start = event['tStartMs'] / 1000.0
                                duration = event['dDurationMs'] / 1000.0
                                end = start + duration
                                
                                segments.append({
                                    "start": start,
                                    "end": end,
                                    "text": text
                                })
                                full_text_parts.append(text)
        else:
            # Fallback for VTT or other formats - use webvtt parser
            try:
                import webvtt
                for caption in webvtt.read(subtitle_path):
                    text = re.sub(r'<[^>]+>', '', caption.text)
                    text = text.strip()
                    
                    if text:
                        start = _timestamp_to_seconds(caption.start)
                        end = _timestamp_to_seconds(caption.end)
                        
                        segments.append({
                            "start": start,
                            "end": end,
                            "text": text
                        })
                        full_text_parts.append(text)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse subtitle file: {str(e)}"
                )
        
        if not segments:
            raise HTTPException(
                status_code=404,
                detail="No transcript content found in subtitle file"
            )
        
        return {
            "transcript_text": " ".join(full_text_parts),
            "segments": segments,
            "source": "yt-dlp"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching transcript with yt-dlp: {str(e)}"
        )
    finally:
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass

def _timestamp_to_seconds(timestamp: str) -> float:
    """
    Convert VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to seconds.
    """
    parts = timestamp.split(':')
    
    if len(parts) == 3:  # HH:MM:SS.mmm
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:  # MM:SS.mmm
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(parts[0])
