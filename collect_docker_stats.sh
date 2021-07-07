
CONTAINER=$1
PLATFORM=$2
EVENTS=$3

mkdir -p results/cpu_memory/${PLATFORM}
touch results/cpu_memory/${PLATFORM}/${CONTAINER}_${EVENTS}.csv
while true; do docker stats $CONTAINER --no-stream --format "{{ .CPUPerc }},{{ .MemPerc }}" | tee --append results/cpu_memory/${PLATFORM}/${CONTAINER}_${EVENTS}.csv; sleep 1; done
