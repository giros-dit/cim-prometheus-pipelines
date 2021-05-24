
CONTAINER=$1
EVENTS=$2

while true; do docker stats $CONTAINER --no-stream --format "{{ .CPUPerc }},{{ .MemPerc }}" | tee --append results/cpu_memory/$CONTAINER/${CONTAINER}_${EVENTS}.csv; sleep 1; done