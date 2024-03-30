#!/bin/bash

# Проверяем, переданы ли порты в аргументах
if [ $# -eq 0 ]; then
    echo "Usage: $0 <port1> [<port2> ...]"
    exit 1
fi

# Перебираем каждый порт и запускаем Memcached сервер
for port in "$@"; do
    echo "Starting Memcached server on port $port..."
    memcached -p "$port" -d -vv >> "/home/soren/Projects/Otus_ProfPython/homework_9_MemcLoad/$port.log" 2>&1
    echo "Memcached server started on port $port."
done

exit 0
