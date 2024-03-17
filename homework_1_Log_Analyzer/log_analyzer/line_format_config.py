"""
####### Структура логов файла #######
log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
                    '$request_time';
"""

import re

LINE_LOG_FORMAT = re.compile(
    r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (?P<remote_user>(-|\S+))  - \[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\] (\"(GET|POST) )(?P<url>.+)(http\/[1-2]\.[0-9]") (?P<statuscode>\d{3}) (?P<bytessent>\d+) (?P<refferer>-|"([^"]+)") (["](?P<useragent>[^"]+)["]) (?P<forwarded_for>"([^"]+)") (?P<request_id>"([^"]+)") (?P<rb_user>"([^"]+)") (?P<request_time>\d+\.\d{3})""",
    re.IGNORECASE,
)


# В формате с переносом строк LINE_LOG_FORMAT НЕ отрабатывает

# LINE_LOG_FORMAT = re.compile(
# r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})
# (?P<remote_user>(-|\S+))  - \[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\]
# (\"(GET|POST) )(?P<url>.+)(http\/[1-2]\.[0-9]") (?P<statuscode>\d{3}) (?P<bytessent>\d+)
# (?P<refferer>-|"([^"]+)") (["](?P<useragent>[^"]+)["]) (?P<forwarded_for>"([^"]+)")
# (?P<request_id>"([^"]+)") (?P<rb_user>"([^"]+)") (?P<request_time>\d+\.\d{3})""",
#     re.IGNORECASE,
# )
