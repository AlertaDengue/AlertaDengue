import importlib

migration = importlib.import_module(
    "dados.migrations.0009_add_df_uf_epidemic_thresholds"
)


class FakeQuerySet:
    def __init__(self, manager):
        self.manager = manager

    def delete(self):
        self.manager.deleted = True


class FakeManager:
    def __init__(self):
        self.rows = {}
        self.deleted = False

    def using(self, alias):
        assert alias == "dados"
        return self

    def update_or_create(self, *, state_code, cid10, defaults):
        self.rows[(state_code, cid10)] = defaults

    def filter(self, **kwargs):
        assert kwargs == {"state_code": 53, "cid10__in": ["A90", "A92.0"]}
        return FakeQuerySet(self)


class FakeParameterUF:
    objects = FakeManager()


class FakeApps:
    @staticmethod
    def get_model(app_label, model_name):
        assert (app_label, model_name) == ("dados", "ParameterUF")
        return FakeParameterUF


class FakeConnection:
    alias = "dados"


class FakeSchemaEditor:
    connection = FakeConnection()


def test_0009_adds_validated_brasilia_thresholds():
    FakeParameterUF.objects = FakeManager()

    migration.add_df_uf_epidemic_thresholds(FakeApps(), FakeSchemaEditor())

    assert FakeParameterUF.objects.rows == {
        (53, "A90"): {
            "state_abbr": "DF",
            "state_name": "Distrito Federal",
            "limiar_preseason": 12.6688586706146,
            "limiar_posseason": 14.2228978596959,
            "limiar_epidemico": 76.6305102857116,
        },
        (53, "A92.0"): {
            "state_abbr": "DF",
            "state_name": "Distrito Federal",
            "limiar_preseason": 0.368068592796877,
            "limiar_posseason": 0.292548628366393,
            "limiar_epidemico": 1.26462573983109,
        },
    }


def test_0009_reverse_removes_only_df_thresholds():
    FakeParameterUF.objects = FakeManager()

    migration.remove_df_uf_epidemic_thresholds(FakeApps(), FakeSchemaEditor())

    assert FakeParameterUF.objects.deleted is True


def test_0009_leaves_es_placeholders_unchanged():
    FakeParameterUF.objects = FakeManager()
    es_placeholder = {
        "state_abbr": "ES",
        "state_name": "Espírito Santo",
        "limiar_preseason": None,
        "limiar_posseason": None,
        "limiar_epidemico": None,
    }
    FakeParameterUF.objects.rows[(32, "A90")] = es_placeholder

    migration.add_df_uf_epidemic_thresholds(FakeApps(), FakeSchemaEditor())

    assert FakeParameterUF.objects.rows[(32, "A90")] == es_placeholder
