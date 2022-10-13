"""
Module for plotting charts in the states reports
"""

from copy import deepcopy

import pandas as pd

# import plotly.graph_objs as go
# from django.utils.translation import gettext as _
# from plotly.subplots import make_subplots


class ReportStateCharts:
    """Charts used by Report State."""

    @classmethod
    def create_notific_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        df = deepcopy(df)

        return df.to_html()

    @classmethod
    def create_level_chart(
        cls,
        df: pd.DataFrame,
    ) -> str:
        df = deepcopy(df)

        return df.to_html()
