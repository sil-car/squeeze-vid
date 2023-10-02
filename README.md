# Squeeze Vid

Normalize videos and audio files to a standardized frame rate and quality to minimize the file size while maintaining adequate quality for video projection.

Property | Default Video | Tutorial Video
--- | --- | ---
Height | 720p | 720p
Video bitrate | 2 Mbps | 500 kbps
Frame rate | 25 fps | 10 fps

## Install snap package
```
$ snap install squeeze-vid
```

## Usage

```
$ squeeze-vid --help
usage: squeeze-vid [-h] [-a] [-c] [-i] [-k TRIM TRIM] [-n] [-s SPEED] [-t]
                   [-v] [--av1] [--video_encoder VIDEO_ENCODER]
                   [file [file ...]]

Convert video file to MP4, ensuring baseline video quality:
  * Default:  720p, 2 Mbps, 25 fps for projected video
  * Tutorial: 720p, 500 Kbps, 10 fps for tutorial video

Also perform other useful operations on media files.

positional arguments:
  file                  space-separated list of media files to modify

optional arguments:
  -h, --help            show this help message and exit
  -a, --audio           convert file(s) to MP3 audio
  -c, --command         print the equivalent ffmpeg bash command and exit
  -i, --info            show stream properties of given file (only 1 accepted)
  -k TRIM TRIM, --trim TRIM TRIM
                        trim the file to keep content between given timestamps
                        (HH:MM:SS)
  -n, --normalize       normalize video reslution, bitrate, and framerate;
                        this is also the default action if no options are given
  -s SPEED, --speed SPEED
                        change the playback speed of the video using the given
                        factor (0.5 to 100)
  -t, --tutorial        use lower bitrate and fewer fps for short tutorial
                        videos
  -v, --verbose         give verbose output
  --av1                 shortcut to use libsvtav1 video encoder
  --video_encoder VIDEO_ENCODER
                        specify video encoder [libx264]: libx264, libsvtav1,
                        libvpx-vp9
```

## Notes

### Setting appropriate values for framerate, resolution, and video/audio bitrate

- "HD" video has 2 **resolutions**: 720p and 1080p. (Note: 4K is actually "2160p".)
- **Framerates** can vary from 24 fps (film) to 30 fps (common streaming) to 60 fps
(fast-paced video) and higher.
- **Video bitrate** can vary from 500 kbps to 8 Mbps or more.
- **Audio bitrate** can vary from 96 kbps to over 1,400 kbps.

#### Resolution: 720p

Assuming mediocre projector quality and internet bandwidth, 720p video strikes a reasonable balance between picture size and file size.

#### Framerate: 25 fps

Assuming that most content consists of presentations with a slow pace, 25 fps seems to be a sufficient framerate.

#### Video Bitrate: 2 Mbps

For 720p 30fps video, bitrate recommendations range from 500 Kbps to 4 Mbps. Personal experience has led to choosing a bitrate of 2 Mbps in an attempt to balance the tensions between filesize and perceived quality.

#### Audio Bitrate: 128 kbps

YouTube audio has chosen to stream AAC files at 126 kbps. At 128 kbps, one can expect to use about 1 MB of storage space for every 1 minute of audio. This seems like a reasonable value for our purposes.

>**References**
>- https://www.multivu.com/blog/2017/video-specs-for-noobs.html
>- https://streamlabs.com/content-hub/post/best-bitrate-settings-for-live-streaming
>- https://homedjstudio.com/audio-bitrates-formats/

## Attributions
[Video icons created by Prashanth Rapolu 15 - Flaticon](https://www.flaticon.com/authors/prashanth-rapolu-15)
