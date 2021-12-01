def chunks(lst, n):
    '''

    :param lst: list to break into chunks
    :param n: int, size of desired chunks. final chunk may be smaller.
    :return: list of lists, where sublists are of size n.
    '''
    return[lst[i:i + n] for i in range(0, len(lst), n)]


def normalize_email(email):
    return (email or '').strip().lower()