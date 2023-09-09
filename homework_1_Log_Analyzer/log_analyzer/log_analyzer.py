#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
####### Структура логов файла #######
log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
                    '$request_time';
"""

import bz2
import datetime
import json
import logging
import os
import gzip
import sys
import time
from functools import wraps
from pathlib import Path
from string import Template
import re
import argparse

system_paths = sys.path
cur_work_dir = os.getcwd()

# Парсим данные командной строки
parser = argparse.ArgumentParser(description='Log parser')
parser.add_argument(
    '--config',
    type=str,
    default='config.json',
    help='Enter path of config file'
)
args = parser.parse_args()

# Подгружаем внешний конфиг
with open(args.config, encoding='utf-8') as f:
    loaded_config = json.load(f)

# конфиг по умолчанию
config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LINE_LOG_FORMAT": re.compile(
        r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (?P<remote_user>(-|\S+))  - \[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\] (\"(GET|POST) )(?P<url>.+)(http\/[1-2]\.[0-9]") (?P<statuscode>\d{3}) (?P<bytessent>\d+) (?P<refferer>-|"([^"]+)") (["](?P<useragent>[^"]+)["]) (?P<forwarded_for>"([^"]+)") (?P<request_id>"([^"]+)") (?P<rb_user>"([^"]+)") (?P<request_time>\d+\.\d{3})""",
        re.IGNORECASE),
    "PARSING_ERROR_LIMIT_PERC": 10,
    "PROGRESS_INFORM_MODE": 1,
    "LOGS_REPORT_PATH": str(Path('logs_report') / "py_log.log"),
    # "LOGS_REPORT_PATH": None,
}
# обновляем дефолтный конфиг контентом из подгруженного
config.update(loaded_config)

# Параметры логирования
logging.basicConfig(filename=config.get('LOGS_REPORT_PATH', None),
                    # if filename == None -> logs in stdout
                    filemode="w",
                    format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d%H:%M:%S',
                    level=logging.INFO)
parsing_logger = logging.getLogger(__name__)


# Статусы выполнения
class Status:
    success = 'Success'
    failed = 'Failed'


# Декоратор замера времени выполнения функции
def log_time(logger, description=''):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            logger.info(f'Start {description} ({func.__name__})')
            result = func(*args, **kwargs)
            end = time.time()
            exec_time = round(end - start, 2)
            logger.info(f'Time {description} ({func.__name__}): {exec_time}s')
            return result

        return wrapper

    return inner


def get_time_str(value):
    return re.search(r'\d{8}', value)[0]


def get_time_str_in_proper_format(value):
    time_str = get_time_str(value)
    time_date = datetime.datetime.strptime(time_str, '%Y%m%d').date()
    time_str_proper = str(time_date).replace('-', '.')
    return time_str_proper


# Получаем имя файла с самой свежей датой
def get_log_file_name_last(config_file):
    log_file_names = os.listdir(config_file['LOG_DIR'])
    log_file_name_last = max(log_file_names, key=get_time_str)
    return log_file_name_last


def sort_condition(url_stat_dict):
    return url_stat_dict['time_sum']


def get_logfile_object(path_log_file):
    if path_log_file.endswith(".gz"):
        logfile = gzip.open(path_log_file)
    elif path_log_file.endswith(".bz2"):
        logfile = bz2.BZ2File(path_log_file)
    else:
        logfile = open(path_log_file, 'rb')

    return logfile


@log_time(logger=parsing_logger)
def count_lines(path_log_file):
    logfile = get_logfile_object(path_log_file)
    num_lines = sum(1 for _ in logfile)
    logfile.close()
    return num_lines


def progress_inform(done_perc, done_perc_flags):
    for perc_point, done_flag in done_perc_flags.items():
        if done_perc > perc_point and not done_flag:
            done_perc_flags[perc_point] = True
            print(f'{perc_point}% done')


