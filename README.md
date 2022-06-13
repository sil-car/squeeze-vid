# normalize-vid

A script for outputting videos with a standardized frame rate and size appropriate for downloading in CAR and projecting on the wall.

Property | Default Video | Tutorial Video
--- | --- | ---
Height | 720p | 720p
Video bitrate | 2 Mbps | 500 kbps
Frame rate | 25 fps | 10 fps

## Usage
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

## Notes

### Setting appropriate values for framerate, resolution, and bitrate

- HD video has 2 **resolutions**: 720p and 1080p. (Note: 4K is actually "2160p".)
- **Framerates** can vary from 24pfs (film) to 30fps (common streaming) to 60 fps
(fast-paced video) and higher.
- Video **bitrate** can vary from 500 Kbps to 8 Mpbs or more.

#### Resolution: 720p

Assuming mediocre projector quality and internet bandwidth, 720p video strikes a reasonable balance between picture size and file size.

#### Framerate: 25fps

Assuming that most content consists of presentations with a slow pace, 25 fps seems to be a sufficient framerate.

#### Bitrate: 2Mbps

For 720p 30fps video, bitrate recommendations range from 500 Kbps to 4 Mbps. Personal experience has led to choosing a bitrate of 2 Mbps in an attempt to balance the tensions between filesize and perceived quality.

**References**
https://www.multivu.com/blog/2017/video-specs-for-noobs.html
https://streamlabs.com/content-hub/post/best-bitrate-settings-for-live-streaming
