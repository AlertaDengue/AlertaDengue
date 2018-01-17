from django.http import HttpResponse
from django.views.generic.base import View

# local
from .db import NotificationQueries, STATE_NAME


class _GetMethod:
    """

    """
    def _get(self, param, default=None):
        """

        :param param:
        :param default:
        :return:
        """
        result = (
            self.request.GET[param]
            if param in self.request.GET else
            default
        )

        return result if result else default



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

        uf = self._state_name[self._get('state_abv')]

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


class AlertCityRJView(View, _GetMethod):
    def get(self, request):
        pass
