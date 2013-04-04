import warnings


def lazy_object(location):
    def inner(*args, **kwargs):
        parts = location.rsplit('.', 1)
        warnings.warn('`xratings.%s` is deprecated. Please use `%s` instead.' % (parts[1], location), DeprecationWarning)
        try:
            imp = __import__(parts[0], globals(), locals(), [parts[1]], -1)
        except:
            imp = __import__(parts[0], globals(), locals(), [parts[1]])
        func = getattr(imp, parts[1])
        if callable(func):
            return func(*args, **kwargs)
        return func
    return inner

RatingField = lazy_object('xratings.fields.RatingField')
AnonymousRatingField = lazy_object('xratings.fields.AnonymousRatingField')
Rating = lazy_object('xratings.fields.Rating')
