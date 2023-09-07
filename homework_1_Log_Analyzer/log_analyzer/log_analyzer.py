#!/usr/bin/env python
# -*- coding: utf-8 -*-
import bz2
import datetime
import os
import gzip
from pathlib import Path
from string import Template
import re

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '  
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def get_time_str(value):
    return re.search(r'\d{8}', value)[0]


def get_time_str_in_proper_format(value):
    time_str = get_time_str(value)
    time_date = datetime.datetime.strptime(time_str, '%Y%m%d').date()
    time_str_proper = str(time_date).replace('-', '.')
    return time_str_proper


def sort_condition(url_stat_dict):
    return url_stat_dict['time_sum']


def main():
    # Получаем имя файла с самой свежей датой
    log_file_names = os.listdir(config['LOG_DIR'])
    log_file_name_last = max(log_file_names, key=get_time_str)

    # Получаем дату из имени файла в формате "2017.06.30"
    file_time = get_time_str_in_proper_format(log_file_name_last)

    # Чтение логфайла
    path_log_file = str(Path('log') / log_file_name_last)
    if path_log_file.endswith(".gz"):
        logfile = gzip.open(path_log_file)
    elif path_log_file.endswith(".bz2"):
        logfile = bz2.BZ2File(path_log_file)
    else:
        logfile = open(path_log_file)

    # Парсинг логов
    lineformat = re.compile(
        r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) -  - \[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\] (\"(GET|POST) )(?P<url>.+)(http\/[1-2]\.[0-9]") (?P<statuscode>\d{3}) (?P<bytessent>\d+) (?P<refferer>-|"([^"]+)") (["](?P<useragent>[^"]+)["]) (?P<forwarded_for>"([^"]+)") (?P<request_id>"([^"]+)") (?P<rb_user>"([^"]+)") (?P<request_time>\d+\.\d{3})""",
        re.IGNORECASE)

    urls_list = []
    requests_time_list = []
    success_count = 0
    fail_count = 0
    #! можно прикрутить сюда генератор
    for row_bytes in logfile.readlines():
        row_str = row_bytes.decode('utf-8')

        data = re.search(lineformat, row_str)
        if data:
            success_count += 1
            datadict = data.groupdict()
            urls_list.append(datadict["url"])
            requests_time_list.append(float(datadict["request_time"]))
        else:
            fail_count += 1

    logfile.close()

    # Группируем урлы
    urls_dict = {}
    requests_time_list = [float(i) for i in requests_time_list]
    for url, request_time in zip(urls_list, requests_time_list):

        # создание ссылки в словаре
        if url not in urls_dict:
            urls_dict[url] = list([])

        urls_dict[url] += [request_time]

    # Расчёт статистик для отчёта
    all_requests_count = len(requests_time_list)
    all_requests_sum = sum(requests_time_list)
    table_json = []
    for url, request_times_list in urls_dict.items():
        row_json = {
            'url': url,
            'count': len(request_times_list),
            'count_perc': (len(request_times_list) / all_requests_count) * 100,
            'time_sum': sum(request_times_list),
            'time_perc': (sum(request_times_list) / all_requests_sum) * 100,
            'time_avg': sum(request_times_list) / len(request_times_list),
            'time_max': max(request_times_list),
            'time_med': sorted(request_times_list)[0],
        }
        table_json.append(row_json)

    # сортировка словарей в списке по time_sum
    table_json = sorted(table_json, key=sort_condition, reverse=True)
    table_json = table_json[:config['REPORT_SIZE']]

    # Подгрузка report шаблона
    path_report_base_file = str(Path('reports') / 'report.html')
    with open(path_report_base_file, 'r') as f:
        report_base_content = f.read()

    # подмена table_json в шаблоне
    default_template = Template(report_base_content)
    report_new = default_template.safe_substitute({'table_json': table_json})
    pass

    # Сохраняем report
    path_report_base_file = str(Path('reports') / f'report-{file_time}.html')
    with open(path_report_base_file, 'w') as f:
        f.write(report_new)


if __name__ == "__main__":
    main()
