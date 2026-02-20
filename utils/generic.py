
def allowed_file(filename: str, allowed_extendions: list):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extendions
