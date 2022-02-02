import Functions.AdminFunctions as AF
from Functions.ScrapeFunctions import *
import pandas as pd
import os, sys
import time
import random


def crawl_issues(journal, from_volume, from_issue, to_volume, to_issue, continuous_issue_inc=False):
    '''

    :param journal:
    :param from_volume:
    :param from_issue:
    :param to_volume:
    :param to_issue:
    :return:
    '''

    # 1. CONFIRM JOURNAL DATA DIRECTORY
    journal_dir = AF.confirm_journal_data_directories(journal)

    # 2. LOAD TABLES OF CONTENTS AND ARTICLES
    tocs_dir = f"{journal_dir}/Tables_of_Contents"
    tocs = os.listdir(tocs_dir)
    article_dir = f"{journal_dir}/Articles"
    articles = os.listdir(article_dir)

    # 3. PREPARE THE FN-LINK-DOI CONVERSION DATAFRAME AS DIC
    fn_link_doi_dic = {'journal': [], 'year': [], 'volume': [], 'issue': [],
                       'article': [], 'filename': [], 'link': [], 'doi': []}


    # 3. CRAWL FROM THE FROM_VOLUME TO THE TO_VOLUME
    year, volume, issue = None, from_volume, from_issue

    while True:
        # search for the html TOC
        toc_fp = None
        for toc in tocs:
            fp = f"{tocs_dir}/{toc}"
            m = re.search(r"(\d{4})_(\d+)_([-\d]+)_Contents.html", toc)
            y = int(m.group(1))
            v = int(m.group(2))
            issue_list = [int(x) for x in m.group(3).split("-")]
            i = issue_list[-1]
            if volume == v and issue in issue_list:
                # if we have the TOC saved in HTML
                toc_fp = fp
                year = y
                break

        # if we do not have the TOC in html, scrape it
        if toc_fp == None:
            try:
                toc_fp = scrape_and_save_toc_html(journal, volume, issue)
            except:
                if issue == 1:
                    issue = "1-2"
                    toc_fp = scrape_and_save_toc_html(journal, volume, issue)
                else:
                    raise ValueError("Invalid issue link.")

            m = re.search(r"(\d{4})_(\d+)_([-\d]+)_Contents.html", toc_fp)
            year = m.group(1)
            volume = int(m.group(2))
            issue_list = [int(x) for x in m.group(3).split("-")]
            issue = issue_list[-1]
            print(f"scraping table of contents: volume {volume}, issue {issue}, year {year}")

        # load the TOC soup
        soup = load_soup(toc_fp)
        # download all of the articles
        article_refs = extract_article_refs(journal, soup)
        article_links = [x['link'] for x in article_refs]
        article_dois = [x['doi'] for x in article_refs]
        article_links_reduced = [x['reduced_link'] for x in article_refs]
        for i in range(0, len(article_links)):
            a_id = i+1
            a_link = article_links[i]
            a_link_red = article_links_reduced[i]
            a_doi = article_dois[i]
            a_fp = generate_article_fp(journal, year, a_link)
            a_fn = re.search(r"Articles/(.+)$", a_fp).group(1)
            # reduced filenames for cases where issue is e.g. 1-2
            a_fp_red = generate_article_fp(journal, year, a_link_red)
            a_fn_red = re.search(r"Articles/(.+)$", a_fp_red).group(1)

            fn_link_doi_dic['journal'].append(journal)
            fn_link_doi_dic['year'].append(year)
            fn_link_doi_dic['volume'].append(volume)
            fn_link_doi_dic['issue'].append(issue)
            fn_link_doi_dic['article'].append(a_id)
            fn_link_doi_dic['filename'].append(a_fn)
            fn_link_doi_dic['link'].append(a_link)
            fn_link_doi_dic['doi'].append(a_doi)

            if a_fn_red not in articles:
                print(f"scraping article: {a_fn_red}")
                scrape_and_save_article_html(a_link, a_fp_red)
                time.sleep(random.randrange(5, 10))

        # load in the volume details
        details = get_volume_details_from_toc(soup)

        # break if we have scraped the to_issue
        if (issue == to_issue) and (volume == to_volume):
            break

        # Increment issue, and increment volume if reached issue max
        if issue == details['end_issue']:
            if not continuous_issue_inc:
                issue = 0
            volume += 1

        issue += 1
        continue


    # 5. SAVE THE FN-LINK-DOI DF AS XLSX
    fn_link_doi_dic_df = pd.DataFrame(fn_link_doi_dic)
    fp = f'{journal_dir}/article_references.xlsx'
    fn_link_doi_dic_df.to_excel(fp, index=False)
    # writer = pd.ExcelWriter(fp, engine='xlsxwriter')
    # fn_link_doi_dic_df.to_excel(writer, sheet_name="Articles", index=False)
    # writer.save()

    print(f"COMPLETED scrape of all articles in the interval for {journal}!")


def c_crawl_issues(journal, from_volume, from_issue, to_volume, to_issue, continuous_issue_inc=False):
    crawl_issues(journal, from_volume, from_issue, to_volume, to_issue, continuous_issue_inc=continuous_issue_inc)

    while True:
        try:
            crawl_issues(journal, from_volume, from_issue, to_volume, to_issue, continuous_issue_inc=continuous_issue_inc)
            break
        except:
            print("Failure. Sleeping then restart...")
            time.sleep(60)



if __name__ == "__main__":
    #c_crawl_issues("ej", 113, 484, 131, 640, True)  #2003
    #c_crawl_issues("ectj", 5, 1, 25, 1, False) # 2002
    #c_crawl_issues("qje", 126, 1, 137, 1, False) # 2011
    #c_crawl_issues("restud", 71, 1, 89, 1, False)  #2004
    c_crawl_issues("oxrep", 24, 1, 37, 4, False) # 2007
    #c_crawl_issues("cje", 28, 1, 45, 6, False) #2004