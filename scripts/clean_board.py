# ============================================================================ #
# Board side cleanup script.
#
# James Burgoyne jburgoyne@phas.ubc.ca
# CCAT Prime 2023   
# ============================================================================ #


# ============================================================================ #
# Imports


import argparse
import os
import datetime



# ============================================================================ #
# Main


def main():
    """Run when this script directly accessed.
    """

    _processCli(_setupArgparse())




# ============================================================================ #
# EXTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# cleanDir
def cleanDir(dname, ftype=None, olderThanDate=None, olderThanDaysAgo=None, largerThanMB=None, confirm=True, testing=True):
    """Delete files in given dir which matches filters.

    ftype: (str) File extension to match.
    olderThanDate: (str) Match files older than YYYY-mm-dd date.
    olderThanDaysAgo: (int) Match files older than this number days ago.
    largerThanMB: (int) Match files larger than this in MB.
    confirm: (bool) Whether to prompt with a confirm dialogue.
    testing: (bool) Whether to actually delete files or not.
    """

    if olderThanDate is None and olderThanDaysAgo is None and largerThanMB is None:
        print("At least one of the filter options is required.")
        return

    # warning
    if confirm:
        print(f"WARNING: This script will DELETE files!")
        if testing:
            print("TESTING MODE: Will not actually delete.")
        if not _promptConfirm("Continue?"):
            return

    file_paths_to_del = [] # files to delete
    try:
        # Iterate over files in the directory
        for root, _, files in os.walk(dname):
            for file in files:
                file_path = os.path.join(root, file)
                toDel = True

                # extension
                if ftype:
                    file_ext = os.path.splitext(file_path)[1]
                    if file_ext != ftype:
                        toDel = False

                # date
                if olderThanDate and toDel:
                    toDel = _isFileOlderThanDate(file_path, olderThanDate)

                # days ago
                if olderThanDaysAgo and toDel:
                    toDel = _isFileOlderThanDaysAgo(file_path, olderThanDaysAgo)

                # size
                if largerThanMB and toDel:
                    toDel = _isFilelargerThanMB(file_path, largerThanMB)

                if toDel: # add to deletion list
                    file_paths_to_del.append(file_path)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    fcnt = len(file_paths_to_del)
    
    print(f"{fcnt} files to be deleted...")

    if fcnt > 0:
        if confirm and _promptConfirm(f"Delete {fcnt} files?"): # confirm first
            for file_path in file_paths_to_del:

                # delete
                if not testing:
                    os.remove(file_path) 
                    print(f"Deleted: {file_path}")
                else: 
                    print(f"NOT deleted (testing): {file_path}")

        else:
            print("Cleaning CANCELLED.")
            return

    print("Cleaning completed.")


# ============================================================================ #
# cleanTmpDir
def cleanTmpDir(**kwargs):
    """Delete files in tmp dir.

    See cleanDir(...) for argument descriptions.
    """

    cleanDir("tmp/", **kwargs)


# ============================================================================ #
# cleanLogDir
def cleanLogDir(**kwargs):
    """Delete files in log dir.
    
    See cleanDir(...) for argument descriptions.
    """

    cleanDir("logs/", ftype=".log", **kwargs)


# ============================================================================ #
# cleanDroneDirs
def cleanDroneDirs(**kwargs):
    """Delete files in drones dir.
    
    See cleanDir(...) for argument descriptions.
    """

    cleanDir("drones/", ftype=".npy", **kwargs)



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _promptConfirm
def _promptConfirm(msg):
    """CLI confirm (y/n) prompt with message.

    msg: (str) The message to display.
    """

    yes = {'yes','ye', 'y'}
    choice = input(f"{msg} [y/n] ").strip().lower()
    if choice in yes:
        return True
    return False


# ============================================================================ #
# _setupArgparse
def _setupArgparse():
    """Setup command line arguments.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Board cleaning CLI script.",
        epilog = "")

    # type of cleaning
    choices=['tmp', 'logs', 'drones']
    parser.add_argument("type", choices=choices, 
        help="Type of cleaning.")
    
    # limiting options
    parser.add_argument("-d", "--keep_from_date", 
        help="Limit to files older than [YYYY-mm-dd].")
    parser.add_argument("-l", "--keep_last_days", 
        help="Limit to files older than this input, in days.")
    parser.add_argument("-s", "--keep_smaller_than_MB",
        help="Limit to files larger than [size], in MB.")

    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# _processCli
def _processCli(args):
    """Process the CLI input.
    """

    def select(type, **kwargs):
        if type == 'tmp': cleanTmpDir(**kwargs)
        if type == 'logs': cleanLogDir(**kwargs)
        if type == 'drones': cleanDroneDirs(**kwargs)

    select(args.type, olderThanDate=args.keep_from_date, olderThanDaysAgo=args.keep_last_days, largerThanMB=args.keep_smaller_than_MB, confirm=True)


# ============================================================================ #
# _isFileOlderThanDate
def _isFileOlderThanDate(file_path, olderThanDate):
    """Check if file has a ctime older than given date.
    Note that ctime may mean creation time but probably means modified time.

    file_path: (str) File path.
    olderThanDate: (str) YYYY-mm-dd.
    """

    # Parse the date string into a datetime object
    delete_date = datetime.datetime.strptime(olderThanDate, "%Y-%m-%d")

    # Get the file's creation time
    file_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))

    # Check if the file is older than the specified days
    isOlderThanDate = file_time < delete_date

    return isOlderThanDate


# ============================================================================ #
# _isFileOlderThanDaysAgo
def _isFileOlderThanDaysAgo(file_path, olderThanDaysAgo):
    """Check if file ctime is older than some number of days ago.
    Note that ctime may mean creation time but probably means modified time.

    file_path: (str) File path.
    olderThanDaysAgo: (int) Number of days.
    """

    delta = datetime.timedelta(days=int(olderThanDaysAgo))
    current_time = datetime.datetime.now()

    # Get the file's creation time
    file_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))

    # Calculate the time difference
    time_difference = current_time - file_time

    # Check if the file is older than the specified days
    isOlderThanDaysAgo = time_difference < delta

    return isOlderThanDaysAgo


# ============================================================================ #
# _isFilelargerThanMB
def _isFilelargerThanMB(file_path, largerThanMB):
    """Check if file size is larger than some given size.

    file_path: (str) File path.
    largerThanMB: (int) The file size in MB.
    """

    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    isLargerThanMB = file_size_mb > float(largerThanMB)

    return isLargerThanMB



if __name__ == "__main__":
    main()