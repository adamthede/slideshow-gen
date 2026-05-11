import pytest
from slideshow_gen.kenburns import choose_effect, KenBurnsEffect, Direction, ScaleMode
from slideshow_gen.config import RenderConfig

def test_choose_effect_static_panorama():
    # Aspect ratio 3.0 > 2.5
    effect = choose_effect(3000, 1000, 1.77)
    assert effect.is_static is True
    assert effect.direction_z == Direction.IN

def test_choose_effect_static_tiny():
    # Long edge < 800
    effect = choose_effect(600, 400, 1.77)
    assert effect.is_static is True

def test_choose_effect_animated():
    # Normal image, should animate
    effect = choose_effect(1920, 1080, 1.77)
    assert effect.is_static is False
    assert effect.scale_mode in (ScaleMode.CROP_CENTER, ScaleMode.PAD)
