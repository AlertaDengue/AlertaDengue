import base64
import io
import matplotlib.pyplot as plt


def get_chart_info_city_base64(
    df_alert, param, var_climate='temp_min', cid='A90', tsdur=104
):
    """
    codigo da figura com 3 subfiguras que e usada para os municipios

    df_alert é o alerta do municipio gerado pelo update.alerta

    example: plot_city(alePR_RS_Cascavel[["CéuAzul"]])

    :param df_alert:
    :param param:
    :param var_climate:
    :param cid:
    :param tsdur:
    :return:

    """
    if cid == "A90":
        title= "Casos de Dengue"
    elif cid == "A92.0":
        title= "Casos de Chikungunya"
    elif cid == "A92.8":
        title= "Casos de Zika"

    if cid == "A92.0":
        legend = 'casos de chikungunya'
    if cid == "A92.8":
        legend = "casos de zika"
    if cid == "A90":
        legend = "casos de dengue tweets"

    buf = io.BytesIO()
    df_alert.plot()
    plt.savefig(buf, format="png")
    img = str(base64.b64encode(buf.getvalue()).strip())
    return img[2:-1]
