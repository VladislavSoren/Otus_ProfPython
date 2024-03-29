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
from multiprocessing import Pool
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


def get_parsing_indexes(start_ind, end_ind, count_bot):
    count_record = (end_ind - start_ind)
    print(count_record)
    part = count_record / count_bot
    part = math.ceil(part)
    tuple_indexes = range(start_ind, start_ind + part * (count_bot + 1), part)
    print(tuple_indexes)
    return tuple_indexes


def get_key_and_packed(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    packed = ua.SerializeToString()
    return key, packed


def load_data_by_chunk(connection: RetryingClient, chunk_dict: dict):
    try:
        failed_keys = connection.set_many(chunk_dict)
    except Exception as e:
        logging.exception("Cannot write to memc %s: %s" % (connection.server, e))
        return False
    else:
        return failed_keys


def load_data_for_all_servers(options, connections_memc, chunk_dicts):
    connection = connections_memc[options.idfa_name]
    failed_keys_idfa = load_data_by_chunk(connection, chunk_dicts[options.idfa_name])

    connection = connections_memc[options.gaid_name]
    failed_keys_gaid = load_data_by_chunk(connection, chunk_dicts[options.gaid_name])

    connection = connections_memc[options.adid_name]
    failed_keys_adid = load_data_by_chunk(connection, chunk_dicts[options.adid_name])

    connection = connections_memc[options.dvid_name]
    failed_keys_dvid = load_data_by_chunk(connection, chunk_dicts[options.dvid_name])

    return failed_keys_idfa, failed_keys_gaid, failed_keys_adid, failed_keys_dvid


def save_in_mem_cache(fd, options):
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


    chunk_dicts = {
        options.idfa_name: {},
        options.gaid_name: {},
        options.adid_name: {},
        options.dvid_name: {},
    }

    count = 0
    errors = 0
    processed = 0

    for line in fd:

        line = line.strip()
        if not line:
            continue
        appsinstalled = parse_appsinstalled(line)
        if not appsinstalled:
            errors += 1
            continue
        # connection = connections_memc.get(appsinstalled.dev_type)
        # if not connection:
        #     errors += 1
        #     logging.error("Unknow device type: %s" % appsinstalled.dev_type)
        #     continue

        key, packed = get_key_and_packed(appsinstalled)

        if appsinstalled.dev_type == options.idfa_name:
            chunk_dicts[options.idfa_name][key] = packed
        elif appsinstalled.dev_type == options.gaid_name:
            chunk_dicts[options.gaid_name][key] = packed
        elif appsinstalled.dev_type == options.adid_name:
            chunk_dicts[options.adid_name][key] = packed
        elif appsinstalled.dev_type == options.dvid_name:
            chunk_dicts[options.dvid_name][key] = packed

        # Increase iter chunk count
        count += 1

        # check if we reach chunk_size
        if count == options.chunk_size:
            failed_keys_idfa, failed_keys_gaid, failed_keys_adid, failed_keys_dvid = load_data_for_all_servers(
                options, connections_memc, chunk_dicts
            )
            errors += sum(
                [len(failed_keys_idfa), len(failed_keys_gaid), len(failed_keys_adid), len(failed_keys_dvid)])
            processed += count

            # zeroing out chunk_dicts for new data
            chunk_dicts[options.idfa_name] = {}
            chunk_dicts[options.gaid_name] = {}
            chunk_dicts[options.adid_name] = {}
            chunk_dicts[options.dvid_name] = {}

            # zeroing out count then we reach chunk_size
            count = 0

    else:
        failed_keys_idfa, failed_keys_gaid, failed_keys_adid, failed_keys_dvid = load_data_for_all_servers(
            options, connections_memc, chunk_dicts
        )
        errors += sum(
            [len(failed_keys_idfa), len(failed_keys_gaid), len(failed_keys_adid), len(failed_keys_dvid)])
        processed += count

        err_rate = float(errors) / processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))

    return err_rate

@log_time(logger=parsing_logger, description='<memc_load_multi>')
def main(options):

    workers_number = options.workers

    for fn in glob.iglob(options.pattern):

        logging.info('Processing %s' % fn)

        fd = gzip.open(fn)
        fd_list = list(fd)

        parsing_indexes = get_parsing_indexes(0, len(fd_list), workers_number)

        # Prepare data for workers
        fds = [fd_list[parsing_indexes[bot_i]:parsing_indexes[bot_i + 1]] for bot_i in range(workers_number)]

        # Processes
        with Pool(processes=workers_number) as p:
            l1 = [(fd_w, options) for fd_w in fds]
            print(p.starmap(save_in_mem_cache, l1))

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
    op.add_option("--idfa_name", action="store", default="idfa")
    op.add_option("--gaid_name", action="store", default="gaid")
    op.add_option("--adid_name", action="store", default="adid")
    op.add_option("--dvid_name", action="store", default="dvid")
    op.add_option("--idfa", action="store", default="127.0.0.1:11215")
    op.add_option("--gaid", action="store", default="127.0.0.1:11216")
    op.add_option("--adid", action="store", default="127.0.0.1:11217")
    op.add_option("--dvid", action="store", default="127.0.0.1:11218")
    op.add_option("--chunk_size", action="store", default=100)
    op.add_option("--workers", action="store", default=20)
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
