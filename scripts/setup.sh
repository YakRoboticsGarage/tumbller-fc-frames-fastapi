# Setup of the repository runtime environment

set -eu

if [[ ! -x /usr/bin/apt-get ]]
then
  >&2 echo "Exiting: This script supports Debian-based systems only and needs apt-get (used with sudo)"
  exit 1
fi

#
# System wide used dependencies
#
if [[ ! -x /usr/bin/screen ]]
then
  sudo -k $(/usr/bin/apt-get update && /usr/bin/apt-get install --yes screen)
fi


#
# Main code, Python dependencies
#
if [[ ! -d venv ]]
then
  python3 -mvenv venv
fi
source venv/bin/activate
pip install --upgrade .


#
# Prepare the environment
#
if [[ ! -f .env ]]
then
  cp .env.template .env
  echo 'Mini App configuration file ready in `.env`. Please edit as needed'
fi


#
# Inform
#
echo "Setup complete"
echo "Next steps: Run the Mini App with bin/miniapp. Optionaly run the fake rover with bin/fakerover"
