from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import scipy.stats as st

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

import Functions.AdminFunctions as AF

def load_soup(filepath):
    file = open(filepath, 'r', encoding='utf-8')
    content = file.read()
    file.close()
    #print(content)
    soup = BeautifulSoup(content, 'lxml')
    return soup




def extract_from_filenames(filenames, target, filter = None):
    '''
    Scan a directory for matching files by year, volume, or issue
    :param fp: filepath to the directory which will be scanned
    :param target: chooses between ["year", "volume", "issue", "filename"]
    :param filter: list of string fitler conditions e.g. ["year<2004", "issue<487"]
    :return:
    '''

    t2g = {"year": 0, "volume": 1, "issue": 2}
    output = []
    for fn in filenames:
        m = re.search(r"^(\d{4})_(\d+)_(\d+)", fn)
        year = int(m.group(1))
        volume = int(m.group(2))
        issue = int(m.group(3))
        vals = [year, volume, issue]
        if filter == None:
            if target == "filename":
                output.append(fn)
            else:
                output.append(vals[t2g[target]])
        else:
            # confirm that the filter is in a list
            if type(filter) != list:
                raise ValueError("filter argument should be a list")
            do_append = True
            for f in filter:
                if not eval(f):
                    do_append = False
                    break
            if do_append:
                if target == "filename":
                    output.append(fn)
                else:
                    output.append(vals[t2g[target]])

    unique_output = list(set(output))
    if len(unique_output) == 0:
        unique_output = None
    elif len(unique_output) == 1:
        unique_output = unique_output[0]

    return unique_output



def article_overview(journal, soup):


    if journal in list(AF.oxford_journals.keys()):
        try:
            title = soup.find("h1", {'class': 'article-title-main'}).text.strip()
        except:
            title = None

        try:
            author_soup = soup.find("div", {'class': "al-authors-list"}).findAll('div', {'class': 'info-card-name'})
            authors = [x.text.strip() for x in author_soup]
        except:
            authors = []
        #print(title)
        #print(authors)


        return {'title': title, 'authors': authors}
    else:
        raise ValueError("Invalid journal abberviation provided.")



def gather_soup(first_element, until=[], include_first_element=False):
    output_soup = []

    nextNode = first_element
    if include_first_element:
        output_soup.append(str(nextNode))
    while True:
        nextNode = nextNode.findNextSibling()
        if nextNode == None:
            break

        try:
            tag_name = nextNode.name
        except AttributeError:
            tag_name = ""

        if tag_name in until:
            break
        else:
            output_soup.append(str(nextNode))

    return BeautifulSoup("".join(output_soup), features="lxml")



def unpack_headings(heading_list, start_level):

    class _UnpackedHeadingObj:
        def __init__(self, heading_list, start_level):
            self._history = []
            self._list = []
            self._recursive_append(heading_list, start_level)
            self.df = None
            self.unpack_to_df()


        def _append_buffered(self, h, level):
            if level > len(self._history):
                self._history.append(h.id)
            self._history[(level - 1)] = h.id
            self._list.append({'level': level, 'id': h.id, 'name': h.name, 'history': self._history[:(level-1)]})

        def _recursive_append(self, heading_list, start_level):
            for h in heading_list:
                self._append_buffered(h, start_level)
                if len(h.subheadings) > 0:
                    self._recursive_append(h.subheadings, (start_level + 1))

        def unpack_to_df(self):
            # get the max level
            max_level = max([x['level'] for x in self._list])
            dic_list = {}
            for l in range(1, (max_level + 1)):
                dic_list[f"h{l}"] = []
            dic_list['heading_name'] = []
            for h in self._list:
                # fill in values for all levels
                i = max_level
                while i > 0:
                    hx = f'h{str(i)}'
                    if i > h['level']:
                        dic_list[hx].append(0)
                    elif i == h['level']:
                        dic_list[hx].append(h['id'])
                    else:
                        diff = i - h['level']
                        dic_list[hx].append(h['history'][diff])
                    i = i - 1

                dic_list['heading_name'].append(h["name"])
            self.df = pd.DataFrame(dic_list)

    return _UnpackedHeadingObj(heading_list, start_level).df.set_index("h1")

