import os.path


def unique_filename(candidate_filename):
        counter = 1
        name, ext = os.path.splitext(candidate_filename)

        while os.path.exists(candidate_filename):
            candidate_filename = f"{name}_{counter}{ext}"
            counter += 1

        return candidate_filename
    
