"""
Usage:

You must give your office number as the first argument:

    lights.py ROOM

With no other arguments, the lights are reset:

lights.py ROOM

You can also specify brightness or color with a range 0-4:

    lights.py ROOM brightness 2

    lights.py ROOM color 3

"""

import sys
from io import BytesIO
import time

import click
import numpy as np
from PIL import Image
from selenium import webdriver
import chromedriver_binary
from selenium.webdriver.chrome.options import ChromiumOptions
from selenium.webdriver.common.action_chains import ActionChains


def setup_driver(url):
    """Connect to the light-control page"""
    print(f"Connecting to {url}")
    options = ChromiumOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    # See https://stackoverflow.com/questions/72111139/this-version-of-chromedriver-only-supports-chrome-version-102
    print(chromedriver_binary.chromedriver_filename)
    service = webdriver.ChromeService(chromedriver_binary.chromedriver_filename)
    driver = webdriver.Chrome(service=service, options=options)

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(500, 500)
    driver.implicitly_wait(10)
    driver.get(url)
    return driver


def room_url(room: int):
    """Get the light control URL for a given office number"""
    if room < 300:
        ip = "172.16.4.61"
    elif 300 <= room < 400:
        ip = "172.16.4.62"
    else:
        ip = "172.16.4.63"
    return f"http://{ip}/webvisu/rom{room}.htm"


# positions of buttons
# positions are relative because they scale with the screen
locations = {
    # brightness
    "reset": (0.5, 0.625),
    "brightness": [(x, 0.7) for x in (0.1, 0.3, 0.5, 0.7, 0.9)],
    "color": [(x, 0.9) for x in (0.1, 0.3, 0.5, 0.7, 0.9)],
}


def get_screen(driver):
    """Get the current screen as an rgb numpy array"""
    png = driver.get_screenshot_as_png()
    im = Image.open(BytesIO(png), formats=["png"])
    return np.asarray(im, dtype=np.uint8)[:, :, :3]  # rgba


def wait_for_page(driver):
    """Wait for the app to load

    The loading screen is mostly white,
    so wait for that to change.

    Not sure if there's a better way to wait for a canvas app to load.
    """
    # loading screen is mostly white (~74%)
    white_fraction = 1
    print("Waiting for page to load...", end="")
    while white_fraction > 0.5:
        screen = get_screen(driver)
        white_fraction = (screen.mean(axis=2) == 255).mean()
        sys.stdout.write(".")
        sys.stdout.flush()
        # print(f"Waiting for white screen to clear {white_fraction:.0%}")
        time.sleep(0.1)
    print("ok")


def click_location(driver, location_name, index=None):
    """Click a given location on the app"""
    canvas = driver.find_element(by="id", value="background")
    size = canvas.size
    loc_percent = locations[location_name]
    name = location_name
    if index is not None:
        loc_percent = loc_percent[index]
        name = f"{location_name}:{index}"
    elif isinstance(loc_percent, list):
        # default to the middle
        loc_percent = loc_percent[2]
    x = loc_percent[0] * size["width"] - size["width"] // 2
    y = loc_percent[1] * size["height"] - size["height"] // 2

    print(f"Clicking {name} ({loc_percent=}) ({x=}, {y=})")

    ActionChains(driver).move_to_element(canvas).move_by_offset(x, y).click().perform()
    # Sleep for two seconds
    time.sleep(5.0)


@click.command()
@click.argument("room", type=int)
@click.argument(
    "button", type=click.Choice(list(locations)), default="reset", required=False
)
@click.argument("index", type=int, required=False)
def lights(room: int, button: str = "reset", index: int | None = None):
    """Interact with the lights for ROOM

    If only the room number is specified,
    the brightness reset button is chosen.

    For multi-value buttons (e.g. brightness, color),
    an INDEX [0-4] can select which button.
    """
    driver = setup_driver(room_url(room))
    wait_for_page(driver)
    click_location(driver, button, index)
    # is there a condition to wait for??
    # if we exit too early, the event doesn't register
    time.sleep(1)


if __name__ == "__main__":
    lights()
