# normalize-vid

A script for outputting videos with a standarized framerate and size appropriate for downloading in CAR and projecting on the wall.

### Usage
```shell
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

# Run the app.
(env) ~/normalize-vid$ python3 normalize-vids.py

# Deactivate environment afterwards.
(env) ~/normalize-vid$ deactivate
~/normalize-vid$
```
