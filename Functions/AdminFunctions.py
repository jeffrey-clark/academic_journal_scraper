import json
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

# load the journal catalogues
f = open(f"{root_dir}/Data/catalogue.json")
cat = json.load(f)
f.close()

oxford_journals = cat['oxford_journals']



def get_journal_data(journal, attribute):
    journal = journal.lower()
    if journal in list(oxford_journals.keys()):
        try:
            journal_dir = oxford_journals[journal][attribute]
        except:
            raise ValueError("Invalid journal attribute provided. Check the journal catalogue.")
    else:
        raise ValueError("Invalid journal abbreviation provided as argument")

    return f"Data/{journal_dir}"

def get_journal_dir(journal):
    return get_journal_data(journal, 'dir_name')

def get_journal_name(journal):
    return get_journal_data(journal, 'name')


def confirm_journal_data_directories(journal, verbose=False):
    '''
    Confirm that the necessary directories exist for the journal i.e. a main journal directory,
    with the subdirectories: Articles, and Tables_of_Contents
    :param journal_name: journal abbreviation (str)  ['ej']
    :return: True
    '''

    journal_dir = get_journal_dir(journal)
    if os.path.isdir(journal_dir):
        if verbose:
            print(f"{journal_dir} exists")
        subdirs = ['Articles', 'Tables_of_Contents']
        for sd in subdirs:
            fp_sd = f"{journal_dir}/{sd}"
            if os.path.isdir(fp_sd):
                if verbose:
                    print(f"{fp_sd} exists")
            else:
                if verbose:
                    print(f"{sd} directory is missing...")
                os.mkdir(fp_sd)
                if verbose:
                    print(f"created empty subdirectory: {fp_sd}")
    else:
        if verbose:
            print(f"created directory: {journal_dir}")
        os.mkdir(journal_dir)
        subdirs = ['Articles', 'Tables_of_Contents']
        for sd in subdirs:
            fp_sd = f"{journal_dir}/{sd}"
            os.mkdir(fp_sd)
            if verbose:
                print(f"created subdirectory: {fp_sd}")

    return journal_dir


if __name__ == "__main__":
    print(oxford_journals)
    print(get_journal_dir("qje"))