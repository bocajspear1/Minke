import os

from minke.lib.screenshots import images_are_same



def test_screenshots():
    file_dir = os.path.abspath(os.path.dirname(__file__))
    screenshot_dir = os.path.join(file_dir, "files", "screenshots")
    screenshots = os.listdir(screenshot_dir)
    screenshots.sort()

    pattern = (
        False, False, False, True, True, True, True, True, True, True, True, True, False, True, False, False, True, True, True, True, True
    )

    for i in range(len(screenshots)):
        if screenshots[i] not in (".", "..") and i < len(screenshots)-1:
            print(screenshots[i], screenshots[i+1])
            result = images_are_same(
                os.path.join(screenshot_dir, screenshots[i]), 
                os.path.join(screenshot_dir, screenshots[i+1])
            )
            assert pattern[i] == result
