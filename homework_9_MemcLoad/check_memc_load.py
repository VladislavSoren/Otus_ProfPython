from pymemcache.client.base import Client

# 100
keys_check = [
    'idfa:26658aeb53c5c03222c631843cdd7332',
    'idfa:e7e1a50c0ec2747ca56cd9e1558c0d7c',
    'dvid:7f88207fd495875f6c6e701e82dd7f73',
    'gaid:be18f8dd478dfc308bd9537d3cf64f6f',
    'adid:9bee278471a5eb9de39f0e44ffa7fd09',
    'gaid:3bb9d849a4626860f58c4da2086f7412',
]

# 100k
keys_check_100k = [
    'gaid:9875b2f670a2eb6920f72039162937a0',
    'dvid:f6491509523d4a57cf1e16461ac0c11d',
    'adid:f38c2729f83d81914227bb25619f1ab0',
    'idfa:b608692d7647d2a8e1d21e0b494ae534',
    'gaid:d138f08a3bad4ab21bde418a598a59d9',
    'adid:81718802cc9ec3740c86e643b9fd0722',
]


def main(check):
    if check == "100k":
        keys_check.extend(keys_check_100k)

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

    for key in keys_check:

        key_sys = key.split(":")[0]

        # check c1 ("idfa")
        if key_sys == "idfa":
            try:
                result = gr1_c1.get(key)
                if result:
                    res_gr1_c1.append(True)
                else:
                    res_gr1_c1.append(False)
            except Exception as e:
                res_gr1_c1.append(False)

            try:
                result = gr2_c1.get(key)
                if result:
                    res_gr2_c1.append(True)
                else:
                    res_gr2_c1.append(False)
            except Exception as e:
                res_gr2_c1.append(False)

        # check c2 ("gaid")
        if key_sys == "gaid":
            try:
                result = gr1_c2.get(key)
                if result:
                    res_gr1_c2.append(True)
                else:
                    res_gr1_c2.append(False)
            except Exception as e:
                res_gr1_c2.append(False)

            try:
                result = gr2_c2.get(key)
                if result:
                    res_gr2_c2.append(True)
                else:
                    res_gr2_c2.append(False)
            except Exception as e:
                res_gr2_c2.append(False)

        # check c3 ("adid")
        if key_sys == "adid":
            try:
                result = gr1_c3.get(key)
                if result:
                    res_gr1_c3.append(True)
                else:
                    res_gr1_c3.append(False)
            except Exception as e:
                res_gr1_c3.append(False)

            try:
                result = gr2_c3.get(key)
                if result:
                    res_gr2_c3.append(True)
                else:
                    res_gr2_c3.append(False)
            except Exception as e:
                res_gr2_c3.append(False)

        # check c4 ("dvid")
        if key_sys == "dvid":
            try:
                result = gr1_c4.get(key)
                if result:
                    res_gr1_c4.append(True)
                else:
                    res_gr1_c4.append(False)
            except Exception as e:
                res_gr1_c4.append(False)

            try:
                result = gr2_c4.get(key)
                if result:
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
