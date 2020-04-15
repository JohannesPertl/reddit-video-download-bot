

<h1 align=center>VredditDownloader</h1>
<p align=center>A bot for reddit that provides downloadable links for v.redd.it videos</p>


## Table of Contents

* [About the Project](#about-the-project)
  * [Usage](#usage) 
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
  * [Running the bot](#running-the-bot)
  * [Start automatically](#start-automatically-at-reboot)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)
* [Acknowledgements](#acknowledgements)

## About The Project

Videos hosted on the social media platform www.reddit.com are nearly impossible to download, especially with sound. To make sharing easier, I decided to write my own bot that provides an easy way to download them. 

Since 2018, I run it on my own Raspberry Pi at home.

Currently, the bot account is [VredditDownloader](https://www.reddit.com/user/VredditDownloader). 


### Usage

If you just want a quick download link, mention "u/VredditDownloader" as a comment under any video hosted on Reddit, or send a private message containing the link. The bot will reply within a few seconds.

You can find more info [at the bot's reddit profile](https://www.reddit.com/user/VredditDownloader/comments/cju1dg/info).


## Getting Started

To host your own video download bot, follow these simple example steps.
    

### Prerequisites

* Python3
* A Reddit Account
  

### Installation


* Clone the repo

      git clone https://github.com/JohannesPertl/vreddit-download-bot.git
    
* Create an app [here](https://www.reddit.com/prefs/apps)
   * Paste the credentials into the [praw.ini file](praw.ini)
* Fill in the bot configuration in [config.yaml](config.yaml)
* Install the requirements

      pip install -r requirements.txt

### Running the bot

    python3 -i bot.py
    
### Start automatically at reboot

To start the bot automatically in the background on Linux, add a cronjob with

    crontab -e
   
and add this line (replace <path> with path to your local repository)

    @reboot python <path>/bot.py &>> /dev/null
    

## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/SomeFeature`)
3. Commit your Changes (`git commit -m 'Add some Feature'`)
4. Push to the Branch (`git push origin feature/SomeFeature`)
5. Open a Pull Request




## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.


## Contact

johannes.pertl@edu.fh-joanneum.at


## Acknowledgements

Special thanks to the owners of **www.vreddit.cc**, **www.viddit.red**, **www.reddit.tube** and **www.lew.la**, who very kindly let me use their services! 

* [Praw](https://praw.readthedocs.io/en/latest)
* [Readme Template](https://github.com/othneildrew/Best-README-Template/blob/master/README.md#acknowledgements)




