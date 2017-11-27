# eMusic
Python 3.6 music bot for Ethereal Network's Discord.

### Known issues: tls errors (they do not effect functionality at this time).

## Quick-Start

If all you want to do is use the bot without creating your own instance:
https://discordapp.com/api/oauth2/authorize?client_id=277298573794607105&scope=bot&permissions=1

Bot may go down unexpectantly if I am working on it, but should be back up in a few moments.

## Creating Own Instance

First, download eMusic.py, emusic_properties.yml, and PlayerPlaylist.py.
Then, place them into a directory together.

### Create a Bot User:
    1. Go to: https://discordapp.com/developers/applications/me
    2. Click New App
    2. Give the app a name (required), description (optional), and icon (optional).
    3. Click Create App
    4. Click on Create a Bot User button.

In the emusic_properties.yml file, add the Bot User's id and token.
Then, choose a command prefix (what you type before a command).

### Windows

Next, download FFmpeg here: http://ffmpeg.zeranoe.com/builds/
Extract the ffmpeg, ffplay, and ffprobe executables and place them in the same directory 
as the eMusic.py file.

Download Python 3.6 here: https://www.python.org/downloads/
Make sure to add Python 3.6 to your PATH. (Check box option in the installer.)

Once installed open a command prompt as administrator and type the following commands:
```
python -m pip install -U PyYaml
python -m pip install -U youtube-dl
python -m pip install -U Discord.py[voice]
```
You can close this command prompt after the installs.

Finally, open another command prompt and change to the directory eMusic.py is in.
Then, run the following command:
```
python eMusic.py
```

### Linux
Install FFmpeg with:
```
sudo apt-get install ffmpeg
```

Install Python 3.6 for your respective distro or use 3.5 then run the following commands.
```
python3 -m pip install -U PyYaml
python3 -m pip install -U youtube-dl
python3 -m pip install -U Discord.py[voice]
```
If an install fails, it is most likely due to not having the dev libraries. (Just Google it.)

Finally, open a terminal in the same directory as eMusic.py and run the following command:
```
python3 eMusic.py
```

That's it! Use the link that is printed in the command prompt to add the bot to your discord server.