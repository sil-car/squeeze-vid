# normalize-vid

A script for outputting videos with a standardized frame rate and size appropriate for downloading in CAR and projecting on the wall.

Property | Default Video | Tutorial Video
---< | ---< | ---<
Height | 720p | 720p
Video bitrate | 500 kbps | 200 kbps
Frame rate: 24 fps | 10 fps

### Usage
```bash
# Clone and enter into repo.
~$ git clone https:github.com/sil-car/normalize-vid.git
~$ cd normalize-vid
~/normalize-vid$

# Create virtual environment.
~/normalize-vid$ python3 -m venv env

# Activate virtual environment.
~/normalize-vid$ source env/bin/activate

# Install enviroment dependencies from requirements.txt.
(env) ~/normalize-vid$ pip3 install --requirement requirements.txt

# See app help info.
(env) ~/normalize-vid$ python3 normalize-vid.py --help

# Deactivate environment afterwards.
(env) ~/normalize-vid$ deactivate
~/normalize-vid$
```
