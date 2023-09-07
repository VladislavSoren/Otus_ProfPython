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

    # extract content
    # file_content_byte = logfile.read(10 * 1024)
    # file_content_str = file_content_byte.decode('utf-8')

    # Закрываем файл логов
    # logfile.close()

    # Парсинг логов
    # log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
    #                     '$status $body_bytes_sent "$http_referer" '
    #                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
    #                     '$request_time';

    lineformat = re.compile(
        r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) -  - \[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\] (\"(GET|POST) )(?P<url>.+)(http\/[1-2]\.[0-9]") (?P<statuscode>\d{3}) (?P<bytessent>\d+) (?P<refferer>-|"([^"]+)") (["](?P<useragent>[^"]+)["]) (?P<forwarded_for>"([^"]+)") (?P<request_id>"([^"]+)") (?P<rb_user>"([^"]+)") (?P<request_time>\d+\.\d{3})""",
        re.IGNORECASE)

    '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390'

    for row_bytes in logfile.readlines(20 * 1024):
        row_str = row_bytes.decode('utf-8')

        data = re.search(lineformat, row_str)
        if data:
            datadict = data.groupdict()
            ip = datadict["ipaddress"]
            datetimestring = datadict["dateandtime"]
            url = datadict["url"]
            bytessent = datadict["bytessent"]
            referrer = datadict["refferer"]
            useragent = datadict["useragent"]
            status = datadict["statuscode"]
            method = data.group(6)


    # logfile.close()

    # # формирование отчётной таблицы "table_json"
    #
    # # Подгрузка report шаблона
    #
    # # подмена table_json в шаблоне
    # default_template = Template(file_content_str)
    # updated_template = default_template.safe_substitute({'table_json': 1, 'what': 2})
    #
    # # Сохраняем report
    #
    # # * Рендерим репорт


if __name__ == "__main__":
    main()

    os.system("ls -l")
