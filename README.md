## Installation

### Source code
First clone the repository, then run `pip3 install -r requirements.txt` inside of the repository folder.

### PyPI
\<to be added\>

### Linux dependencies
This app is designed for linux distributions. You can install the dependecises for linux using the following command:
```console
Amin@Maximus:./Data-Manager$ bash requirements_linux.sh

```

## Usage

After installing the dependencies, you can run the program via following command:
```console
Amin@Maximus:./Data-Manager$ python3 src/main.py --server_ip localhost --port 8080

```
You can access the app via the following url http://localhost:8080. It is also possible to run the program on a different PORT (Please to make sure that PORT is open in your firewall settings). 
The default username and password are *admin* and *admin* (You can change this password in the <em>profile</em> tab).
