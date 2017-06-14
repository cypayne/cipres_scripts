''' 
Program: cipres_data_parse 

  Description: Standalone Python program to parse data files uploaded
  to CIPRES gateway. Currently configued to handle BEAST, BEAST2, 
  MrBayes, GARLI configuration, and Migrate input files

  Note that all files are opened with universal newlines support
  ('rU') so that we can handle files created using the Linux, Windows
  and Mac formats

  File parsing routines have very minimal error checking capabilities,
  definitely no substitute for a comprehensive file format checker
 
  Authors: Robert Sinkovits and Cheyenne Payne, SDSC
 
  Usage: 
  > python3 cipres_data_parse.py [file_name] <-t file_type>
'''

import re
import argparse
import os 

# Process the command line arguments
file_types = ['beast', 'beast2', 'migrate_parm', 'migrate_infile', 'bayes', 'garli']
parser     = argparse.ArgumentParser(description='Process file name and file type cmd line args')
parser.add_argument(dest='file_name')
parser.add_argument('-t', '--type', dest='file_type', choices=file_types, default='unknown')
args      = parser.parse_args()
file_name = args.file_name
file_type = args.file_type

def process_beast(file_name):
    ''' Process BEAST files and return following
    
          datatype (nucleotide or amino acid)
          codon_partioning (True or False)
          nu_partitions (number of partitions)
          nu_patterns (number of patterns)
    '''

    # Initialize results
    datatype           = 'unknown'
    codon_partitioning = False
    nu_partitions      = 0
    pattern_count      = 0

    # Start by assuming successful parsing of file
    err_code = 0

    # Define the regex that will be used to identify
    # and parse the dataType, npatterns and codon lines
    regex_datatype = '.*alignment.*data[tT]ype\s*=\s*"'
    regex_patterns = '.*npatterns\s*=\s*'
    regex_codon    = 'codon'

    # Compile the regex. Probably doesn't make a performance difference
    # since python will cache recently used regex, but doesn't hurt
    cregex_datatype = re.compile('.*alignment.*data[tT]ype\s*=\s*"')
    cregex_patterns = re.compile('.*npatterns\s*=\s*')
    cregex_codon    = re.compile('codon')

    with open(file_name, 'rU') as fin:
        for line in fin:
            line = line.rstrip()

            # Process the dataType lines
            if cregex_datatype.search(line):
                line = re.sub(regex_datatype, '', line)
                line = re.sub('".*', '', line)
                datatype = re.sub('\s*', '', line)

            # Process the lines that list number of patterns
            # Increment pattern and partition counts
            if cregex_patterns.search(line):
                line = re.sub(regex_patterns, '', line)
                line = re.sub('\D.*', '', line)
                pattern_count += int(line)
                nu_partitions += 1
                    
            # Look for lines that contain the string "codon"
            if cregex_codon.search(line):
                codon_partitioning = True

    # Test for errors:
    # Data type is not set to aminoacid or nucleotide
    if datatype != 'aminoacid' and datatype != 'nucleotide':
        err_code = 1
    # Number of partitions or pattern counts non-positive numbers
    if nu_partitions <= 0 or pattern_count <= 0:
        err_code = 1

    return err_code, datatype, codon_partitioning, nu_partitions, pattern_count

def process_beast2(file_name):
    ''' Process BEAST2 files and return following
    
          nu_partitions (number of partitions)

        Partition count is determined from the number of <distribution
         ...> </distribution> pairs appearing AFTER the tag starting with
         <distribution id="likelihood"
    '''

    # Initialize results
    nu_partitions = 0
    start_counting = False

    # Start by assuming successful parsing of file
    err_code = 0

    with open(file_name, 'rU') as fin:
        for line in fin:
            line = line.rstrip()
            
            # Look for the starting line
            if line.find('<distribution id="likelihood"') >= 0:
                start_counting = True
                continue
                
            # Start counting partitions
            if start_counting and line.find('<distribution') >= 0 and line.find('/>') < 0:
                nu_partitions += 1

    # Test for errors:
    # Number of partitions non-positive number
    if nu_partitions <= 0:
        err_code = 1

    return err_code, nu_partitions

