# 1. IMPORTS

## Dependencies
import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import Functions.AdminFunctions as AF
import json

## import credentials
import Credentials.cookie as cookie_data

#-------------- NESTED PATH CORRECTION --------------------------------#
import os, sys, re
# For all script files, we add the parent directory to the system path
cwd = re.sub(r"[\\]", "/", os.getcwd())
cwd_list = cwd.split("/")
path = sys.argv[0]
path_list = path.split("/")
# either the entire filepath is entered as command i python
if cwd_list[0:3] == path_list[0:3]:
    full_path = path
# or a relative path is entered, in which case we append the path to the cwd_path
else:
    full_path = cwd + "/" + path
# remove the overlap
root_dir = re.search(r"(^.+HTML-projektet)", full_path).group(1)
sys.path.append(root_dir)

#----------------------------------------------------------------------#


# 2. GENERAL SCRAPING FUNCTIONS

def get_cookies_and_headers():
    '''
    Returns the cookies and headers needed to scrape past authentication
    :return: (cookie, header) tuple
    '''

    cookies = cookie_data.cookies

    headers = {
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-GPC': '1',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://login.ez.hhs.se/',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    return cookies, headers

def scrape_link(link):
    '''
    Download an HTML webpage as a soup object
    :param link: link/url(str)
    :return: soup object
    '''

    # Getting the headers and cookies
    cookies, headers = get_cookies_and_headers()
    # Using the cookies and headers info above to access the EJ site through Stockholm University library
    # Enter verify=False as an argument in the command below to work arround certification issues (note, this makes you exposed to man in the middle attacks)
    response = requests.get(link, headers=headers, cookies=cookies)  #, verify=False)
    # Getting the HTML content from the site
    content = response.content
    # Getting the HTML content ready for scraping using BeautifulSoup
    soup = BeautifulSoup(content, 'lxml')

    # Check that the credentials were valid
    if cookie_data.university == "SSE":
        soup_title = str(soup.find('title').contents)
        m = re.search(r"sse.+library.+login", soup_title.lower())
        if m:
            raise ValueError("Credentials for scraping are not valid. Update credentials and the variable valid_credentials.")
        else:
            return soup
    elif cookie_data.university == "LU":
        soup_title = str(soup.find('title').contents)
        m = re.search(r"shibboleth authentication request", soup_title.lower())
        if m:
            raise ValueError(
                "Credentials for scraping are not valid. Update credentials and the variable valid_credentials.")
        else:
            return soup


def get_base_link():
    '''
    returns the base link for all issues tables of contents
    :param university_abbreviation: (str) from list ["SSE", "LU"]
    :return: base_link (str)
    '''
    if cookie_data.university == "SSE":
        return "https://academic-oup-com.ez.hhs.se"
    elif cookie_data.university == "LU":
        return "https://academic-oup-com.ludwig.lub.lu.se"
    else:
        return None


def generate_issue_link(journal, volumenumber, issuenumber):
    '''
    Generate url to issue of desired journal
    :param journal: journal abbreviation (str) ['ej']
    :param volumenumber: volume number (int)
    :param issuenumber: issue number (int)
    :return: link the the journal issue (str)
    '''

    if journal.lower() in list(AF.oxford_journals.keys()):
        # Combining the different parts of the URL to get the correct issue link
        issuelink = f"{get_base_link()}/{journal}/issue/{str(volumenumber)}/{str(issuenumber)}"
        return issuelink
    else:
        return None


def generate_issue_toc_fp(journal_dir, year, volumenumber, issuenumber):
    '''
    Generate filepath to offline soup file of table of contents for issue
    :param journal_dir: path to journal data (str) e.g. "Data/Economic_Journal
    :para year: the volume year (int)
    :param volumenumber: volume number (int)
    :param issuenumber: issue number (int)
    :return: filepath to toc soup file (str)
    '''
    return f"{journal_dir}/Tables_of_Contents/{str(year)}_{str(volumenumber)}_{str(issuenumber)}_Contents.html"

def generate_article_fp(journal, year, link):
    if journal.lower() in list(AF.oxford_journals.keys()):
        journal_dir = AF.get_journal_dir(journal)
        # https://academic-oup-com.ludwig.lub.lu.se/ej/article/113/484/65/5079556
        m = re.search(r"article/(.+)$", link).group(1).replace("/", "_")
        return f"{journal_dir}/Articles/{str(year)}_{m}.html"


def save_soup_html(journal, type, soup, filepath):
    '''
    Save the text of a soup file as an html file (basic html skeleton included)
    Tip: clean out contents in head tags from soup as they might contain trackers
    :param text: desired html code from a soup object
    :param filepath: filepath to save destination
    :return: True
    '''
    content_list = []
    if journal == "ej":
        if type.lower() in ['toc', 'table of contents', 'contents']:
            issue_dropdown = soup.find("select", {"id": "IssuesList"})
            article_list = soup.find("div", {"id": "ArticleList"})
            content_list = [str(issue_dropdown), str(article_list)]
        if type.lower() in ['article']:
            main = soup.find("div", {'id': 'ContentColumn'}).find("div", {'class': "content-inner-wrap"})
            content_list = [str(main)]

    prepend = '''
<!DOCTYPE html>
<html>
<body>
    '''
    append = '''
</body>
</html>
    '''

    if content_list != []:
        output = prepend + "\n".join(content_list) + append

        file = open(filepath, 'w',encoding='utf8')
        file.write(output)
        file.close()
        return True
    else:
        print("No content to save")
        return False


def load_soup(filepath):
    file = open(filepath, 'r', encoding='utf-8')
    content = file.read()
    file.close()
    #print(content)
    soup = BeautifulSoup(content, 'lxml')
    return soup



def scrape_and_save_toc_html(journal, volume, issue):
    '''

    :param journal:
    :param volume:
    :param issue:
    :return:
    '''
    il = generate_issue_link(journal, volume, issue)
    #print(il)
    soup = scrape_link(il)
    details = get_volume_details_from_toc(soup)
    # reduce the filepath for cases where we have issue e.g. 1-2
    if type(issue) == str:
        issue = int(re.search(r"-(\d+)$", issue).group(1))
    toc_fp = generate_issue_toc_fp(AF.get_journal_dir(journal), details['year'], volume, issue)
    save_soup_html("ej", "toc", soup, toc_fp)
    return toc_fp


def scrape_and_save_article_html(link, article_fp):
    soup = scrape_link(link)
    save_soup_html("ej", "article", soup, article_fp)
    return article_fp



# 3. FUNCTIONS SPECIFIC TO ECONOMIC JOURNAL


def get_volume_details_from_toc(soup):
    '''
    Get the issue span and year of a volume from its table of contents (toc)
    :param soup: the soup object of a table of contents for an issue
    (e.g. soup of https://academic-oup-com.ez.hhs.se/ej/issue/113/484)
    :return: {'start_issue': xxx, 'end_issue': xxx, 'year': xxxx} dictionary
    '''
    issues = []
    years = []
    dropdown = soup.find("select", {"id": "IssuesList"})
    options = dropdown.find_all('option')
    for o in options:
        try:
            m = re.search(r">.*Issue\s*(\d+),[\w\s]+(\d{4})", str(o))
            issues.append(int(m.group(1)))
            years.append(str(m.group(2)))
        except:
            pass

    year_out = "-".join(list(set(years)))
    if "-" not in year_out:
        year_out = int(year_out)

    return {'start_issue': min(issues), 'end_issue': max(issues), 'year': year_out}



def extract_article_refs(journal, soup, refs='all'):
    '''
    Extract all links to articles of an issue
    :param journal: journal abbreviation (oxford journals)
    :param soup: soup of TOC
    :param refs: choose between ['link', 'doi', 'all']
    :return: list of all links to articles in the issue
    '''

    # extract all articles
    articles = soup.findAll('h5')

    output = []
    # find all the articles
    for a in articles:
        # extract the link  (put in try statement to avoid non-link h5s)
        try:
            path = re.search(r"href=\"(/" + re.escape(journal) + r"/article/.+)\"", str(a)).group(1)
            link = get_base_link() + path
            # reduced link has the latter issue i.e. 1-2 = 2
            m = re.search(r"^(.*article/\d+/)([-\d]+)(/.*)$", link)
            reduced_link = m.group(1) + re.sub(r"\d-", "", m.group(2)) + m.group(3)
        except:
            continue

        # extract the doi as well
        try:
            uni_doi = a.parent.find('div', {'class': 'ww-citation-primary'}).find('a').text
            doi_ending = re.search(r"doi[^/]+(/.+)$", uni_doi).group(1)
            universal_doi = f"https://doi.org{doi_ending}"
        except:
            universal_doi = None

        if refs == "all":
            output.append({'link': link, 'doi': universal_doi, 'reduced_link': reduced_link})
        elif refs == "link":
            output.append(link)
        elif refs == "doi":
            output.append(universal_doi)


    return output






if __name__ == "__main__":
    # url = generate_issue_link("ej", 116, 515)
    # soup = scrape_link(url)
    # details = get_volume_details_from_toc(soup)

    # test that all links and dois are correct in the refs
    # toc = scrape_link("https://academic-oup-com.ludwig.lub.lu.se/ej/issue/116/515")
    # refs = extract_article_refs(toc)
    # print(refs)

    pass


