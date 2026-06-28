# =============================================================================
#  main.py  --  the starting point for the BROWSER version of the game.
# =============================================================================
#
#  You don't need this file to play on your own computer.
#  For that, just run:   python game.py
#
#  This file exists because the browser packager (pygbag) always looks for a
#  file named exactly "main.py" to start from. All it does is launch the game.
#
#  To build and play in a browser yourself:
#       pip install pygbag
#       pygbag main.py
#  ...then open the address it prints (http://localhost:8000) in any browser.
# =============================================================================

import asyncio
from game import main

asyncio.run(main())
