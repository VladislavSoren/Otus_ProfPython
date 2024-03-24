#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
import os
import gzip
import sys
import glob
import logging
import collections
import threading
import time
from functools import wraps
from optparse import OptionParser
from threading import Thread

# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
# import memcache
from pymemcache.client.base import Client
from pymemcache.client.retrying import RetryingClient
from pymemcache.exceptions import MemcacheUnexpectedCloseError

import logging

# Параметры логирования
logging.basicConfig(filename="log_memc_load.log",
                    filemode="a",
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
parsing_logger = logging.getLogger(__name__)


class threadsafe_iter:
    """Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """

    def __init__(self, it):
        self.it = it
        # self.lock = threading.Lock()
        self.lock = threading.RLock()

    def __iter__(self):
        return self

    def __next__(self):
        with self.lock:
            return self.it.__next__()


# Функция декоратор замера времени выполнения функции
def log_time(logger, description=''):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            logger.info(f'Start parsing {description} ({func.__name__})')
            result = func(*args, **kwargs)
            end = time.time()
            exec_time = round(end - start, 10)
            logger.info(f'Parsing time {description} ({func.__name__}): {exec_time}s')
            return result

        return wrapper

    return inner


NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    # os.rename(path, os.path.join(head, "." + fn))


# @log_time(logger=parsing_logger, description='<insert_appsinstalled>')
def insert_appsinstalled(connection, appsinstalled, dry_run=False):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    try:
        if dry_run:
            logging.debug("%s - %s -> %s" % (str(connection.server), key, str(ua).replace("\n", " ")))
        else:
            resp = connection.set(key, packed)
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (connection.server, e))
        return False
    else:
        return True


# @log_time(logger=parsing_logger, description='<parse_appsinstalled>')
def parse_appsinstalled(line):
    line_parts = line.decode().strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)

    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


@log_time(logger=parsing_logger, description='<memc_load_multi>')
def main(options):
    connections_memc = {
        "idfa": RetryingClient(
            Client(options.idfa, connect_timeout=3, timeout=1),
            attempts=3,
            retry_delay=0.01,
            retry_for=[MemcacheUnexpectedCloseError]),
        "gaid": RetryingClient(
            Client(options.gaid, connect_timeout=3, timeout=1),
            attempts=3,
            retry_delay=0.01,
            retry_for=[MemcacheUnexpectedCloseError]),
        "adid": RetryingClient(
            Client(options.adid, connect_timeout=3, timeout=1),
            attempts=3,
            retry_delay=0.01,
            retry_for=[MemcacheUnexpectedCloseError]),
        "dvid": RetryingClient(
            Client(options.dvid, connect_timeout=3, timeout=1),
            attempts=3,
            retry_delay=0.01,
            retry_for=[MemcacheUnexpectedCloseError]),
    }

    workers = options.workers

    for fn in glob.iglob(options.pattern):

        logging.info('Processing %s' % fn)

        fd = gzip.open(fn)
        fd_safe_iter = threadsafe_iter(fd)

        def save_in_mem_cache(bot_i):

            errors = 0
            processed = 0

            while True:

                try:
                    line = next(fd_safe_iter)
                except StopIteration as e:
                    logging.error(f"Error: {e}")
                    break
                else:
                    line = line.strip()
                    if not line:
                        continue

                    appsinstalled = parse_appsinstalled(line)

                    if not appsinstalled:
                        errors += 1

                    connection = connections_memc.get(appsinstalled.dev_type)

                    if not connection:
                        errors += 1
                        logging.error("Unknow device type: %s" % appsinstalled.dev_type)

                    ok = insert_appsinstalled(connection, appsinstalled, options.dry)
                    if ok:
                        processed += 1
                    else:
                        errors += 1

            err_rate = float(errors) / processed
            if err_rate < NORMAL_ERR_RATE:
                logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
            else:
                logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))

        # Потоки
        # Формирование группы потоков
        Threads_VK = [
            Thread(target=save_in_mem_cache, args=(
                bot_i,)) for bot_i in range(workers)
        ]

        # .........Запускаем потоки (начинаем нормализацию).........
        for t in Threads_VK:
            t.start()

        # Проверяем живы ли потоки
        for t in Threads_VK:
            if t.is_alive():
                logging.info(f'Thread №{t} ALIVE')
            else:
                logging.info(f'Thread №{t} DEAD')

        # .................Ждём завершения всех потоков
        for t in Threads_VK:
            t.join()

        # .................Проверяем завершение всех потоков
        for t in Threads_VK:
            if t.is_alive():
                logging.info(f'Thread №{t} ALIVE')
            else:
                logging.info(f'Thread №{t} DEAD')

        fd.close()
        dot_rename(fn)


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="./data/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:11215")
    op.add_option("--gaid", action="store", default="127.0.0.1:11216")
    op.add_option("--adid", action="store", default="127.0.0.1:11217")
    op.add_option("--dvid", action="store", default="127.0.0.1:11218")
    op.add_option("--workers", action="store", default=2)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
