import subprocess
from pathlib import Path
import pytest
import sys
import os
from PIL import Image

# Add src to path to ensure we test the local version
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slideshow_gen.pipeline import RenderPipeline
from slideshow_gen.config import RenderConfig

def generate_test_assets(test_dir: Path):
    """Generate minimal valid assets for testing using Pillow for images."""
    # Use larger images (> 800px) to trigger the Ken Burns zoompan filter path
    # img1.jpg (red)
    img1 = Image.new('RGB', (1200, 900), color='red')
    img1.save(test_dir / "2026-05-19 12-00-00 - Test Image 1.jpg", quality=95)
    
    # img2.jpg (blue)
    img2 = Image.new('RGB', (1200, 900), color='blue')
    img2.save(test_dir / "2026-05-19 12-01-00 - Test Image 2.jpg", quality=95)
    
    # video.mp4 (green, 440Hz tone)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=green:s=640x480:d=2",
        "-f", "lavfi", "-i", "sine=f=440:d=2",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(test_dir / "video.mp4")
    ], check=True, capture_output=True)
    
    # track.mp3 (880Hz tone)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=f=880:d=10",
        "-c:a", "libmp3lame", str(test_dir / "track.mp3")
    ], check=True, capture_output=True)

def get_max_volume(path: Path) -> float:
    """Detect peak volume in dB."""
    cmd = ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stderr.split('\n'):
        if "max_volume:" in line:
            return float(line.split("max_volume:")[1].split("dB")[0].strip())
    return -100.0

def verify_output(output_path: Path):
    """Verify stream parameters and audibility."""
    assert output_path.exists()
    
    # Get stream info via ffprobe
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,channels,sample_rate",
        "-of", "csv=p=0", str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    streams = result.stdout.strip().split('\n')
    
    has_video = False
    has_audio = False
    
    for s in streams:
        parts = s.split(',')
        if len(parts) < 2: continue
        
        # CSV fields might be in different order depending on ffprobe version
        # but usually codec_type is first with -of csv=p=0
        if 'video' in parts:
            idx = parts.index('video')
            # Check for h264 in the codec name part (usually next or previous to 'video')
            if any('h264' in p for p in parts):
                has_video = True
        if 'audio' in parts:
            if 'aac' in parts and '48000' in parts:
                has_audio = True
    
    assert has_video, f"Video stream (h264) not found or wrong codec in: {streams}"
    assert has_audio, f"Audio stream (aac, 2ch, 48000Hz) not found or wrong format in: {streams}"
    
    # Check if audio is actually audible (not just silent anullsrc)
    max_vol = get_max_volume(output_path)
    assert max_vol > -60.0, f"Audio seems silent: {max_vol} dB"

@pytest.fixture
def asset_dir(tmp_path):
    """Fixture to create and populate a test asset directory."""
    d = tmp_path / "assets"
    d.mkdir()
    generate_test_assets(d)
    return d

def test_audio_no_background(asset_dir, tmp_path):
    """Scenario A: Preserves video audio, image slides silent, no background track."""
    output = tmp_path / "output_no_bg.mp4"
    config = RenderConfig(
        output_width=640,
        output_height=480,
        slide_duration=2.0,
        fade_duration=0.5,
        fps=30,
        batch_size=2,
        workers=1,
        verbose=True
    )
    
    pipeline = RenderPipeline(config, [asset_dir], output)
    pipeline.run()
    
    verify_output(output)

def test_audio_with_background(asset_dir, tmp_path):
    """Scenario B: Mixes background track with video audio."""
    output = tmp_path / "output_with_bg.mp4"
    track = asset_dir / "track.mp3"
    config = RenderConfig(
        output_width=640,
        output_height=480,
        slide_duration=2.0,
        fade_duration=0.5,
        fps=30,
        batch_size=2,
        workers=1,
        verbose=True,
        audio_track=track,
        audio_volume=0.5
    )
    
    pipeline = RenderPipeline(config, [asset_dir], output)
    pipeline.run()
    
    verify_output(output)
