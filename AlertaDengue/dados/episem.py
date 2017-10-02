import numpy as np
import datetime

__author__ = 'Marcelo Ferreira da Costa Gomes'
'''
Return Brazilian epidemiological week from passed date
'''


def extractweekday(x=datetime.datetime):
    # Extract weekday as [Sun-Sat] |-> [0-6]
    # isoweekday() returns weekday with [Mon-Sun] as [1-7]
    w = x.isoweekday() % 7
    return w


def firstepiday(year=int):
    day = datetime.datetime.strptime('%s-01-01' % year, '%Y-%m-%d')

    day_week = extractweekday(day)

    # Whe want day1 to correspond to the first day of the first epiweek.
    # That is, we need the Sunday corresponding to epiweek=%Y01
    # If first day of the year is between Sunday and Wednesday,
    # epiweek 01 includes it. Otherwise, it is still the last epiweek
    # of the previous year
    if day_week < 4:
        day = day - datetime.timedelta(days=day_week)
    else:
        day = day + datetime.timedelta(days=(7-day_week))

    return day


def lastepiday(year=int):
    day = datetime.datetime.strptime('%s-12-31' % year, '%Y-%m-%d')


    day_week = extractweekday(day)

    # Whe want day to correspond to the last day of the last epiweek.
    # That is, we need the corresponding Saturday
    # If the last day of the year is between Sunday and Tuesday,
    # epiweek 01 of the next year includes it.
    # Otherwise, it is still the last epiweek of the current year
    if day_week < 3:
        day = day - datetime.timedelta(days=(day_week+1))
    else:
        day = day + datetime.timedelta(days=(6-day_week))

    return day


def episem(x, sep='W', out='YW'):

    """
    Return Brazilian corresponding epidemiological week from x.

    :param x: Input date. Can be a string in the format %Y-%m-%d or
      datetime.datetime
    :param sep: Year and week separator.
    :param out: Output format. 'YW' returns sep.join(epiyear,epiweek).
     'Y' returns epiyear only. 'W' returns epiweek only.
    :return: str
    """

    def out_format(year, week, out, sep='W'):
        if out == 'YW':
            return '%s%s%02d' % (year, sep, week)
        if out == 'Y':
            return '%s' % (year)
        if out == 'W':
            return '%02d' % week

    if type(x) != datetime.datetime:
        if str(x) == '' or (type(x) != str and np.isnan(x)):
            return None
        x = datetime.datetime.strptime(x, '%Y-%m-%d')

    epiyear = x.year
    epiend = lastepiday(epiyear)

    if x > epiend:
        epiyear += 1
        return out_format(epiyear, 1, out, sep)

    epistart = firstepiday(epiyear)

    # If current date is before its year first epiweek,
    # then our base year is the previous one
    if x < epistart:
        epiyear -= 1
        epistart = firstepiday(epiyear)

    epiweek = int(((x - epistart)/7).days) + 1

    return out_format(epiyear, epiweek, out, sep)
