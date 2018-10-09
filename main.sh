#! /bin/bash

print_usage() {
  printf "Usage: ..."
}

while getopts 'm:s:' flag; do
  case "${flag}" in
    m) miner_count=$OPTARG ;;
    s) spv_client_count=$OPTARG ;;
    *) print_usage
       exit 1 ;;
  esac
done