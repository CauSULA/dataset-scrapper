def replaces(s: str):
    return s.replace('\u202f', ' ').replace('\xa0', '\n').replace('&nbsp', ' ')
