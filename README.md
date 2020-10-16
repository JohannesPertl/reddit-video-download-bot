<h1 align=center>Video Download Bot for reddit</h1>
<p align=center>A bot for reddit that provides downloadable links for videos by using an external service</p>


## Table of Contents


* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Run the bot](#run-the-bot)
* [Usage](#usage)
* [License](#license)
* [Acknowledgements](#acknowledgements)


## Prerequisites

* Python3
* A reddit account
* Docker
  

## Installation


* Clone the repo

      git clone https://github.com/JohannesPertl/reddit-video-download-bot.git
    
* Create a [reddit app](https://ssl.reddit.com/prefs/apps/)
* Fill in the credentials in a [praw.ini file](https://praw.readthedocs.io/en/latest/getting_started/configuration/prawini.html)
located in the shared folder
* Fill in the bot configuration in [config.yaml](shared/config.yaml)

## Run the bot

**Start:** ```bash start.sh```  
**Stop:** ```bash stop.sh```

You can scale each service by editing the ```start.sh``` script

## Usage

Mention the bot's name as a comment or send it a private message with the post link

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.


## Acknowledgements

Special thanks to the owner of **www.reddit.tube** who very kindly lets me use their service! 




