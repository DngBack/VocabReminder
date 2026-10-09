"""Fetch the classic game sprites used by the desktop prototype.

Source: https://github.com/PokeAPI/sprites/tree/master/sprites
The files are bundled locally; the running app does not need an internet connection.
"""

from pathlib import Path
from urllib.request import urlopen

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)
BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"

BALLS = ("poke-ball", "great-ball", "ultra-ball", "master-ball", "premier-ball", "luxury-ball")
POKEMON = {"pikachu": 25, "charmander": 4, "bulbasaur": 1,
           "squirtle": 7, "eevee": 133, "jigglypuff": 39}


def download(url, path):
    with urlopen(url, timeout=30) as response:
        data = response.read()
    path.write_bytes(data)
    with Image.open(path) as sprite:
        sprite.verify()
    print(path.name, len(data))


if __name__ == "__main__":
    for ball in BALLS:
        download(f"{BASE}/items/{ball}.png", OUT / f"orb_{ball.replace('-', '_')}.png")
    for name, number in POKEMON.items():
        download(f"{BASE}/pokemon/versions/generation-v/black-white/{number}.png",
                 OUT / f"pokemon_{name}.png")
    icon = Image.open(OUT / "orb_poke_ball.png").convert("RGBA")
    icon.resize((256, 256), Image.Resampling.NEAREST).save(OUT / "app_icon.png")
    icon.save(OUT / "app_icon.ico", sizes=[(16, 16), (32, 32), (48, 48),
                                          (64, 64), (128, 128), (256, 256)])
