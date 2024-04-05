import os
import re
import datetime
import logging
import argparse
import asyncio
import aiofiles
import aiohttp
import requests
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


# def find_href_in_comments(comments_pages):
#     """Функция поиска ссылок в комментариях. Принимает единственный аргумент comments_pages.
#     Ожидается, что это будет итерируемый объект (сейчас список), содержащий ссылки на комментарии.
#     Результатом выполенния функции является сбор ссылок со страниц комментариев к новостям.
#     Новые ссылоки добавляются к уже существующей глобальной переменной link_list, сама функция
#     ничего не возвращает."""
#     global link_list
#     for page in comments_pages:
#         response = requests.get(page)
#         bs_page = BeautifulSoup(response.text, 'lxml')
#         data = bs_page.find_all('div', class_='comment')
#         result = [x.find('a').get('href') for x in data \
#                   if x.find('a') and 'https' in x.find('a').get('href')]
#         if result:
#             link_list += result

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
                    if "Sorry, we're not able to serve your requests this quickly." in text:
                        print(f"Received 'Sorry' message. Retrying...")
                        await asyncio.sleep(retry_interval)
                        retry_count += 1
                        if retry_count > max_retry_count:
                            return f"Retry limit reached for {url}"
                        continue
                    if "Timeout occurred while fetching" in text:
                        pass
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
                        print(f"Forbidden on: {url}")
                        return f"Forbidden on: {url}"
                    elif response.content_type != "text/html":
                        print(f"Content_type on: {url}")
                        return f"Content_type on: {url}"
                    else:
                        try:
                            text = await response.text()
                        except Exception as e:
                            print(e)
                            return e

                        if "Sorry, we're not able to serve your requests this quickly." in text:
                            print(f"Received 'Sorry' message. Retrying...")
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

    # """Асинхронная функция загрузки содержимого страниц. Принимает в качестве аргументов два значения:
    # link - ссылка на страницу (ожидается строка) и parser - объект содержащий аргументы при запуске скрипта.
    # Функция ничего не возвращает, а лишь выполняет запись страниц в указанной папке."""
    # global news_dict
    # filename = re.sub(r"[?:*<>,; /\\]", r'', link)
    # full_filename = os.path.join(parser.d, filename[:20])
    # if not news_dict[link]:
    #     async with aiofiles.open(f'{full_filename}.html', mode='wb+') as handle:
    #         async with aiohttp.ClientSession() as session:
    #             try:
    #                 response = await session.request('GET', link)
    #                 page = await response.read()
    #                 await handle.write(page)
    #                 news_dict[link] = True
    #             except aiohttp.client_exceptions.InvalidURL as err:
    #                 logger.info(f'Ссылка {link} сейчас недоступна.')
    #
    # else:
    #     logger.info(f'Ссылка {link} уже была обработана ранее.')


async def main():
    timeout = 10  # Adjust the timeout value (in seconds) as per your requirement
    max_concurrent = 3
    retry_interval = 2
    max_retry_count = 5

    html = await get_start_page_html()
    urls_news_list, urls_comment_list = get_comment_urls_list(html)

    # urls_comment_list = urls_comment_list[:5]

    responses = await fetch_all(urls_comment_list, max_concurrent, timeout, retry_interval, max_retry_count)

    # run for fetching links from comments
    tasks = []
    for response in responses:
        url_main, urls_in_comments_list = get_url_main_and_urls_in_comments(response)
        if url_main and urls_in_comments_list:
            tasks.append(fetch_comment_links(url_main, urls_in_comments_list, max_concurrent, timeout, retry_interval,
                                             max_retry_count))

    if tasks:
        responses = await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
