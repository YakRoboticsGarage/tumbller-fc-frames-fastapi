# tumbller-fc-frames-fastapi
FastAPI farcaster frames server

Getting Started
---------------

### Requirements

* Python 3.10 or above, with `setuptools`.
* A serial console like `cu` on Linux-compatible systems, RealTerm and PuTTY on Windows, etc.

### First time settings

Optional by recommended: Create a virtual environment for the Python code of this project:

```shell
python -m venv venv
# or
virtualenv venv
```

To activate the virtual environment, you need to tell the command line:

```shell
# Linux compatible shells
source venv/bin/activate

# Windows shells
# TODO
```

To install the project dependencies:

```shell
# At the root of this repository
pip install -e .
```

At this point you should be good to go.

If you also want to modify the code, you are likely to need dev depencies too:

```shell
pip install -e ".[dev]"
```

### Usage

At every usage, when opening a shell for the Python code, you need to ensure the virtual environment is active (often the prompt is prefixed with `venv`).

# TODO
# Serial console on Linux-compatible systems: cu -s 115200 -l /dev/tty.usbserial
