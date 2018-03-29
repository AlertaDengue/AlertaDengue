from datetime import timedelta

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
        if str(x) == '' or x is None or (type(x) != str and np.isnan(x)):
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


def episem2date(epi_year_week: str, weekday: int=0):
    """
    Function to obtain first day of corresponding Brazilian epidemiological
    week provided

    Function \code{episem2date} uses the Brazilian definition of epidemiological
    week and returns the date of the corresponding o the provided epi. week, using
    week day requested. Uses Sunday as default, the first week day by Brazilian epi.
    week definition.
    @see https://github.com/marfcg/leos.opportunity.estimator/blob/master/R/episem2date.R

    @name episem2date
    @param epiyearweek Epidemiological week in the format "%Y\[*\]%W" where Y and W defined
     by the Brazilian epidemiological week system. The separator between Y and W is irrelevant.
     Ex.: 2014W02
    @param weekday Week day to be used as representative of the epi. week. Uses Date week day
    classification. 0: Sunday, 6:Saturday. Default: 0

    @return Date corresponding to the Sunday of epiyearweek
    @export

    @examples
    epiyearweek <- '2014W02'
    episem2date(epiyearweek)

    Test:

    dt = datetime.datetime.now()

    yw1 = int(episem(dt, sep=''))
    dt1 = episem2date(yw1)
    yw2 = int(episem(dt1, sep=''))

    assert yw1 == yw2

    :param epi_year_week:
    :param weekday:
    :return:
    """
    # force str format
    epi_year_week = str(epi_year_week)
    # Separate year and week:
    if len(epi_year_week) not in [6, 7]:
        raise Exception('Epi Year Week not valid.')

    epiyear = int(epi_year_week[:4])
    epiweek = int(epi_year_week[-2:])

    # Obtain sunday of first epiweek of epiyear
    # day.one
    date_1 = datetime.datetime.strptime('%s-01-01' % epiyear, '%Y-%m-%d')
    # day.one.week
    date_1_w = int(date_1.strftime('%w'))

    # Check wether week day of Jan 1st was before or after a Wednesday
    # and set the start of the epiyear accordingly
    epiweek_day_1 = (
        date_1 - timedelta(days=date_1_w) if date_1_w <= 3 else
        date_1 + timedelta(days=7 - date_1_w)
    )
    return epiweek_day_1 + timedelta(days=7 * (epiweek - 1) + weekday)
