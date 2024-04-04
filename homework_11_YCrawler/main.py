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

import logging

# Параметры логирования
logging.basicConfig(filename="logs.log",
                    filemode="a",
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = 'https://news.ycombinator.com/'


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


# async def fetch_link(session, semaphore, url, timeout):
#     async with semaphore:
#         try:
#             async with session.get(url, timeout=timeout) as response:
#                 if
#                 return await response.text()
#         except asyncio.TimeoutError:
#             return f"Timeout occurred while fetching {url}"
#         except aiohttp.ClientError as e:
#             return f"Error occurred while fetching {url}: {e}"

async def fetch_link(session, semaphore, url, timeout, retry_interval):
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
                        if retry_count > 5:
                            return f"Retry limit reached for {url}"
                        continue
                    return text
            except asyncio.TimeoutError:
                return f"Timeout occurred while fetching {url}"
            except aiohttp.ClientError as e:
                return f"Error occurred while fetching {url}: {e}"


async def fetch_all(links, max_concurrent, timeout, retry_interval):
    semaphore = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_link(session, semaphore, link, timeout, retry_interval) for link in links]
        return await asyncio.gather(*tasks)


async def main():
    timeout = 10  # Adjust the timeout value (in seconds) as per your requirement
    max_concurrent = 5
    retry_interval = 1

    html = await get_start_page_html()
    urls_news_list, urls_comment_list = get_comment_urls_list(html)

    responses = await fetch_all(urls_comment_list, max_concurrent, timeout, retry_interval)
    for url, response in zip(urls_comment_list, responses):
        print(f'Response from {url}:')
        print(response)
        print()


# async def main():
#     MAX_CONNECTIONS = 5
#
#     html = await get_start_page_html()
#     urls_news_list, urls_comment_list = get_comment_urls_list(html)
#
#     responses = await fetch_all(urls_comment_list, MAX_CONNECTIONS)
#     for url, response in zip(urls_comment_list, responses):
#         print(f'Response from {url}:')
#         print(response)
#         print()


if __name__ == "__main__":
    asyncio.run(main())
