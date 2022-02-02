from Functions.ParseFunctions import *
import Functions.AdminFunctions as AF
import pandas as pd

#-------------- NESTED PATH CORRECTION --------------------------------#
import os, re, sys
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



class Journal():
    def __init__(self, journal_abb):
        self.name = AF.get_journal_name(journal_abb)
        self.abbreviation = journal_abb
        self._fp = AF.get_journal_dir(journal_abb)
        self.ref_df = pd.read_excel(f"{self._fp}/article_references.xlsx")

    def _get_toc_filenames(self):
        return os.listdir(f"{self._fp}/Tables_of_Contents")

    def list_years(self, type="df"):
        l = sorted(extract_from_filenames(self._get_toc_filenames(), "year"))
        if type in ['df']:
            return pd.DataFrame({'year': l})
        elif type in ['list']:
            return l
        else:
            list_method_format_error()

    def list_volumes(self, type="df"):
        l =  sorted(extract_from_filenames(self._get_toc_filenames(), "volume"))
        if type in ['df']:
            return pd.DataFrame({'volume': l})
        elif type in ['list']:
            return l
        else:
            list_method_format_error()

    def volume(self, volume_number):
        # return the volume object of volume number
        return Volume(volume_number, self)

    def year(self, year):
        volume_number = extract_from_filenames(self._get_toc_filenames(), "volume", [f"year=={year}"])
        if type(volume_number) == list:
            raise ValueError(f"Year {year} has multiple volumes. Please select by volume instead.")
        else:
            return self.volume(volume_number)

    def find_article_by_doi(self, doi):
        ref_df = self.ref_df
        fn = ref_df.loc[ref_df['doi'] == doi, 'filename'].values[0]
        return Article(fn, self)


class Volume():
    def __init__(self, volume_number, journal):
        self.volume_number = volume_number
        self._journal = journal
        self.year = self._get_year()

    def _get_toc_filenames(self):
        return os.listdir(f"{self._journal._fp}/Tables_of_Contents")

    def journal(self):
        return Journal(self._journal.abbreviation)

    def list_issues(self, type='df'):
        l = sorted(extract_from_filenames(self._get_toc_filenames(), "issue", [f"volume=={self.volume_number}"]))
        if type in ['df']:
            return pd.DataFrame({"issue": l})
        elif type in ['list']:
            return l
        else:
            list_method_format_error()

    def _get_year(self):
        return extract_from_filenames(self._get_toc_filenames(), "year", [f"issue in {self.list_issues('list')}"])

    def issue(self, issue_number):
        # return the issue object of issue number
        return Issue(self.volume_number, issue_number, self._journal)



class Issue():
    def __init__(self, volume_number, issue_number, journal):
        self.issue_number = issue_number
        self.volume_number = volume_number
        self._journal = journal
        self._toc_filenames = os.listdir(f"{journal._fp}/Tables_of_Contents")
        self._article_filenames = os.listdir(f"{journal._fp}/Articles")

        self.year = self._get_year()


    def journal(self):
        return Journal(self._journal.abbreviation)

    def volume(self):
        return Volume(self.volume_number, self._journal)

    # def _get_volume(self):
    #     return extract_from_filenames(self._toc_filenames, "volume", [f"issue=={self.issue_number}",
    #                                                                   f"volume=={self.volume_number}"])

    def _get_year(self):
        return extract_from_filenames(self._toc_filenames, "year", [f"issue=={self.issue_number}",
                                                                    f"volume=={self.volume_number}"])

    def list_articles(self, format="df"):
        filenames = extract_from_filenames(self._article_filenames, "filename", [f"issue=={self.issue_number}",
                                                                                 f"volume=={self.volume_number}"])
        articles = []
        for f in filenames:
            a = Article(f, self._journal)
            articles.append(a)
        # sort by id
        articles = sorted(articles, key=lambda x: int(x.id))
        # output
        if format in ['df']:
            dic = {'id': [x.id for x in articles],
                   'authors': [x.authors for x in articles],
                   'title': [x.title for x in articles]}
            a_df = pd.DataFrame(dic).set_index('id')
            return a_df
        elif format in ['list']:
            return articles
        else:
            list_method_format_error()

    def count_articles(self):
        return self.list_articles().shape[0]

    def article(self, article_id):
        ref_df = self._journal.ref_df
        fn = ref_df.loc[(ref_df['volume'] == self.volume_number) & (ref_df['issue'] == self.issue_number) & (ref_df['article'] == article_id), 'filename' ].values[0]
        return Article(fn, self._journal)



