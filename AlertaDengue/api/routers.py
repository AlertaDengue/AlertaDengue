from .models import HistoricoAlerta, HistoricoAlertaChik, HistoricoAlertaZika

ROUTED_MODELS = [HistoricoAlerta, HistoricoAlertaChik, HistoricoAlertaZika]


class MunicipioRouter(object):
    """
    Router for schema "Municipio" in infodengue postgres database
    """

    def db_for_read(self, model, **hints):
        if model in ROUTED_MODELS:
            return '"Municipio"'
        return None
