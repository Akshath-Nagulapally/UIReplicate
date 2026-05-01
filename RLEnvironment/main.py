import numpy as np
from PIL import Image


def get_imitation_image(prompt, url):
    #Spins up docker container with required parameters
    pass


def run_tests(image_one, image_two, sensitivity_score):
    #Run a comparision test of both the images, for now just simple matrix similarity.

    if sensitivity_score <= 0:
        raise ValueError("sensitivity_score must be positive")

    with Image.open(image_one) as first_image, Image.open(image_two) as second_image:
        first = np.asarray(first_image.convert("RGB"), dtype=np.float32) / 255.0
        second = np.asarray(second_image.convert("RGB"), dtype=np.float32) / 255.0

    if first.shape != second.shape:
        raise ValueError(f"image shapes differ: {first.shape} != {second.shape}")

    mse = float(np.mean((first - second) ** 2))
    reward = 1.0 / (1.0 + mse / sensitivity_score)

    return {"mse": mse, "reward": reward}
