import os
import json
from lxml import html
import requests
import sys

# This script is a slightly modified version of the original Keybase verification script more accomodated to the Keycord verification process.
# It does seem bad that the original wouldn't work as intended but that's only due to the expectation of having to login and a few other things.

print("Welcome to the Keycord verification script. The point of this script "
"is to help you see what an end-to-end working integration flow looks "
"like. It is our hope that this will help you have something to build "
"against. For more info, check out our docs: "
"http://keybase.io/docs/proof_integration_guide\n")

# CHANGE ME
# ---------
identity_service_username = "squeekytween"
identity_service_password = "hunter2"
# This is the URL for the request that happens when a user click
# on the `Submit` or `Post` button on your site. It's super specific
# to your implementation, so we'll make a reasonable guess if you
# don't fill this in. But our guess is probably wrong, so just fill
# this in when you figure out what it should be.
proof_post_url = None

# This is the signature ID of a Reddit proof on a test user. It is a valid proof
# and so will pass the Keybase check if you're doing it on your side when these
# values get posted. For an explanation of why this is necessary, see:
# http://keybase.io/docs/proof_integration_guide#3-linking-user-profiles
kb_username = "marvin_gannon"
sig_id = "06dec904c22abaf6d4498ff7fc54a5b55759bbece2418b4a82b5ac5b1052466b0f"
# and here's another existing test user for you to play with (this one on twitter)
# using this you can test a user with multiple keybase usernames or an update to a signature
# kbuser: t_alice, sig_id: 8514ae2f9083a3c867318437845855f702a4154d1671a19cf274fb2e6b7dec7c0f

# Check that this script was called correctly
try:
    sys.argv[1]
except IndexError:
    print("Missing path to config. Please run like this: `python verify.py ./config.json`")
    sys.exit()

# Read in the config as json
config_path = sys.argv[1]
with open(config_path) as json_data:
    config = json.load(json_data)
print("1. Read in your config. Thanks. \nIf the script prompts you for additional "
"information, please feel free to stop the run, and go hardcode the values we're "
"looking for. They're all right at the top of the file. And if any of the requests "
"are failing, You may need to tweak some things to work with your specific site.\n")

# Set up valid creds for your service so we can create an authenticated session.
# We'll plop in our defaults, and if they're still there (please change them above), we'll
# prompt for new ones.
if identity_service_username == "squeekytween":
    identity_service_username = input(f"User ID of a valid account in {config['display_name']}: ")

# create a basic, logged in session
base_url = os.path.join("http://", config['domain'])
session = requests.session()

print(f"2. Created an authenticated session to {config['display_name']} for {identity_service_username}.")

######################################
# PROOF CREATION: http://keybase.io/docs/proof_integration_guide#2-1-proof-creation
######################################
# go to the prefill_url with the keybase username and signature values populated
prefill_url = config['prefill_url']
prefill_url = prefill_url.replace("%{kb_username}", kb_username, 1)
prefill_url = prefill_url.replace("%{username}", identity_service_username, 1)
prefill_url = prefill_url.replace("%{sig_hash}", sig_id, 1)
resp = session.get(prefill_url)
print(prefill_url)
assert resp.status_code == 200
assert kb_username in resp.text, "kb_username should be in the response text"
assert sig_id in resp.text, "kb_username should be in the response text"
print("3. Was able to GET the prefill_url, and naively, the response appears "
" to have what we expect. \nPlease take a look at this output and verify that "
"it's what you expect. There should be a submit button, and the keybase "
"username and sig_hash.")
print(resp.text)

input("\nPress enter when it looks right and you've followed the proof creation steps.")
# Now that we're done posting the proof, we no longer need the session.
# Let's delete it so we don't use it accidentally below.
del(session)

######################################
# PROOF CHECKING: http://keybase.io/docs/proof_integration_guide#2-2-proof-checking
######################################
# Now that the proof has been posted to your site, we'll check it.
check_url = config['check_url']
prefill_url = check_url.replace("%{username}", identity_service_username, 1)
headers = {"Accept": "application/json"}
resp = requests.get(prefill_url, headers=headers)
print(resp.status_code)
assert resp.status_code == 200, "expected checking the proof to be a 200"
response_data = resp.json()
# step into it using the check_path to find the data we care about
running_proofs = response_data
for step in config['check_path']:
    running_proofs = running_proofs[step]
expected_proofs = [{'kb_username': kb_username, 'sig_hash': sig_id}]
assert running_proofs == expected_proofs, "expected proofs from your check_url to match"
print("5. Got the proofs we were looking for. Everything checks out. :)")
