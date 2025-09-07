"""
Export utilities for transcript formats
"""

import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any


class TranscriptExporter:
    """Handles export of transcripts in various formats"""
    
    def __init__(self):
        self.start_time = None
        self.segments = []
    
    def start_recording(self):
        """Start recording timestamp"""
        self.start_time = time.time()
        self.segments = []
    
    def add_segment(self, text: str, timestamp: float = None):
        """Add a text segment with timestamp"""
        if timestamp is None:
            timestamp = time.time()
        
        if self.start_time is None:
            self.start_time = timestamp
        
        relative_time = timestamp - self.start_time
        self.segments.append({
            'text': text.strip(),
            'timestamp': relative_time,
            'absolute_time': timestamp
        })
    
    def export_txt(self, filename: str) -> bool:
        """Export as plain text"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for segment in self.segments:
                    if segment['text']:
                        f.write(segment['text'] + '\n')
            return True
        except Exception as e:
            print(f"Error exporting TXT: {e}")
            return False
    
    def export_vtt(self, filename: str) -> bool:
        """Export as WebVTT format"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                
                for i, segment in enumerate(self.segments):
                    if not segment['text']:
                        continue
                    
                    start_time = self._format_vtt_time(segment['timestamp'])
                    end_time = self._format_vtt_time(segment['timestamp'] + 5)  # 5 second duration
                    
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment['text']}\n\n")
            
            return True
        except Exception as e:
            print(f"Error exporting VTT: {e}")
            return False
    
    def export_srt(self, filename: str) -> bool:
        """Export as SRT format"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                segment_num = 1
                
                for segment in self.segments:
                    if not segment['text']:
                        continue
                    
                    start_time = self._format_srt_time(segment['timestamp'])
                    end_time = self._format_srt_time(segment['timestamp'] + 5)  # 5 second duration
                    
                    f.write(f"{segment_num}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment['text']}\n\n")
                    
                    segment_num += 1
            
            return True
        except Exception as e:
            print(f"Error exporting SRT: {e}")
            return False
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for VTT (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def export_simple_txt(text: str, filename: str) -> bool:
    """Export simple text to file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"Error exporting text: {e}")
        return False


def export_simple_vtt(text: str, filename: str) -> bool:
    """Export simple text as VTT with basic timing"""
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for i, line in enumerate(lines):
                start_time = i * 5  # 5 seconds per line
                end_time = start_time + 5
                
                start_formatted = f"{start_time//60:02d}:{start_time%60:02d}.000"
                end_formatted = f"{end_time//60:02d}:{end_time%60:02d}.000"
                
                f.write(f"{start_formatted} --> {end_formatted}\n")
                f.write(f"{line}\n\n")
        
        return True
    except Exception as e:
        print(f"Error exporting VTT: {e}")
        return False


def export_simple_srt(text: str, filename: str) -> bool:
    """Export simple text as SRT with basic timing"""
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        with open(filename, 'w', encoding='utf-8') as f:
            for i, line in enumerate(lines):
                start_time = i * 5  # 5 seconds per line
                end_time = start_time + 5
                
                start_formatted = f"00:{start_time//60:02d}:{start_time%60:02d},000"
                end_formatted = f"00:{end_time//60:02d}:{end_time%60:02d},000"
                
                f.write(f"{i + 1}\n")
                f.write(f"{start_formatted} --> {end_formatted}\n")
                f.write(f"{line}\n\n")
        
        return True
    except Exception as e:
        print(f"Error exporting SRT: {e}")
        return False
