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

# import queen
# import alcove



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
def cleanDir(dname, olderThanDate=None, olderThanDaysAgo=None, largerThanMB=None, confirm=True):
    if olderThanDate is None and olderThanDaysAgo is None and largerThanMB is None:
        print("At least one of the filter options is required.")
        return

    # warning
    if confirm:
        print("WARNING: This script will DELETE files!")
        if not _promptConfirm("Continue?"):
            return

    file_paths_to_del = [] # files to delete
    try:
        # Iterate over files in the directory
        for root, _, files in os.walk(dname):
            for file in files:
                file_path = os.path.join(root, file)
                toDel = True

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
                # TODO: commented out for safety during testing
                # os.remove(file_path) 
                print(f"Deleted: {file_path}")

        else:
            print("Cleaning CANCELLED.")
            return

    print("Cleaning completed.")


# ============================================================================ #
# cleanTmpDir
def cleanTmpDir(**kwargs):
    cleanDir("tmp/", **kwargs)


# ============================================================================ #
# cleanLogDir
def cleanLogDir(**kwargs):
    cleanDir("logs/", **kwargs)


# ============================================================================ #
# cleanDroneDirs
def cleanDroneDirs():
    print("Functionality not added yet.")
    # cleanDir("tmp/", **kwargs)
    # each drone dir has subdirs which need cleaning
    # but don't touch the files in the base drone dir:
    # drones/drone[1-4]/



# ============================================================================ #
# INTERNAL FUNCTIONS
# ============================================================================ #


# ============================================================================ #
# _promptConfirm
def _promptConfirm(msg):
    yes = {'yes','ye', 'y'}
    choice = input(f"{msg} [y/n] ").strip().lower()
    if choice in yes:
        return True
    return False


# ============================================================================ #
# _setupArgparse
def _setupArgparse():
    """
    Setup command line arguments.
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Board cleaning CLI script.",
        epilog = "")

    # type of cleaning
    parser.add_argument("type", choices=['all', 'tmp', 'logs', 'drones'], 
        help="Type of cleaning.")
    
    # TODO: make one of these required
    # limiting options
    parser.add_argument("-d", "--date", 
        help="Limit to files older than [date].")
    parser.add_argument("-t", "--time", 
        help="Limit to files older than this input, in days.")
    parser.add_argument("-s", "--size",
        help="Limit to files larger than [size], in MB.")

    # return arguments values
    return parser.parse_args()


# ============================================================================ #
# _processCli
def _processCli(args):
    """Process the CLI input.
    """

    # print(args.type)
    # print(args.time)

    if args.type == 'tmp':
        cleanTmpDir(olderThanDate=args.date, olderThanDaysAgo=args.time, largerThanMB=args.size, confirm=True)


# ============================================================================ #
# _isFileOlderThanDate
def _isFileOlderThanDate(file_path, olderThanDate):
    """
    olderThanDate: (str) YYYY-mm-dd"
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
    """
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
    """
    """

    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    isLargerThanMB = file_size_mb > float(largerThanMB)

    return isLargerThanMB



if __name__ == "__main__":
    main()