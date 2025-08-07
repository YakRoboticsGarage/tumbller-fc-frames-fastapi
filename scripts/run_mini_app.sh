# Run the Mini App server

set -e

root_dir=$(realpath $0 | rev | cut -d / -f 3- | rev)

if [[ ! -d "${root_dir}/venv" ]]
then
  >&2 echo "Setup requirements no found. Perhaps need to run scripts/setup.sh?"
  exit 1
fi

pushd $root_dir
  source venv/bin/activate
  pushd fastapi-frames-server
    uvicorn main:app --host 0.0.0.0 --port 8080 --reload
  popd
popd