class Article:
    def __init__(self, filename, journal):
        self._journal = journal
        self._toc_filenames = os.listdir(f"{journal._fp}/Tables_of_Contents")
        self.year = extract_from_filenames([filename], "year")
        self.volume_number = extract_from_filenames([filename], "volume")
        self.issue_number = extract_from_filenames([filename], "issue")

        # find article id (i.e. order in table of contents) from references df
        ref_df = self._journal.ref_df
        self.id = ref_df.loc[ref_df['filename'] == filename, 'article'].values[0]
        self.doi = ref_df.loc[ref_df['filename'] == filename, 'doi'].values[0]

        # article overview
        self.filepath = f"{self._journal._fp}/Articles/{filename}"
        self.soup = self._get_soup()
        ao = article_overview(self._journal.abbreviation, self.soup)
        self.title = ao['title']
        self.authors = ao['authors']
        self.author_count = len(ao['authors'])
        try:
            self.abstract = self.soup.find('section', {'class': 'abstract'}).text
        except:
            self.abstract = None

    def journal(self):
        return Journal(self._journal.abbreviation)

    def volume(self):
        return Volume(self.volume_number, self._journal)

    def issue(self):
        return Issue(self.volume_number, self.issue_number, self._journal)

    def _get_soup(self):
        return load_soup(self.filepath)

    def _identify_headings(self, expanded=False):
        headings = []
        headings_expanded = []

        if self._journal.abbreviation in list(AF.oxford_journals.keys()):
            soup = BeautifulSoup(str(self.soup), 'lxml')
            # prepend the intro div
            article_fulltext = soup.find("div", {"data-widgetname": "ArticleFulltext"})
            # remove the abstract is there is one
            try:
                article_fulltext.find('section', {'class': 'abstract'}).decompose()
                article_fulltext.find('h2', {'class': 'abstract-title'}).decompose()
            except:
                pass

            # create the headings_raw list, which determines split of sections
            intro = article_fulltext.find("p")
            headings_raw = soup.findAll("h2")
            headings_raw = [intro] + headings_raw

            # add \n to end of all h3, h4, h5
            for x in soup.findAll(['h3', 'h4', 'h5' 'p']):
                x.append("\n\n")

            for i in range(0, len(headings_raw)):

                # extract heading text and subsequent soup
                if i == 0:
                    h = "Introduction"
                    h_soup = gather_soup(headings_raw[i], until=['h2'], include_first_element=True)
                else:
                    h = headings_raw[i].text
                    h_soup = gather_soup(headings_raw[i], until=['h2'])

                # For economic journal, the first soup object is the div after the abstract and before the

                try:
                    num_string = re.search(r"^([\d\.]+)", h).group(1)
                    level_list = num_string.split(".")
                    while level_list[-1] == "":
                        level_list = level_list[:-1]
                    levels = len(level_list)
                except:
                    levels = 1

                # append in the correct target (main headers list, or in a subheading list)
                append_target = headings
                parent = None
                for j in range(1, levels):
                    parent = append_target[-1]
                    append_target = parent.subheadings

                id = len(append_target) + 1

                # now prepare for next round and append
                to_append = Heading(h, levels, id, parent, h_soup, self.doi, self._journal)
                headings_expanded.append(to_append)  # for the expanded list
                append_target.append(to_append)
        if expanded:
            return headings_expanded
        else:
            return headings


    def list_headings(self, format="df"):
        if format in ['df']:
            return unpack_headings(self._identify_headings(), 1)
        elif format in ['list']:
            return self._identify_headings(expanded=True)
        else:
            list_method_format_error()

    def heading(self, id):
        if type(id) == int:
            id = [id]
        elif type(id) == tuple or type(id) == list:
            pass
        else:
            raise ValueError("Could not understand heading selection. "
                             "Please select heading by h1 id or by a tuple of (h1, h2, ...)")

        target = self._identify_headings()
        for i in id:
            if i < 1:
                raise ValueError("Invalid index entered.")
            if type(target) == list:
                target = target[i-1]
            elif type(target) != list:
                # no zero ids in the subheadings for ej
                if i == 0:
                    break
                try:
                    target = target.subheadings[i-1]
                except:
                    df = self.list_headings()
                    cols = df.columns[df.columns.str.endswith(tuple('0123456789'))]
                    raise ValueError(f"Too many levels specified in heading selection. Max depth is {len(cols)}.")
        return target

    def list_tables(self, type='df'):
        all_tables = []
        for h in self.list_headings('list'):
            t = h.list_tables("list")
            all_tables = all_tables + t
        if type in ['df']:
            id = [i for i in range(1, (len(all_tables)+1))]
            name = [x.name for x in all_tables]
            title = [x.title for x in all_tables]
            return pd.DataFrame({"id": id, "name": name, "title": title}).set_index("id")
        elif type in ['list']:
            return all_tables
        else:
            list_method_format_error()

    def table(self, id):
        tables = self.list_tables("list")
        if len(tables) == 0:
            raise ValueError("No tables are found in this article.")
        else:
            try:
                return tables[int(id)-1]
            except:
                raise ValueError(f"Invalid table id provided. You entered \"{id}\", "
                                 f"but expected an integer between 1-{str(len(tables))}.")
            pass