# парсинг логов
@log_time(logger=parsing_logger)
def parsing_logs(path_log_file, config_file):
    num_lines = count_lines(path_log_file)
    urls_list = []
    requests_time_list = []
    status_counters = {
        'success_count': 0,
        'fail_count': 0,
    }
    done_perc_flags = {
        10: False, 20: False, 30: False, 40: False, 50: False,
        60: False, 70: False, 80: False, 90: False
    }

    logfile = get_logfile_object(path_log_file)

    parsing_logger.info(f'Parsing is started')
    for row_bytes in logfile:
        row_str = row_bytes.decode('utf-8')

        data = re.search(config_file['LINE_LOG_FORMAT'], row_str)
        if data:
            status_counters['success_count'] += 1
            datadict = data.groupdict()
            urls_list.append(datadict["url"])
            requests_time_list.append(float(datadict["request_time"]))
        else:
            status_counters['fail_count'] += 1
            parsing_logger.error(f'Parsing error for row: {row_str}')

        # progress inform
        if config_file['PROGRESS_INFORM_MODE']:
            done_perc = ((status_counters['success_count'] + status_counters['fail_count']) / num_lines) * 100
            progress_inform(done_perc, done_perc_flags)

    logfile.close()
    parsing_logger.info(f'Parsing is finished')
    return urls_list, requests_time_list, status_counters


def get_grouped_urls_dict(urls_list, requests_time_list):
    urls_dict = {}
    requests_time_list = [float(i) for i in requests_time_list]
    for url, request_time in zip(urls_list, requests_time_list):

        # создание ссылки в словаре
        if url not in urls_dict:
            urls_dict[url] = list([])

        urls_dict[url] += [request_time]
    return urls_dict


@log_time(logger=parsing_logger)
def get_table_json_stat(urls_dict, requests_time_list):
    all_requests_count = len(requests_time_list)
    all_requests_sum = sum(requests_time_list)
    table_json = []
    for url, request_times_list in urls_dict.items():
        row_json = {
            'url': url,
            'count': round(len(request_times_list), 3),
            'count_perc': round(((len(request_times_list) / all_requests_count) * 100), 3),
            'time_sum': round(sum(request_times_list), 3),
            'time_perc': round(((sum(request_times_list) / all_requests_sum) * 100), 3),
            'time_avg': round((sum(request_times_list) / len(request_times_list)), 3),
            'time_max': round(max(request_times_list), 3),
            'time_med': round(sorted(request_times_list)[0], 3),
        }
        table_json.append(row_json)

    return table_json


def get_formatted_report(table_json, config_file):
    table_json = sorted(table_json, key=sort_condition, reverse=True)
    table_json = table_json[:config_file['REPORT_SIZE']]

    return table_json


@log_time(logger=parsing_logger)
def save_report(table_json, file_time, config_file) -> None:
    # Получаем шаблон
    path_report_base_file = str(Path(config_file['REPORT_DIR']) / 'report.html')
    with open(path_report_base_file, 'r') as f:
        report_base_content = f.read()

    # Подменяем table_json в шаблоне
    default_template = Template(report_base_content)
    report_new = default_template.safe_substitute({'table_json': table_json})

    # Сохраняем report
    path_report_base_file = str(Path(config_file['REPORT_DIR']) / f'report-{file_time}.html')
    with open(path_report_base_file, 'w') as f:
        f.write(report_new)


def get_fatal_error_status(status_counters, config_file):
    all_rows_count = status_counters['success_count'] + status_counters['fail_count']
    fail_perc = (status_counters['fail_count'] / all_rows_count) * 100
    limit = config_file['PARSING_ERROR_LIMIT_PERC']
    if fail_perc > limit:
        parsing_logger.error(f'Error limit is over, {fail_perc} > {limit}')
        return Status.failed
    return Status.success


@log_time(logger=parsing_logger)
def main(config_file):
    log_file_name_last = get_log_file_name_last(config_file)

    # Получаем дату из имени файла в формате "2017.06.30"
    file_time = get_time_str_in_proper_format(log_file_name_last)

    # Получаем данные для формирования отчёта и счётчики качества парсинга
    path_log_file = str(Path(config_file['LOG_DIR']) / log_file_name_last)
    urls_list, requests_time_list, status_counters = parsing_logs(path_log_file, config_file)

    # В случае превышения ошибок при парсинге поднимаем SystemError
    status = get_fatal_error_status(status_counters, config_file)
    if status == Status.failed:
        parsing_logger.error(f'Program is stopped due to fatal error!')
        raise SystemError('Error limit during parsing exceeded')
        # sys.exit()

    # Группируем урлы
    urls_dict = get_grouped_urls_dict(urls_list, requests_time_list)

    # Получение полного статистического отчёта
    table_json = get_table_json_stat(urls_dict, requests_time_list)

    # Получение отчёта, приведённого к нужному формату (готовый отчёт)
    table_json = get_formatted_report(table_json, config_file)

    # Сохранение отчёта
    save_report(table_json, file_time, config_file)


if __name__ == "__main__":
    try:
        main(config)
    except Exception as e:
        logging.exception(f'Неожиданная ошибка {e}')
