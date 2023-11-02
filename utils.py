import os.path


def unique_filename(candidate_filename: str) -> str:
    """
    Function to generate a unique filename in the current directory.

    This function takes a candidate filename, checks if it already exists in 
    the current working directory, and if it does, appends a counter value 
    before the file extension until a unique filename is found.

    Parameters: 
    candidate_filename (str): Initial filename supplied by the user.

    Returns: 
    candidate_filename (str): A unique filename. If the initial filename 
    is not unique, the function will add a counter to the base of the filename,
    incrementing it until a unique filename is found.

    Example:
    >>> unique_filename('test.txt')
    'test_1.txt'
    """

    counter = 1
    name, ext = os.path.splitext(candidate_filename)

    while os.path.exists(candidate_filename):
        candidate_filename = f"{name}_{counter}{ext}"
        counter += 1

    return candidate_filename
    
