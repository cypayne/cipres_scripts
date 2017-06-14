'''
POST-GARLI CIPRES SCRIPT
~~~~~~~~~ v1.0 ~~~~~~~~~
To be used when Garli has elected multiple best trees (from being run on parallel cores), 
and multiple .best.tre files exists in the current directory. This script collects the 
Garli scores from each of these best tree files, and ranks the trees by score from highest
to lowest score. This allows the user to quickly determine which of the "best trees" is 
truly the best tree.

Execute this file inside the directory containing all of your .best.tre files

Simply run as:
> python3 post_garli.py
'''

import os 
import re

def collect_score(regex_score, line):
    '''
    Collects the GarliScore from current line using regex
    Parameters: regex_score - compiled regex for pulling score from line
                line - line to collect score from
    Returns: The collected GarliScore, or score of 0 if none is found
    '''
    match = regex_score.search(line)

    # if a score is collected, store value
    if match:
        score = float(match.group(1))

    # otherwise give error score of 0
    else:
        score = 0

    return score
 
def make_out_file(score_dict):
    '''
    Creates the output file containing scores and their corresponding 
       filenames in descending order
    Parameters: score_dict - dictionary of scores, filenames
    Returns: nothing
    '''
    output_file = open('garli_scores.txt', 'w')
    output_file.write('### RANK OF GARLI SCORES (highest to lowest) ###\n\n Score:\tfilename \n')

    # sort scores in descending order, write to output file
    for gs in sorted(score_dict, reverse = True):
        output_file.write('%s: %s \n' % (gs, score_dict[gs]))  
        
    output_file.close


''' Main ''' 

print('\n############### Ranking Garli Scores ############### \n')

# create empty dictionary to store filename, score pairs
score_dict = {}

# regex to pull GarliScore (compiled)
regex_score = re.compile('GarliScore\s([-?]\d+[\.\d]+)')

# start with no error and empty list of error-prone Garli output files
error_code = 0
problem_files= []

first_file = True
lines_until_score = 0

# loop through all *.best.tre files in current directory
print('Processing files... \n')

files = [f for f in os.listdir('.') if f.endswith('.best.tre')] 

for filename in files:
    with open(filename, 'rU') as fin: 
        line_num = 0
        for line in fin:

            # for the first file, count the number of lines before reaching the 
            # line containing Garli score. Once reached, stop counting lines and
            # store score
            if first_file:
                line = line.rstrip()
                if line.find('GarliScore') >= 0:
                    score = collect_score(regex_score, line)
                    first_file = False
                    break

                lines_until_score += 1
            
            # for all other files, jump to line with score and collect score
            else:
                if line_num == lines_until_score:
                    line = line.rstrip()
                    score = collect_score(regex_score, line)
                    break
                else:
                    line_num += 1

    # give files for which score retrieval was unsuccessful an error code of 1, 
    # add their name to list of problematic files
    if score == 0:
        error_code = 1
        problem_files.append(filename)
    
    # otherwise, add score, filename to list of scores 
    else:
        score_dict[score] = filename

# print error_code and problem_files (if relevant)
if error_code == 1:
    print('Errors were encountered when processing the\n'
           + 'following files: \n')
    print(problem_files)

else:
    # add scores with corresponding filename to file called garli_scores.txt
    make_out_file(score_dict)

    print('All scores were collected successfully, please see\n'
           + 'garli_scores.txt for ranked Garli scores.\n')

