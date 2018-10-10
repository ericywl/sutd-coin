#! /bin/bash

print_usage() { echo "$0 usage:" && grep " .)\ #" $0; exit 0; }
IDS=()

finish() {
  sudo kill $(jobs -p)
  kill 0;
  exit;
}

trap finish SIGHUP SIGINT SIGTERM
while getopts ":hm:s:f" flag; do
  case $flag in
    m) # Set miner count.
      miner_count=$OPTARG ;;
    s) # Set SPV client count.
      spv_client_count=$OPTARG ;;
    f) # enable fuckers
      fucker_count=1 ;;
    h | *) # Display help.
      print_usage ;;
  esac
done

if [ $OPTIND -eq 1 ];
  then print_usage;
else
  if [ -z "$miner_count" ]; then
    echo "Please set miners"
  else
    python trusted_server.py &
    IDS+=($!)
    sleep 3

    if [ -n "$spv_client_count" ]; then
      for i in $(seq 1 $spv_client_count)
        do
          sleep 2
          python spv_client.py $(($i + 22345)) &
          IDS+=($!)
        done
    fi

    for i in $(seq 1 $miner_count)
      do
        sleep 2
        python miner.py $(($i + 12345)) &
        IDS+=($!)
      done

    if [ -n "$fucker_count" ]; then
      sudo nice -n -15 python adversary.py $((33345)) &
      IDS+=($!)
    fi
  fi
fi

echo "Press [CTRL+C] to stop.."
while true
do
	sleep 1
done
