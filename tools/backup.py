"""Backups of files this toolkit edits. They go OUTSIDE the game's content folder (<content>_backups/...): the game loads stray files
that sit next to the real ones (e.g. SNDG_<course>.bars.bak is opened as a second sound archive and breaks the course music)."""
import os, shutil


def save(content, path, tag='bak'):
    content = os.path.abspath(content); rel = os.path.relpath(os.path.abspath(path), content)
    dst = os.path.join(os.path.dirname(content), os.path.basename(content) + '_backups', rel + '.' + tag)
    if not os.path.exists(dst) and os.path.exists(path):
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(path, dst)
    return dst
