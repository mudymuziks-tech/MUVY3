import cv2
from pathlib import Path

SOURCE_DIR = Path("tests/fixtures/clips")
OUTPUT_DIR = Path("tests/fixtures/small_clips")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for source in SOURCE_DIR.glob("*.mp4"):
    cap = cv2.VideoCapture(str(source))

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if not fps or not width or not height:
        print(f"Skipping {source.name}: could not read video metadata")
        cap.release()
        continue

    # Scale down while preserving aspect ratio.
    target_width = 640
    target_height = round(height * target_width / width)

    output = OUTPUT_DIR / source.name

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(output),
        fourcc,
        fps,
        (target_width, target_height),
    )

    frames = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.resize(
            frame,
            (target_width, target_height),
            interpolation=cv2.INTER_AREA,
        )

        writer.write(frame)
        frames += 1

    cap.release()
    writer.release()

    print(
        f"{source.name}: "
        f"{width}x{height} -> {target_width}x{target_height}, "
        f"{frames} frames"
    )