class Heading:
    def __init__(self, name, level, id, parent, soup, doi, journal):
        self.name = name
        self.level = level
        self.id = id
        self.parent = parent
        self.soup = soup
        self.text = self.get_text()
        self.subheadings = []
        self.id_global = self._get_id_global()
        self._journal = journal
        self._article_doi = doi

    # access the article that has the heading
    def article(self):
        j = Journal(self._journal.abbreviation)
        x = j.find_article_by_doi(self._article_doi)
        return x

    def _get_id_global(self):
        n = []
        h = self
        while h.parent != None:
            n.append(str(h.id))
            h = h.parent
        n.append(str(h.id))
        n.reverse()
        return ".".join(n)

    def list_subheadings(self):
        return unpack_headings(self.subheadings, 1)

    def subheading(self, id):
        if type(id) == int:
            id = [id]
        elif type(id) == tuple or type(id) == list:
            pass
        else:
            raise ValueError("Could not understand heading selection. "
                             "Please select heading by h1 id or by a tuple of (h1, h2, ...)")
        if self.subheadings == []:
            raise ValueError("This heading has no subheadings.")
        target = self.subheadings
        for i in id:
            if i == 0:
                raise ValueError("Invalid subheading id.")
            if type(target) == list:
                target = target[i-1]
            elif type(target) != list:
                try:
                    target = target.subheadings[i-1]
                except:
                    df = self.list_subheadings()
                    cols = df.columns[df.columns.str.endswith(tuple('0123456789'))]
                    raise ValueError(f"Too many levels specified in heading selection. Max depth is {len(cols)}.")
        return target


    def _identify_tables(self):
        # get all the tables in the heading section
        soup_tables = (self.soup.findAll('table'))

        # convert all the tables to pd dataframes
        tables = []
        raw_dfs = []
        for i in range(0, len(soup_tables)):
            t = soup_tables[i]
            t_wrapper = t.parent.parent
            title_wrap = t_wrapper.find('div', {'class': 'table-wrap-title'})
            name = title_wrap.find('span')
            title = title_wrap.find('div', {'class': 'caption'})
            footnotes = t_wrapper.find('div', {'class': 'footnote'})
            # extract text when available
            if name != None:
                name = name.text
            if title != None:
                title = title.text
            if footnotes != None:
                footnotes = footnotes.text

            # create the Table objects using the soup for the table as we will need to
            # correct misaligned tables directly in the html code.
            tables.append(Table(name, title, t, footnotes, self))
            # convert to df for duplicate identification, as tables might be duplicate,
            # but differ in html tags. Converting the dataframes will disregard html tags
            raw_dfs.append(pd.read_html(str(t))[0])

        # Remove any duplicate
        tables_unique = []
        dfs_unique = []
        # if len(tables) == 0:
        #     return []
        for i in range(0, len(tables)):
            t = tables[i]
            df = raw_dfs[i]
            if i > 0:
                for dfu in dfs_unique:
                    if df.equals(dfu):
                        break
                else:
                    tables_unique.append(t)
                    dfs_unique.append(df)
        return tables_unique


    def list_tables(self, type='df'):
        table_list = self._identify_tables()
        if type in ['df']:
            id = [i for i in range(1, (len(table_list)+1))]
            name = [x.name for x in table_list]
            title = [x.title for x in table_list]
            return pd.DataFrame({"id": id, "name": name, "title": title}).set_index("id")
        elif type in ['list']:
            return table_list
        else:
            list_method_format_error()

    def table(self, id):
        tables = self.list_tables("list")
        if len(tables) == 0:
            raise ValueError("No tables are found in this article.")
        else:
            try:
                return tables[int(id)-1]
            except:
                raise ValueError(f"Invalid table id provided. You entered \"{id}\", "
                                 f"but expected an integer between 1-{str(len(tables))}.")
            pass


    def get_text(self):
        soup = BeautifulSoup(str(self.soup), 'lxml')
        for t in soup.findAll('div', {'class': ['table-full-width-wrap', 'table-modal']}):
            t.decompose()
        return soup.text

class Table:
    def __init__(self, name, title, soup, footnotes, heading):
        self.name = name
        self.title = title
        self._df_raw = pd.read_html(str(soup))[0]
        #self.df = correct_misshift(soup, (self.name + " " + self.title)) # for debugging
        self.df = correct_misshift(soup)

        self.footnotes = footnotes
        self._heading = heading

        # Results for analyses stored in attributed
        self.parentheses_unit = scan_for_units(self.footnotes)


    def heading(self):
        return self._heading

    def article(self):
        return self._heading.article()

    def list_coefficients(self, type='df'):
        if type in ['df']:
            coef_df = find_se_rows(self.df)
            if coef_df.empty:
                return None
            else:
                coef_df = compute_z_score(coef_df, self.parentheses_unit)
                coef_df = compute_p_value(coef_df, "z")
                return coef_df
        elif type in ['list']:
            #return table_list
            raise ValueError("CODE NOT COMPLETED YET.")
        else:
            list_method_format_error()



if __name__ == "__main__":
    # my_journal = Journal("Economic Journal", "ej", f"{root_dir}/Data/Economic_Journal")
    # # print(my_journal.year(2003).issue(488).count_articles())
    # #a = my_journal.find_article_by_doi("https://doi.org/10.1111/ecoj.12428")
    # a = my_journal.find_article_by_doi("https://doi.org/10.1111/j.1468-0297.2012.02544.x")
    # print(a.heading(6).subheading_by_id(2))

    ej = Journal("ej")
    print(ej.volume(113).issue(484).article(1).list_headings())