# THE OLD MISSHIFT FUNCTION
# def correct_misshift(df):
#     df = df.copy()
#     rows_to_shift = []
#     first_col = df.iloc[:, 0].values
#     last_col = df.iloc[:, -1].values
#
#     for i in range(0, len(first_col)):
#         f = first_col[i]
#         l = last_col[i]
#     # search for parenthesis in first column values
#         m = re.search(r"^\(.*\)$", str(f))
#         try:
#             isnan = np.isnan(l)
#         except:
#             isnan = False
#         if (m != None) and isnan:
#             rows_to_shift.append(i+1)
#
#     for r in rows_to_shift:
#         i = df.iloc[(r-1), :].shape[0]
#         while i > 1:
#             df.iloc[(r-1), i-1] = df.iloc[(r-1), i-2]
#             i = i -1
#         df.iloc[(r-1), 0] = np.nan
#
#     return df

def correct_misshift(soup, identifier=None):
    '''

    :param soup:
    :param identifier: pass the table name and title to help see what is what when printing
    :return:
    '''
    warnings = []
    # analyze table head
    col_counts = []
    theads = soup.find('thead').findAll('tr')
    if identifier != None:
        print(f"table name is: {identifier}")
    # compute the maximum colspan in the table head (just through a basic count)
    for tr in theads:
        colspan = 0
        cols = tr.findAll(['td', 'th'])
        for c in cols:
            try:
                colspan += int(c['colspan'])
            except:
                colspan += 1
        col_counts.append(colspan)
    colspan = max(col_counts)
    #print(f"col_counts are: {col_counts}")
    #print(f"colspan is: {colspan}")

    # updadate the col_counts list now, but adjusting for rowspans > 1
    # note this will only be needed if we have different col_counts
    if len(set(col_counts)) > 0:
        col_counts = []
        active_rowspans = [0] * colspan
        for tr in theads:
            # compute the col_count adjusting for any lagging rowspans
            colspan = 0
            cols = tr.findAll(['td', 'th'])
            for i in range(0, len(cols)):
                c = cols[i]
                # add column colspans
                try:
                    colspan += int(c['colspan'])
                except:
                    colspan += 1
            # add any lagging rowspans as 1 colspan each
            colspan = colspan + (len(active_rowspans) - active_rowspans.count(0))
            col_counts.append(colspan)

            # now decrement the numbers in active_rowspans
            for i in range(0, len(active_rowspans)):
                r = active_rowspans[i]
                r = r-1
                if r > 0:
                    active_rowspans[i] = r
                else:
                    active_rowspans[i] = 0

            # compute any new lagging rowspans
            buffer = 0
            for i in range(0, len(cols)):
                c = cols[i]
                # check if there is a lagging rowspan in this spot, if so, add to buffer
                # for updating the active_rowspan lags
                while active_rowspans[i+buffer] != 0:
                    buffer += 1
                    if (i+buffer) == len(active_rowspans):
                        break

                # add cell rowspan
                try:
                    active_rowspans[i+buffer] = int(c['rowspan']) - 1
                except:
                    active_rowspans[i+buffer] = 0
        colspan = max(col_counts)

        # append warning if there is a mismatch in span among rows in the thead.
        if len(list(set(col_counts))) > 1:
            warnings.append("Table-head colspan mismatch")

        # having trained on Table 4 in https://doi.org/10.1111/ecoj.12550
        # we correct any tr in the table head that do not have col_count == colspan
        # correcting the table head
        # soup = BeautifulSoup(data)
        # for a in soup.findAll('a'):
        #     a.parent.insert(a.parent.index(a)+1, Tag(soup, 'br'))

        head = soup.find('thead').findAll("tr")
        for i in range(0, len(head)):
            tr = head[i]
            if col_counts[i] != colspan:
                diff = colspan - col_counts[i]
                while diff > 0:
                    tr.insert(0, BeautifulSoup('<td>&nbsp;</td>', 'html.parser'))
                    diff = diff -1


    # now correct the table body
    # similarily we need to control for rowspans. I do this with an active_rowspan_list

    body = soup.find('tbody').findAll("tr")
    rows_html = []
    active_rowspans = [0] * colspan
    for tr in body:
        cells = tr.findAll('td')
        colspan_row = 0
        for c in cells:
            try:
                colspan_row += int(c['colspan'])
            except:
                colspan_row += 1
        # add any lagging active_rowspans
        colspan_row = colspan_row + (len(active_rowspans) - active_rowspans.count(0))
        # buffer in the difference
        len_diff = colspan - colspan_row
        for i in range(0, len_diff):
            tr.insert(0, BeautifulSoup('<td>&nbsp;</td>', 'html.parser'))

        # now decrement the numbers in active_rowspans
        for i in range(0, len(active_rowspans)):
            r = active_rowspans[i]
            r = r-1
            if r > 0:
                active_rowspans[i] = r
            else:
                active_rowspans[i] = 0

        # now check for any new active_rowspans
        buffer = 0
        for i in range(0, len(cells)):
            c = cells[i]

            # check if there is a lagging rowspan in this spot, if so, add to buffer
            # for updating the active_rowspan lags
            while active_rowspans[i+buffer] != 0:
                buffer += 1
                if (i+buffer) == len(active_rowspans):
                    break
            # add cell rowspan
            try:
                active_rowspans[i+buffer] = int(c['rowspan']) - 1
            except:
                active_rowspans[i+buffer] = 0



    # replace the tbody in the soup
    #soup.tbody.replace_with(BeautifulSoup(html, 'html.parser'))
    df = pd.read_html(str(soup))[0]
    return df


