#!/usr/bin/env python3
"""Repair Argus's single-point triangulation calls for OpenCV 5.

Run with argus_env/bin/python; rerun after reinstalling Argus.
"""

from pathlib import Path
import sys
import sysconfig


def main():
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run this with your Argus virtual environment Python.")
    path = Path(sysconfig.get_path("purelib")) / "argus_gui" / "triangulate.py"
    original = path.read_bytes()
    source = original.decode("utf-8")
    replacements = (
        (
            "cv2.triangulatePoints(P, P1, ps1[:, k], ps2[:, k], tmp)",
            "tmp = cv2.triangulatePoints(P, P1, ps1[:, k:k + 1], ps2[:, k:k + 1])",
        ),
        (
            "cv2.triangulatePoints(P1, P_, ps1[:, k], ps2[:, k], tmp_)",
            "tmp_ = cv2.triangulatePoints(P1, P_, ps1[:, k:k + 1], ps2[:, k:k + 1])",
        ),
    )
    # Check both calls before writing so unexpected package versions stay intact.
    for old, new in replacements:
        if source.count(old) == 1:
            source = source.replace(old, new)
        elif source.count(new) != 1:
            raise SystemExit(f"Unrecognized triangulation code in {path}; no changes written.")
    patched = source.encode("utf-8")
    if patched == original:
        print(f"Already repaired: {path}")
        return
    backup = path.with_name(path.name + ".before-opencv5-fix")
    if not backup.exists():
        backup.write_bytes(original)
    path.write_bytes(patched)
    print(f"Repaired: {path}\nBackup: {backup}")


if __name__ == "__main__":
    main()
