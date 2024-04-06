import os
import re
import argparse
import asyncio
import time
from functools import wraps

import aiofiles
import aiohttp
from bs4 import BeautifulSoup
from pathlib import Path
import logging

# Параметры логирования
logging.basicConfig(filename="logs.log",
                    filemode="a",
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = 'https://news.ycombinator.com/'

GLOB_PATH = Path(__file__).parent.resolve()


# Функция декоратор замера времени выполнения функции
def log_time(logger, description=''):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            logger.info(f'Start parsing {description} ({func.__name__})')
            result = func(*args, **kwargs)
            end = time.time()
            exec_time = round(end - start, 5)
            logger.info(f'Parsing time {description} ({func.__name__}): {exec_time}s')
            return result

        return wrapper

    return inner


async def get_start_page_html():
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL) as response:
            logger.info(f"Status: {response.status}")
            logger.info(f"Content-type: {response.headers['content-type']}")

            html = await response.text()
            logger.info(f"Body: {html[:50]}")
    return html


def get_comment_urls_list(html):
    bs_page = BeautifulSoup(html)
    data = bs_page.find_all('span', class_='titleline')
    urls_news_list = [x.find('a').get('href') for x in data]
    # name_news_list = [x.find('a').text for x in data]
    data = bs_page.find_all('a', string=re.compile('comments'))
    urls_comment_list = [BASE_URL + x.get('href') for x in data[1:]]
    return urls_news_list, urls_comment_list


def get_url_main_and_urls_in_comments(comments_page):
    bs_page = BeautifulSoup(comments_page)

    data = bs_page.find_all('span', class_='titleline')
    url_main = [x.find('a').get('href') for x in data]
    if url_main:
        url_main = url_main[0]
    else:
        url_main = None

    data = bs_page.find_all('div', class_='comment')
    urls_in_comments_list = [x.find('a').get('href') for x in data \
                             if x.find('a') and 'https' in x.find('a').get('href')]
    return url_main, urls_in_comments_list


async def fetch_link(session, semaphore, url, timeout, retry_interval, max_retry_count):
    async with semaphore:
        retry_count = 0
        while True:
            try:
                async with session.get(url, timeout=timeout) as response:
                    text = await response.text()

                    # if status is not in 200 group
                    if str(response.status)[0] != "2":
                        logger.info(f"Status: {response.status}, reason: {response.reason}. For url - {url}")
                        await asyncio.sleep(retry_interval)
                        retry_count += 1
                        if retry_count > max_retry_count:
                            return f"Retry limit reached for {url}"
                        continue
                    return text
            except asyncio.TimeoutError:
                return f"Timeout occurred while fetching {url}"
            except aiohttp.ClientError as e:
                return f"Error occurred while fetching {url}: {e}"


async def fetch_all(links, max_concurrent, timeout, retry_interval, max_retry_count):
    semaphore = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_link(session, semaphore, link, timeout, retry_interval, max_retry_count) for link in links]
        return await asyncio.gather(*tasks)


async def fetch_comment_links(url_main, urls_in_comments_list, max_concurrent, timeout, retry_interval,
                              max_retry_count):
    semaphore = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_comment_link(session, semaphore, url_main, url, timeout, retry_interval, max_retry_count) for
                 url in urls_in_comments_list]
        return await asyncio.gather(*tasks)


async def fetch_comment_link(session, semaphore, url_main, url, timeout, retry_interval, max_retry_count):
    async with semaphore:
        retry_count = 0
        while True:
            try:
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 403:
                        logger.info(f"Forbidden on: {url}")
                        return f"Forbidden on: {url}"
                    elif response.content_type != "text/html":
                        logger.info(f"Content_type on: {url}")
                        return f"Content_type on: {url}"
                    else:
                        try:
                            text = await response.text()
                        except Exception as e:
                            logger.info(e)
                            return e

                        if str(response.status)[0] != "2":
                            logger.info(f"Status: {response.status}, reason: {response.reason}. For url - {url}")
                            await asyncio.sleep(retry_interval)
                            retry_count += 1
                            if retry_count > max_retry_count:
                                return f"Retry limit reached for {url}"
                            continue

                        await save_comment_page(url_main, text)
                        return text

            except asyncio.TimeoutError:
                return f"Timeout occurred while fetching {url}"
            except aiohttp.ClientError as e:
                return f"Error occurred while fetching {url}: {e}"


async def save_comment_page(url_main, text):
    url_main = re.sub('[:/!@#$]', '', url_main)
    url_main = url_main + ".txt"
    file_path = GLOB_PATH / "downloads" / url_main
    file_name = file_path / file_path

    async with aiofiles.open(file_name, "a") as file:
        await file.write(text)


def parse_arguments():
    """Функция парсинга аргументов. Принимается два аргумента:
    -d - аргумент для указания папки для сохранения страниц,
    -t - аргумент для указания количества секунд между запусками обкачки."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--only_one', type=int, help='Флаг единичного запуска',
                        default=1)
    parser.add_argument('--parse_dir', type=str, help='Директория для парсинга',
                        default="downloads")
    parser.add_argument('--parse_pause', type=int,
                        help='Количество секунд между запусками обкачки новостного комбинатора, сек',
                        default=10)
    parser.add_argument('--timeout', type=int, help='Таймаут ответа, сек',
                        default=10)
    parser.add_argument('--max_concurrent', type=int, help='Максимальное кол-во одновременных запросов',
                        default=3)
    parser.add_argument('--retry_interval', type=int, help='Таймаут повторной попытки запроса, сек',
                        default=2)
    parser.add_argument('--max_retry_count', type=int, help='Максимальное кол-во повторных запросов',
                        default=5)
    return parser.parse_args()


async def main():
    parser = parse_arguments()

    if not os.path.isdir(f'./{parser.parse_dir}'):
        os.mkdir(parser.d)

    parse_pause = parser.parse_pause
    timeout = parser.timeout
    max_concurrent = parser.max_concurrent
    retry_interval = parser.retry_interval
    max_retry_count = parser.max_retry_count

    while True:
        html = await get_start_page_html()
        urls_news_list, urls_comment_list = get_comment_urls_list(html)

        # urls_comment_list = urls_comment_list[:5]

        responses = await fetch_all(urls_comment_list, max_concurrent, timeout, retry_interval, max_retry_count)

        # run for fetching links from comments
        tasks = []
        for response in responses:
            url_main, urls_in_comments_list = get_url_main_and_urls_in_comments(response)
            if url_main and urls_in_comments_list:
                tasks.append(
                    fetch_comment_links(url_main, urls_in_comments_list, max_concurrent, timeout, retry_interval,
                                        max_retry_count))

        if tasks:
            responses = await asyncio.gather(*tasks)

        if parser.only_one == 1:
            break

        await asyncio.sleep(parse_pause)


if __name__ == "__main__":
    start = time.time()
    logger.info('Start parsing')
    asyncio.run(main())
    end = time.time()
    exec_time = round(end - start, 5)
    logger.info(f'Parsing time: {exec_time}s')
