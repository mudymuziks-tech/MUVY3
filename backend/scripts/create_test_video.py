import cv2
import numpy as np


OUTPUT = "tests/fixtures/test_movie.mp4"

WIDTH = 640
HEIGHT = 360
FPS = 30
SECONDS = 5


def main():
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        OUTPUT,
        fourcc,
        FPS,
        (WIDTH, HEIGHT),
    )

    total_frames = FPS * SECONDS

    for i in range(total_frames):
        frame = np.zeros(
            (HEIGHT, WIDTH, 3),
            dtype=np.uint8,
        )

        # Slowly changing visual pattern.
        value = (i * 5) % 255

        frame[:, :] = (
            value,
            (value * 2) % 255,
            (value * 3) % 255,
        )

        cv2.putText(
            frame,
            f"MUVY TEST {i}",
            (50, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (255, 255, 255),
            2,
        )

        writer.write(frame)

    writer.release()

    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()