def process_migrate_parm(file_name):
    ''' Process Migrate parmfile and return following
    
          num_reps (Number of replicates)

        Replicate count is determined from the line 
        replicate=< NO | YES:<VALUE | LastChains> >
    '''

    # Initialize replicates to 1
    num_reps = 1

    # Start by assuming successful parsing of file
    err_code = 0

    with open(file_name, 'rU') as fin:
        for line in fin:
            line = line.rstrip()
            
            # Look for the starting line
            if line.find('replicate=YES') >= 0:
                p1, num_reps = line.split(':')
                break

    # Test for errors:
    # number of replicates is not a valid number
    if not str(num_reps).isdigit():
        err_code = 1

    return err_code, num_reps

def process_migrate_infile(file_name):
    ''' Process Migrate infile and return following
    
          Number of num_loci

        Num_Loci count is determined from 1st record, 2nd field
    '''

    # Initialize num_loci to 1
    num_loci = 1

    # Start by assuming successful parsing of file
    err_code = 0

    with open(file_name, 'rU') as fin:
        for line in fin:
            line = line.strip()
            pline = line.split()
            num_loci = pline[1]
            break

    # Test for errors:
    # number of loci is not a valid number
    if not str(num_loci).isdigit():
        err_code = 1

    return err_code, num_loci

 
def process_garli(file_name):
    ''' Process garli infile and return the following values:
          
          bootstrapreps - number of bootstrap reps
          searchreps - number of search reps
          availablememory - amount of available memory

          nruns - number of runs, determined from value of
                  bootstrap reps

        if bootstrapreps=0, nruns=searchreps and searchreps=1
        otherwise, nruns=bootstrapreps and bootstrapreps=1
    '''

    # Start by assuming successful parsing of file
    err_code = 0

    # define, compile regex for extracting desired values 
    cregex_bootstrapreps = re.compile('bootstrapreps\s*=\s*(\d+).*')
    cregex_searchreps = re.compile('searchreps\s*=\s*(\d+).*')
    cregex_availmem = re.compile('.*availablememory\s*=\s*(\d+).*')

    # start with negative parameter values 
    nruns = -1
    bootreps = -1
    searchreps = -1
    availmem = -1
    have_bootreps = False
    have_searchreps = False
    have_availmem = False

    with open(file_name, 'rU') as fin:
        for line in fin:
            line = line.strip()

            # see if line has bootstrapreps value
            # if it does, collect value
            if not have_bootreps: 
                match = cregex_bootstrapreps.search(line)
                if match: 
                    bootreps = match.group(1)
                    have_bootreps = True

            # see if line has searchreps value
            # if it does, collect value
            if not have_searchreps: 
                match = cregex_searchreps.search(line)
                if match: 
                    searchreps = match.group(1)
                    have_searchreps = True

            # see if line has availablememory value
            # if it does, collect value
            if not have_availmem:
                match = cregex_availmem.search(line)
                if match:
                    availmem = match.group(1)
                    have_availmem = True

    # Test for errors:
    if not have_bootreps or not have_searchreps or not have_availmem:
        print('Input garli.conf file did not have one or more of the \
                required values (bootstrapreps, searchreps, availablememory')
        err_code = 1
    else:
        if bootreps == 0:
            nruns = searchreps
            searchreps = 1
        else:
            nruns = bootreps
            bootreps = 1

    return err_code, nruns, bootreps, searchreps, availmem


