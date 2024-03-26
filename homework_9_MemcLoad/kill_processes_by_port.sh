#!/bin/bash

# Проверяем, переданы ли порты в аргументах
if [ $# -eq 0 ]; then
    echo "Usage: $0 <port1> [<port2> ...]"
    exit 1
fi

# Получаем список портов из аргументов
ports=("$@")

# Перебираем каждый порт
for port in "${ports[@]}"; do
    echo "Searching processes listening on port $port..."

    # Получаем PID процессов, прослушивающих заданный порт
    pids=$(lsof -t -i :$port)

    # Проверяем, есть ли процессы, прослушивающие заданный порт
    if [ -z "$pids" ]; then
        echo "No processes found listening on port $port"
    else
        echo "Processes found listening on port $port: $pids"

        # Убиваем найденные процессы
        echo "Killing processes..."
        sudo kill -9 $pids

        echo "Processes killed."
    fi
done

exit 0
