# Peer Testing Website

---

## Environment
* Linux *or* [Windows 10 with LXSS](https://msdn.microsoft.com/commandline/wsl/about)
* Python 3 (preferrably 3.5 or higher)
* Python virtualenv package
* This may require pip 3
* Resources to conduct coursework tasks (e.g. java, javac)
 


## Installation

1. Create a Venv `python3 -m virtualenv name-of-your-venv`
   * Choose a short name for your venv
   * Ensure this is run using python3
2. Activate Venv `source name-of-your-venv/bin/activate`
3. Clone Repository with `git clone`
4. Go into repository `cd repository/patool`
5. Install Necessary Packages `pip install -r requrements.txt`
6. Locate patool/patool/default_local.py
7. Copy this into patool/patool/local.py, and edit the variables within the file accordingly
8. Run or using the commands within `init-dev.sh`
   * Double-check usernames within `setfacl` commands
   * If only running local debug, and not serving over apache, `setfacl` commands are not needed
9. Run the server using `manage.py runserver 0.0.0.0:8000`
   * [Optional] Add `0.0.0.0 peer-testing.com` to your `/etc/hosts`
10. Visit either [http://peer-testing.com:8000](http://peer-testing.com:8000) or [http://localhost:8000](http://localhost:8000) in a web browser
