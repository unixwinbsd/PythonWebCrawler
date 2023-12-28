﻿"""Simple Python 3 web crawler, to be extended for various uses.
"""
import collections
import string
import sys

from timeit import default_timer
from urllib.parse import urldefrag, urljoin, urlparse

import bs4
import requests


def crawler(startpage, maxpages=100, singledomain=True):
    """Crawl the web starting from specified page.

    1st parameter = URL of starting page
    maxpages = maximum number of pages to crawl
    singledomain = whether to only crawl links within startpage's domain
    """

    pagequeue = collections.deque()  # queue of pages to be crawled
    pagequeue.append(startpage)
    crawled = []  # list of pages already crawled
    domain = urlparse(startpage).netloc if singledomain else None

    pages = 0  # number of pages succesfully crawled so far
    failed = 0  # number of links that couldn't be crawled

    sess = requests.session()  # initialize the session
    while pages < maxpages and pagequeue:
        url = pagequeue.popleft()  # get next page to crawl (FIFO queue)

        # read the page
        try:
            response = sess.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema):
            print("*FAILED*:", url)
            failed += 1
            continue
        if not response.headers["content-type"].startswith("text/html"):
            continue  # don't crawl non-HTML content

        # Note that we create the Beautiful Soup object here (once) and pass it
        # to the other functions that need to use it
        soup = bs4.BeautifulSoup(response.text, "html.parser")

        # process the page
        crawled.append(url)
        pages += 1
        if pagehandler(url, response, soup):
            # get the links from this page and add them to the crawler queue
            links = getlinks(url, domain, soup)
            for link in links:
                if not url_in_list(link, crawled) and not url_in_list(link, pagequeue):
                    pagequeue.append(link)

    print("{0} pages crawled, {1} links failed.".format(pages, failed))


def getcounts(words=None):
    """Convert a list of words into a dictionary of word/count pairs.
    Does not include words not deemed interesting.
    """

    # create a dictionary of key=word, value=count
    counts = collections.Counter(words)

    # save total word count before removing common words
    wordsused = len(counts)

    # remove common words from the dictionary
    shortwords = [word for word in counts if len(word) < 3]  # no words <3 chars
    ignore = shortwords + [
        "after",
        "all",
        "and",
        "are",
        "because",
        "been",
        "but",
        "for",
        "from",
        "has",
        "have",
        "her",
        "more",
        "not",
        "now",
        "our",
        "than",
        "that",
        "the",
        "these",
        "they",
        "their",
        "this",
        "was",
        "were",
        "when",
        "who",
        "will",
        "with",
        "year",
        "hpv19slimfeature",
        "div",
    ]
    for word in ignore:
        counts.pop(word, None)

    # remove words that contain no alpha letters
    tempcopy = [_ for _ in words]
    for word in tempcopy:
        if noalpha(word):
            counts.pop(word, None)

    return (counts, wordsused)


def getlinks(pageurl, domain, soup):
    """Returns a list of links from from this page to be crawled.

    pageurl = URL of this page
    domain = domain being crawled (None to return links to *any* domain)
    soup = BeautifulSoup object for this page
    """

    # get target URLs for all links on the page
    links = [a.attrs.get("href") for a in soup.select("a[href]")]

    # remove fragment identifiers
    links = [urldefrag(link)[0] for link in links]

    # remove any empty strings
    links = [link for link in links if link]

    # if it's a relative link, change to absolute
    links = [
        link if bool(urlparse(link).netloc) else urljoin(pageurl, link)
        for link in links
    ]

    # if only crawing a single domain, remove links to other domains
    if domain:
        links = [link for link in links if samedomain(urlparse(link).netloc, domain)]

    return links


def getwords(rawtext):
    """Return a list of the words in a text string.
    """
    words = []
    cruft = ',./():;!"' + "<>'â{}"  # characters to strip off ends of words
    for raw_word in rawtext.split():
        # remove whitespace before/after the word
        word = raw_word.strip(string.whitespace + cruft + "-").lower()

        # remove posessive 's at end of word
        if word[-2:] == "'s":
            word = word[:-2]

        if word:  # if there's anything left, add it to the words list
            words.append(word)

    return words


def pagehandler(pageurl, pageresponse, soup):
    """Function to be customized for processing of a single page.

    pageurl = URL of this page
    pageresponse = page content; response object from requests module
    soup = Beautiful Soup object created from pageresponse

    Return value = whether or not this page's links should be crawled.
    """
    print("Crawling:" + pageurl + " ({0} bytes)".format(len(pageresponse.text)))
    # wordcount(soup) # display unique word counts
    return True


def noalpha(word):
    """Determine whether a word contains no alpha characters.
    """
    for char in word:
        if char.isalpha():
            return False
    return True


def samedomain(netloc1, netloc2):
    """Determine whether two netloc values are the same domain.

    This function does a "subdomain-insensitive" comparison. In other words ...

    samedomain('www.unixwinbsd.site', 'unixwinbsd.site') == True
    samedomain('unixwinbsd.site', 'www.unixwinbsd.site') == True
    """
    domain1 = netloc1.lower()
    if "." in domain1:
        domain1 = domain1.split(".")[-2] + "." + domain1.split(".")[-1]

    domain2 = netloc2.lower()
    if "." in domain2:
        domain2 = domain2.split(".")[-2] + "." + domain2.split(".")[-1]

    return domain1 == domain2


def url_in_list(url, listobj):
    """Determine whether a URL is in a list of URLs.

    This function checks whether the URL is contained in the list with either
    an http:// or https:// prefix. It is used to avoid crawling the same
    page separately as http and https.
    """
    http_version = url.replace("https://", "http://")
    https_version = url.replace("http://", "https://")
    return (http_version in listobj) or (https_version in listobj)


def wordcount(soup):
    """Display word counts for a crawled page.

    pageresponse = page content; response object from requests module
    soup = Beautiful Soup object created from pageresponse

    This is an example of a page handler. Just creates a list of unique words on
    the page and displays the word counts.
    """
    rawtext = soup.get_text()
    # print(rawtext)
    words = getwords(rawtext)
    counts, _ = getcounts(words)
    if counts.most_common(1)[0][1] < 10:
        print("This page does not have any words used more than 10 times.")
    else:
        print(counts.most_common(10))


# if running standalone, crawl some Microsoft pages as a test
if __name__ == "__main__":
    # set stdout to support UTF-8
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    START = default_timer()
    crawler("https://www.unixwinbsd.site", maxpages=350)
    END = default_timer()
    print("Elapsed time (seconds) = " + str(END - START))
