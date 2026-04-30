def run_environment(instructions, link=None, file_path=None):
    if (link is None) == (file_path is None):
        raise ValueError(
            "Provide exactly one of `link` or `file_path` (not neither, not both)."
        )
    
