# Peer Testing Website
© Léon McGregor, Manuel Maarek, 2017-2020

# Environment
* Linux *or* [Windows 10 with LXSS](https://msdn.microsoft.com/commandline/wsl/about)
* Python 3 (preferrably 3.5 or higher)
* Python virtualenv package
* This may require pip 3
* Resources to conduct coursework tasks (e.g. java, javac)
 


# Installation

1. Create a Venv `python3 -m virtualenv name-of-your-venv`
   * Or `python3.5 -m venv name-of-your-venv`
   * Choose a short name for your venv
   * Ensure this is run using python3
2. Activate Venv `source name-of-your-venv/bin/activate`
3. Clone Repository with `git clone`
4. Go into repository `cd repository/website`
5. Install Necessary Packages `pip install -r requirements.txt`
6. Locate `website/main/default_local.py` and `website/main/default_secret.py`
7. Copy this into `website/main/local.py` and `website/main/secret.py` respectively, and edit the variables within the file accordingly
    * Developing using the built-in webserver? DONT use an HTTP prefix in local.py
8. Make these checks and then run the commands within `init-dev.sh`
   * Double-check usernames within `setfacl` commands
   * If only running local debug, and not serving over apache, `setfacl` commands are not needed
   * Make sure to set appropriate admin user details
9. Run the server using `manage.py runserver 0.0.0.0:8000`
   * [Optional] Add `0.0.0.0 example.com` to your `/etc/hosts`
10. Visit either [http://example.com:8000](http://example.com:8000) or [http://localhost:8000](http://localhost:8000) in a web browser

## Setting up a GitLab connection
* Logins only work through gitlab, so you need to set this up
* Log in as a GitLab administrator
* Go to /admin/applications and make a new one
* Set the redirect URI as: http://your-url.domain/prefixes/complete/gitlab/
* Set the "scopes" as [api, read_user]
* Copy the secrets to `secret.py`

## Preparing for users
* Create a `roles.csv` file in the base directory like so:
    * *email,role,course* where *email* is an email, *role* is teacher|student, *course* is a course ID
    * emails should match those used on gitlab
* Create a `groups.csv` file in the base directory like so:
    * *"group_id","user_ids"*, where *group_id* is a number and *user_ids* is a CSV string of user ids surrounded by quotes

## Logging in for the first time
* Log in to gitlab as a teacher
* Open the peer-testing website
* You will go through the gitlab authorisation flow
* You will then be taken to the teacher admin page
    * Enrolled users are added automatically to their course when they log in

# Running A Coursework
* Make it
* The coursework ID must be the same as the project/repository that code will be fetched from