def scan_for_units(text):
    if text == None:
        return None

    # 1. Check for explicit statement of STANDARD ERRORS IN PARENTHESES
    re_stderr = [r"st.{1,8}err.{,4}"] # standard error, std. err.
    re_parentheses = [r"parenthes[ie]s"]
    # check for standard errors being in parentheses
    for re_s in re_stderr:
        for re_p in re_parentheses:
            m = re.search(re_s + r".{,15}" + re_p, text.lower())
            if m != None:
                return "standard error"

    # 2. check for eplicit statement of SOMETHING ELSE IN PARENTHESES

    # 3. Weak matching on just key word ['standard error', 't-statistic', 'p-value'], append to list
    keywords = []
    # 3.1. check for standard error
    for re_s in re_stderr:
        m = re.search(re_s, text.lower())
        if m != None:
            keywords.append("standard error")
            break

    # 4. if unique value in list, return as result
    if len(keywords) == 1:
        return keywords[0]
    else:
        return 'unsure'



def list_method_format_error():
    raise SyntaxError("Invalid format passed. Try \"df\" or \"list\".")


#####################################################################
# PARSING CODE FOR EXTRACTING COEFFICIENTS FROM DF   ################
#####################################################################


# step 1: lets write a function that extracts the coefficients with their location in a nice dataframe
def find_se_rows(df):

    output_df = pd.DataFrame()
    # store the number of columns (excluding the first column with row titles)
    num_cols = df.shape[1] - 1
    # iterate through all of the rows in the df
    for i in df.index:
        row = df.iloc[i,1:]
        # check how many cells contain a number wrapped in parentheses
        try:
            bool = row.str.contains(r"\([\d\.]+\)")
        except:
            continue
        bool_sum = bool.sum(skipna=True)
        na = row.isnull()
        nan_sum = sum(na)

        # if we have a row with parentheses-wrapped numbers in all non-NA cells (excluding the first (row name) column)
        #if bool_sum >= num_cols - nan_sum:
        if bool_sum > 0:
            # save the index of the standard error row as well as the row above it (containing the coefficients
            row_indexes = [(i-1), i]
            mini_df = df.iloc[row_indexes, :].transpose()

            # extract the column name from possible multi-level indexes
            try:
                # trim away long content after e.g. "panel B: xxxxxxxxxxxxxxxx"
                # trim away all unnamed x_level_x
                column_levels = list(mini_df.index.values)

                for i in range(0, len(column_levels)):
                    column_levels[i] = list(column_levels[i])
                    m = re.search(r'^(panel.{1,7}:)', column_levels[i][0], re.IGNORECASE)
                    if m != None:
                        column_levels[i][0] = m.group(1)
                    for j in range(0, len(column_levels[i])):
                        m = re.search(r"unnamed.{,6}_level_", column_levels[i][j], re.IGNORECASE)
                        if m != None:
                            column_levels[i][j] = ""

                column_names = [" ".join(list(x)) for x in column_levels]
            except:
                count_index_levels = 1
                column_names = mini_df.index.values
            #print(f"column names: {column_names}")

            # with columns extraceted, we can drop the index of transposed mini_df
            mini_df.reset_index(drop=True, inplace=True)
            # now name the columns "coefficient" and "parentheses"
            mini_df.columns =['coefficient', 'parentheses']
            # now add columns for id and name of the coefficient row and column from the original df
            row_name = mini_df.iloc[0, :].values[0]
            mini_df['row_id'] = i
            mini_df['row_name'] = row_name
            mini_df['col_id'] =range(0, 0 + len(mini_df))
            mini_df['col_name'] = column_names
            # remove the first row of the mini_df (the first column from the df, no coefficients here)
            mini_df = mini_df.iloc[1:, :]
            # remove any coefficients with value nan or if std error in nan
            mini_df = mini_df.loc[(mini_df['coefficient'].isnull() == False) & (mini_df['parentheses'].isnull() == False), :]

            # trim away the parentheses from the standard error
            def no_parentheses(x):
                try:
                    x = float(re.search(r"\((.*)\)", x).group(1))
                except:
                    x = np.nan
                return x
            mini_df['parentheses'] = mini_df['parentheses'].apply(no_parentheses)

            # remove any stars from the coefficients and return the star count
            def count_stars(x):
                return x.count("*")
            mini_df['sig_stars'] = mini_df['coefficient'].apply(count_stars)
            def clean_coefficients(x):
                # remove the stars
                x = re.sub(r"\*", "", x)
                # replace weird negative signs
                x = re.sub(r"^[_¯ˉˍ‒‑–—―‾⎯⏤─−]+", "-", x)
                try:
                    return float(x)
                except:
                    return np.nan
            mini_df['coefficient'] = mini_df['coefficient'].apply(clean_coefficients)

            # drop any coefficient pair where there is NaN in coefficient or stderr
            mini_df = mini_df.loc[(mini_df['coefficient'].isnull() == False) & (mini_df['parentheses'].isnull() == False), : ]
            #print(mini_df)
            # assign or append to output_df

            if output_df.empty:
                output_df = mini_df
            else:
                output_df = output_df.append(mini_df, ignore_index=True)

    return output_df

# step 3 divide the coefficient by the stadnrd error to get list of z scores
def compute_z_score(coef_df, parentheses_unit):
    def standard_error(coef_df):
        coef_df['z_score'] = abs(coef_df['coefficient']/coef_df['parentheses'])
        coef_df = coef_df.rename(columns = {'parentheses':'standard_error'})
        return coef_df
    if parentheses_unit == "standard error":
        return standard_error(coef_df)
    else:
        # here we make an assumption about the values in the parentheses
        return standard_error(coef_df)
# step 4 compute the pvalues from the zscores
def compute_p_value(coef_df, col_from):
    if col_from in ['z_score', 'z']:
        # Calculating the p-value from the z-value using the survival function and multiplying the result by 2 (assuming two-taied test)
        coef_df['p_value'] = st.norm.sf(coef_df['z_score'].apply(abs))*2
    return coef_df

if __name__ == "__main__":
    x = "mples ‘board’ and ‘city’. Standard errors are in parenthesis and are robust to correlation within clusters (Woredas within Addis Ababa). *denotes significance at the 10%, ** at the 5% an"
    scan_for_units(x)