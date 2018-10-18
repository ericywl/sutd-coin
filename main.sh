#! /bin/bash
IDS=()

print_usage() {
  echo "$0 usage:" && grep " .)\ #" $0;
  exit 0;
}

finish() {
  sudo kill $(jobs -p)
  kill 0;
  rm mine_lock
  exit;
}

if [[ $UID != 0 ]]; then
  echo "Please run script with sudo (for nice):"
  echo "sudo $0 $*"
  exit 1
fi

trap finish SIGHUP SIGINT SIGTERM
while getopts ":hm:s:fd" flag; do
  case $flag in
    m) # Set miner count.
      miner_count=$OPTARG ;;
    s) # Set SPV client count.
      spv_client_count=$OPTARG ;;
    d) # Enable double spend.
      double_spend=true ;;
    f) # enable selfish miner
      selfish=true ;;
    h | *) # Display help.
      print_usage ;;
  esac
done

if [ $OPTIND -eq 1 ]; then
  print_usage;
  exit 1;
elif [ -z "$miner_count" ]; then
    echo "Please set miners";
    exit 1;
else
  python src/trusted_server.py &
  IDS+=($!)
  sleep 3

  if [ -n "$spv_client_count" ]; then
    for i in $(seq 1 $spv_client_count)
      do
        python src/spv_client.py $(($i + 22345)) &
        IDS+=($!)
        sleep 1
      done
  fi

  for i in $(seq 1 $miner_count)
    do
      python src/miner.py $(($i + 12345)) $double_spend $selfish &
      IDS+=($!)
      sleep 1
    done

  if [ -n "$double_spend" ]; then
    python src/double_spend.py $((33345)) "VENDOR" &
    sleep 1
    sudo nice -n -3 python src/double_spend.py $((33346)) "MINER" &
    sleep 1
    python src/double_spend.py $((33347)) "SPV" &
    sleep 1
  elif [ -n "$selfish" ]; then
    sudo nice -n -3 python src/selfish.py $((33345)) &
    IDS+=($!)
    sleep 1
  fi
fi

sleep 5
touch mine_lock

echo "Press [CTRL+C] to stop.."
while true
do
	sleep 1
done
