def diff_default(file1, file2) :
    trans = lambda s : '\n'.join(map(lambda s : s.rstrip(), filter(lambda t : len(t) > 0, s.split('\n'))))

    with open(file1) as f :
        f1 = trans(f.read())
    with open(file2) as f :
        f2 = trans(f.read())
    
    return f1 != f2