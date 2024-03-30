import collections
import glob
import gzip
import logging

from pymemcache.client.base import Client

from homework_9_MemcLoad import appsinstalled_pb2

AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


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


def get_key_and_packed(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    packed = ua.SerializeToString()
    return key, packed


def main(check):
    if check == "all":
        test_path = "./data/appsinstalled/*.tsv.gz"
    elif check == "100":
        test_path = "./data/appsinstalled/*100.tsv.gz"
    elif check == "100k":
        test_path = "./data/appsinstalled/*100k.tsv.gz"

    # group1
    gr1_c1 = Client(('localhost', 11211))
    gr1_c2 = Client(('localhost', 11212))
    gr1_c3 = Client(('localhost', 11213))
    gr1_c4 = Client(('localhost', 11214))

    res_gr1_c1 = []
    res_gr1_c2 = []
    res_gr1_c3 = []
    res_gr1_c4 = []

    # group2
    gr2_c1 = Client(('localhost', 11215))
    gr2_c2 = Client(('localhost', 11216))
    gr2_c3 = Client(('localhost', 11217))
    gr2_c4 = Client(('localhost', 11218))

    res_gr2_c1 = []
    res_gr2_c2 = []
    res_gr2_c3 = []
    res_gr2_c4 = []

    for fn in glob.iglob(test_path):
        fd = gzip.open(fn)

        for n, line in enumerate(fd):

            if n % 5000 == 0:
                appsinstalled = parse_appsinstalled(line)
                key_sys = appsinstalled.dev_type
                key, packed = get_key_and_packed(appsinstalled)

                # check c1 ("idfa")
                if key_sys == "idfa":
                    try:
                        result = gr1_c1.get(key)
                        if result == packed:
                            res_gr1_c1.append(True)
                        else:
                            res_gr1_c1.append(False)
                    except Exception as e:
                        res_gr1_c1.append(False)

                    try:
                        result = gr2_c1.get(key)
                        if result == packed:
                            res_gr2_c1.append(True)
                        else:
                            res_gr2_c1.append(False)
                    except Exception as e:
                        res_gr2_c1.append(False)

                # check c2 ("gaid")
                if key_sys == "gaid":
                    try:
                        result = gr1_c2.get(key)
                        if result == packed:
                            res_gr1_c2.append(True)
                        else:
                            res_gr1_c2.append(False)
                    except Exception as e:
                        res_gr1_c2.append(False)

                    try:
                        result = gr2_c2.get(key)
                        if result == packed:
                            res_gr2_c2.append(True)
                        else:
                            res_gr2_c2.append(False)
                    except Exception as e:
                        res_gr2_c2.append(False)

                # check c3 ("adid")
                if key_sys == "adid":
                    try:
                        result = gr1_c3.get(key)
                        if result == packed:
                            res_gr1_c3.append(True)
                        else:
                            res_gr1_c3.append(False)
                    except Exception as e:
                        res_gr1_c3.append(False)

                    try:
                        result = gr2_c3.get(key)
                        if result == packed:
                            res_gr2_c3.append(True)
                        else:
                            res_gr2_c3.append(False)
                    except Exception as e:
                        res_gr2_c3.append(False)

                # check c4 ("dvid")
                if key_sys == "dvid":
                    try:
                        result = gr1_c4.get(key)
                        if result == packed:
                            res_gr1_c4.append(True)
                        else:
                            res_gr1_c4.append(False)
                    except Exception as e:
                        res_gr1_c4.append(False)

                    try:
                        result = gr2_c4.get(key)
                        if result == packed:
                            res_gr2_c4.append(True)
                        else:
                            res_gr2_c4.append(False)
                    except Exception as e:
                        res_gr2_c4.append(False)

        if all(res_gr1_c1) and all(res_gr1_c2) and all(res_gr1_c3) and all(res_gr1_c4):
            print("localhost:11211/11214 - Success")
        else:
            print("localhost:11211/11214 - Fail")

        if all(res_gr2_c1) and all(res_gr2_c2) and all(res_gr2_c3) and all(res_gr2_c4):
            print("localhost:11215/11218 - Success")
        else:
            print("localhost:11215/11218 - Fail")


if __name__ == '__main__':
    main(check="100k")
