"""  
Air Hockey Vision  
=================  
Entry point.  Run:  python main.py  
"""  

import sys
import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL",  "3")
os.environ.setdefault("GLOG_minloglevel",       "3")
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU",  "1")
os.environ.setdefault("OPENCV_LOG_LEVEL",       "SILENT")

# ── MUST be first: fix MediaPipe Unicode-path issue on Windows ────────────────
def _patch_mediapipe_unicode_path():
    try:
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

        import mediapipe as mp
        mp_dir = os.path.dirname(mp.__file__)
        if mp_dir.isascii():
            return

        import shutil
        temp_root = (os.environ.get("TEMP") or os.environ.get("TMP") or r"C:\Temp")
        fix_root  = os.path.join(temp_root, "ahv_mediapipe")
        fix_dir   = os.path.join(fix_root, "mediapipe")

        if not os.path.isdir(fix_dir):
            print("[Fix] Copying MediaPipe models to ASCII path (first run only)...")
            shutil.copytree(mp_dir, fix_dir)

        mp.__file__ = mp.__file__.replace(mp_dir, fix_dir)

        try:
            import mediapipe.python._framework_bindings.resource_util as ru
            orig_set = ru.set_resource_dir
            def patched_set(path):
                if isinstance(path, str):
                    path = path.replace(os.path.dirname(mp_dir), fix_root)
                return orig_set(path)
            ru.set_resource_dir = patched_set
            import mediapipe.python.solution_base as sb
            if hasattr(sb, 'resource_util'):
                sb.resource_util.set_resource_dir = patched_set
        except Exception:
            pass

        try:
            import mediapipe.python.solution_base as sb
            cls = sb.validated_graph_config.ValidatedGraphConfig
            orig_init = cls.initialize
            def patched_init(self, *args, **kwargs):
                new_kwargs = kwargs.copy()
                if 'binary_graph_path' in new_kwargs and new_kwargs['binary_graph_path']:
                    new_kwargs['binary_graph_path'] = new_kwargs['binary_graph_path'].replace(mp_dir, fix_dir)
                new_args = [a.replace(mp_dir, fix_dir) if isinstance(a, str) else a for a in args]
                return orig_init(self, *new_args, **new_kwargs)
            cls.initialize = patched_init
        except Exception as e:
            print(f"[Fix] ValidatedGraphConfig patch failed: {e}")

        print("[Fix] MediaPipe ASCII redirect applied successfully.")
    except Exception as e:
        print(f"[Fix] MediaPipe path patch skipped: {e}")


_patch_mediapipe_unicode_path()
# ────────────────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(__file__))


def _preload():
    """Pre-warm pygame, fonts, and background cache so first frame is instant."""
    import pygame
    if not pygame.get_init():
        pygame.init()
    pygame.font.init()

    from src.core.settings import (
        FONT_HUGE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY
    )
    from src.rendering.ui import FontCache
    for size in (FONT_HUGE, FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY, 36, 40):
        FontCache.get(size, bold=False)
        FontCache.get(size, bold=True)

_preload()

from src.core.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