def process_bayes(file_name):
    ''' Process a MrBayes (NEXUS) infile and return the following values:
          
          nruns - number of runs
          nchains - number of chains

    '''

    # First check for a line headed by 'mcmc' or 'mcmcp'. If present, collect
    # nruns and nchains values, otherwise exit

    # Start by assuming successful parsing of file
    err_code = 0

    # Define, compile regex to collect nruns and nchains values
    cregex_mcmcp = re.compile('^(mcmc|mcmcp)\s')
    cregex_nruns = re.compile('.*nruns\s*=\s*(\d+).*')
    cregex_nchains = re.compile('.*nchains\s*=\s*(\d+).*')

    cregex_bootstrapreps = re.compile('bootstrapreps\s*=\s*(\d+).*')
    # start with no runs/chains
    nruns = -1
    nchains = -1
    mrbayes = False

    # First check for a line headed by 'mcmc' or 'mcmcp'. If present, collect
    # nruns and nchains values, otherwise exit
    with open(file_name, 'rU') as fin:
        for line in fin:
            line = line.strip()

            # First check for "begin mrbayes;" line
            if cregex_mcmcp.search(line):
                mrbayes = True

                # Search for nruns, collect value
                # otherwise, use default value
                match = cregex_nruns.search(line)
                if match:
                    nruns = match.group(1)
                else:
                    nruns = 2

                # Search for nchains, collect value
                # otherwise, use default value
                match = cregex_nchains.search(line)
                if match: 
                    nchains = match.group(1)
                else:
                    nchains = 4
                break

    # Test for errors:
    # Number of partitions non-positive number
    if nruns == -1 or nchains == -1:
        err_code = 1

    if not mrbayes:
        print('No bayes block to process, so no values collected')

    return err_code, nruns, nchains

#--------------------------------------------------------------
# ------------------- Start main program ----------------------
#--------------------------------------------------------------

# Determine the input file type if not already set
if file_type == 'unknown':
    with open(file_name, 'rU') as fin:
        for line in fin:
            if line.find('BEAUTi') >= 0:
                file_type = 'beast'
                break
            if line.find('<beast') >= 0 and line.find('version="2.0">') >= 0:
                file_type = 'beast2'
                break
            if line.find('Parmfile for Migrate') >= 0:
                file_type = 'migrate_parm'
                break
            if line.find('#NEXUS') >= 0:
                file_type = 'bayes'
                break
            if line.find('[general]') >= 0:
                file_type = 'garli'
                break

# Process BEAST files
if file_type == 'beast':
    err_code, datatype, codon_partitioning, nu_partitions, pattern_count = process_beast(file_name)
    results =  'file_type=' + file_type + '\n'
    results += 'err_code=' + str(err_code) + '\n'
    results += 'datatype=' + datatype + '\n'
    results += 'codon_partitioning=' + str(codon_partitioning) + '\n'
    results += 'nu_partitions=' + str(nu_partitions) +'\n'
    results += 'pattern_count=' + str(pattern_count)

# Process BEAST2 files
if file_type == 'beast2':
    err_code, nu_partitions = process_beast2(file_name)
    results =  'file_type=' + file_type + '\n'
    results += 'err_code=' + str(err_code) + '\n'
    results += 'nu_partitions=' + str(nu_partitions)

# Process Migrate parmfile
if file_type == 'migrate_parm':
    err_code, num_reps = process_migrate_parm(file_name)
    results =  'file_type=' + file_type + '\n'
    results += 'err_code=' + str(err_code) + '\n'
    results += 'num_reps=' + str(num_reps)

# Process Migrate infile
if file_type == 'migrate_infile':
    err_code, num_loci = process_migrate_infile(file_name)
    results =  'file_type=' + file_type + '\n'
    results += 'err_code=' + str(err_code) + '\n'
    results += 'num_loci=' + str(num_loci)

# Process GARLI configuration infile 
if file_type == 'garli':
    err_code, nruns, bootreps, searchreps, availmem = process_garli(file_name)
    results = 'file_type=' + file_type + '\n'
    results += 'err_code=' + str(err_code) + '\n'
    results += 'nruns=' + str(nruns) + '\n'
    results += 'bootstrapreps=' + str(bootreps) + '\n'
    results += 'searchreps=' + str(searchreps) + '\n'
    results += 'availablememory=' + str(availmem)

# Process MrBayes files
if file_type == 'bayes':
    err_code, nruns, nchains = process_bayes(file_name)
    results = 'file_type=' + file_type + '\n'
    results += 'err_code=' + str(err_code) + '\n'
    results += 'nruns=' + str(nruns) + '\n'
    results += 'nchains=' + str(nchains)

# Unknown or unidentifiable file type
if file_type == 'unknown':
    results =  'file_type=' + file_type + '\n'
    results += 'err_code=1'

print(results)
