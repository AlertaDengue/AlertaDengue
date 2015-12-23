from django.shortcuts import render
from django import template

register = template.Library()

@register.tag()
def alerta_series(geocodigo):
    return
    
