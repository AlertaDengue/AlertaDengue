from django.http import HttpResponse
from django.views.generic.base import View

# local
from .db import NotificationQueries, STATE_NAME, AlertCity, MRJ_GEOCODE


class _GetMethod:
    """

    """
    def _get(self, param, default=None, cast=None, error_message=None):
        """

        :param param:
        :param default:
        :return:
        """
        if error_message is not None and param not in self.request.GET:
            raise Exception(error_message)

        result = (
            self.request.GET[param]
            if param in self.request.GET else
            default
        )

        return result if cast is None or result is None else cast(result)



class NotificationReducedCSV_View(View, _GetMethod):
    """

    """
    _state_name = STATE_NAME

    request = None

    def get(self, request):
        """

        :param kwargs:
        :return:
        """
        self.request = request

        state_name = self._get('state_abv', default='').upper()

        if state_name not in self._state_name:
            return HttpResponse(
                'ERROR: STATE NOT FOUND', content_type="text/plain",
                status=404
            )

        uf = self._state_name[state_name]

        chart_type = self._get('chart_type')

        notifQuery = NotificationQueries(
            uf=uf,
            disease_values=self._get('diseases'),
            age_values=self._get('ages'),
            gender_values=self._get('genders'),
            city_values=self._get('cities'),
            initial_date=self._get('initial_date'),
            final_date=self._get('final_date')
        )

        result = None

        if chart_type == 'disease':
            result = notifQuery.get_disease_dist().to_csv()
        elif chart_type == 'age':
            result = notifQuery.get_age_dist().to_csv()
        elif chart_type == 'age_gender':
            result = notifQuery.get_age_gender_dist().to_csv()
        elif chart_type == 'age_male':
            result = notifQuery.get_age_male_dist().to_csv()
        elif chart_type == 'age_female':
            result = notifQuery.get_age_female_dist().to_csv()
        elif chart_type == 'gender':
            result = notifQuery.get_gender_dist().to_csv()
        elif chart_type == 'period':
            result = notifQuery.get_period_dist().to_csv(
                date_format='%Y-%m-%d'
            )
        elif chart_type == 'epiyears':
            # just filter by one disease
            result = notifQuery.get_epiyears(uf, self._get('disease')).to_csv()
        elif chart_type == 'total_cases':
            result = notifQuery.get_total_rows().to_csv()
        elif chart_type == 'selected_cases':
            result = notifQuery.get_selected_rows().to_csv()

        return HttpResponse(result, content_type="text/plain")


class AlertCityView(View, _GetMethod):
    """

    """
    request = None

    def get(self, request):
        self.request = request
        format = ''

        try:
            disease = self._get(
                'disease', error_message='Disease sent is empty.'
            ).lower()
            geocode = self._get(
                'geocode', cast=int, error_message='GEO-Code sent is empty.'
            )
            format = self._get(
                'format', error_message='Format sent is empty.'
            ).lower()
            ew_start = self._get(
                'ew_start', cast=int,
                error_message='Epidemic start week sent is empty.'
            )
            ew_end = self._get(
                'ew_end', cast=int,
                error_message='Epidemic end week sent is empty.'
            )
            e_year = self._get(
                'e_year', cast=int,
                error_message='Epidemic year sent is empty.'
            )

            if format not in ['csv', 'json']:
                raise Exception(
                    'The output format available are: `csv` or `json`.'
                )

            ew_start = e_year*100 + ew_start
            ew_end = e_year*100 + ew_end

            if geocode == MRJ_GEOCODE:
                df = AlertCity.search_rj(
                    disease=disease, ew_start=ew_start, ew_end=ew_end
                )
            else:
                df = AlertCity.search(
                    geocode=geocode, disease=disease,
                    ew_start=ew_start, ew_end=ew_end
                )
                # change all keys to lower case
                df.drop(
                    columns=['municipio_geocodigo', 'municipio_nome'],
                    inplace=True
                )

            if format == 'json':
                result = df.to_json(orient='records')
            else:
                result = df.to_csv(index=False)
        except Exception as e:
            if format == 'json':
                result = '{"error_message": "%s"}' % e
            else:
                result = '[EE] error_message: %s' % e

        content_type = 'application/json' if format == 'json' else 'text/plain'

        return HttpResponse(result, content_type=content_type)
