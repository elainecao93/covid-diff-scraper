import requests
import re
import smtplib
import ssl
import difflib
import os

SITE_URL = "https://www.cdc.gov/coronavirus/2019-ncov/index.html"

SMTP_SERVER = os.environ.get("SMTP_SERVER")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
PASSWORD = os.environ.get("PASSWORD")

FULL_URL_REGEX = "http[s]?://www.cdc.gov/coronavirus/(?:[a-zA-Z]|[0-9]|[$-@])+.html"
URL_REGEX = "\"/coronavirus/(?:[a-zA-Z]|[0-9]|[$-@])+.html"

pages_dict = {}


def get_page(page_url):
    r = requests.get(page_url)
    return r.text


def get_urls(text):
    urls = set()
    for line in text.splitlines():
        for elem in re.findall(FULL_URL_REGEX, line):
            urls.add(elem)
        for elem in re.findall(URL_REGEX, line):
            urls.add("https://www.cdc.gov" + elem[1:])
    return urls


def get_diff(text1, text2):
    diff_maker = difflib.Differ(charjunk=difflib.IS_CHARACTER_JUNK)
    diff = diff_maker.compare(text1.splitlines(), text2.splitlines())
    output = []
    for line in diff:
        if (line[0] == "-" or line[0] == "+") and len(line) > 80:
            output.append(line)
    return "\n".join(output)


def get_pages(pages, depth_counter):
    next_pages = set()
    for page in pages:
        if page in pages_dict:
            print(f"skipped {page}")
            continue
        print(f"{str(depth_counter)} {page}")
        page_text = get_page(page)
        page_urls = get_urls(page_text)
        pages_dict[page.lower()] = page_text
        for page_url in page_urls:
            next_pages.add(page_url)

    if depth_counter != 3:
        get_pages(next_pages, depth_counter+1)
    else:
        for page in next_pages:
            print(f"missing: {page}")


def compare_pages():
    output = {}
    for page_url in pages_dict:
        print(f"comparing {page_url}")
        page_base = "data/" + page_url[32:].replace("/", "-")
        new_text = pages_dict[page_url]
        try:
            f = open(page_base, "r", encoding="utf-16")
            old_text = f.read()
            f.close()
            diff = get_diff(old_text, new_text)
            if len(diff) > 0:
                output[page_url] = diff
        except FileNotFoundError:
            output[page_url] = "New page"

        f = open(page_base, "w", encoding="utf-16")
        f.write(new_text)
        f.close()

    return output


def build_message(output):
    return "Subject: Automated message from covid-diff-scraper\n\n" + \
           "This is an automated message from covid-diff-scraper.\n\n"\
           + "\n\n".join(f"{elem}\n{output[elem]}\n---" for elem in output)


def send_email(message):
    port = 465

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, port, context=context) as server:
        server.login(SENDER_EMAIL, PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message)


def main():
    get_pages([SITE_URL], 0)
    for page in pages_dict:
        print(page)
    output = compare_pages()
    for elem in output:
        print(elem)
        print(output[elem])
    message = build_message(output)
    send_email(message)


if __name__ == "__main__":
    main()
